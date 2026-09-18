"""LLMService — the only place application code talks to a language model.

Responsible for: NL understanding, entity extraction, and customer-facing /
human-facing text generation. NOT authoritative for any financial fact (see
architectural Rule 1) — callers must inject verified values and this service
only phrases them.
"""

from __future__ import annotations

import json
import logging
import re

from app.agent import prompts
from app.config import get_settings

logger = logging.getLogger("nishchint.llm")

SENSITIVE_PATTERN = re.compile(
    r"\b(otp|pin|upi\s*pin|card\s*pin|password)\b.{0,15}?(\d{3,6})", re.IGNORECASE
)
# (?<!\d)/(?!\d) so this never matches a sub-run of a longer digit
# sequence, e.g. a fragment of a 12-digit UPI Ref No.
AMOUNT_PATTERN = re.compile(r"(?:₹|rs\.?|inr)?\s*(?<!\d)([\d,]{3,7})(?:\.\d+)?(?!\d)")
TXN_ID_PATTERN = re.compile(r"\bTXN\w+\b", re.IGNORECASE)
# Real UPI/Paytm reference numbers are 12 digits, e.g. "809489842596" — the
# format customers actually see and type, unlike the internal "TXN..." id.
UPI_REF_PATTERN = re.compile(r"\b\d{12}\b")


def contains_sensitive_credential(text: str) -> bool:
    return bool(SENSITIVE_PATTERN.search(text))


def normalize_language(language: str | None) -> str:
    """Canonicalizes whatever's in Customer.preferred_language (or a
    request override) to exactly one of "English" | "Hindi" | "Hinglish" —
    the single source of truth for response language everywhere (spec:
    picked once on the landing page, must stay uniform across every
    LLM-generated response, regardless of what language the customer
    types in). Unrecognized/missing values default to English rather than
    guessing."""
    value = (language or "").strip().lower()
    if value.startswith("hinglish"):
        return "Hinglish"
    if value.startswith("hindi") or value in ("hi", "hin"):
        return "Hindi"
    return "English"


class LLMService:
    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            settings = get_settings()
            if not settings.llm_api_key:
                return None
            if settings.llm_provider == "anthropic":
                from app.integrations.llm.anthropic_provider import AnthropicProvider

                self._provider = AnthropicProvider()
            elif settings.llm_provider == "gemini":
                from app.integrations.llm.gemini_provider import GeminiProvider

                self._provider = GeminiProvider()
            elif settings.llm_provider == "groq":
                from app.integrations.llm.groq_provider import GroqProvider

                self._provider = GroqProvider()
            else:
                raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
        return self._provider

    def understand_complaint(self, message: str, customer_context: dict) -> dict:
        """Returns intent/entities. Falls back to a conservative, clearly
        degraded heuristic if the LLM is unavailable or errors — never
        invents financial facts in either path (spec section 43)."""
        provider = self._get_provider()

        if provider is not None:
            try:
                user_prompt = (
                    f"Customer message: {message!r}\n\n"
                    f"Known customer context (JSON): {json.dumps(customer_context)}"
                )
                raw = provider.complete_json(
                    prompts.UNDERSTAND_SYSTEM_PROMPT, user_prompt, prompts.UNDERSTAND_SCHEMA_HINT
                )
                parsed = json.loads(_extract_json(raw))
                parsed.setdefault("extracted_entities", {})
                return parsed
            except Exception:
                logger.exception("LLM understand_complaint failed; using fallback heuristic")

        return self._fallback_understand(message)

    def _fallback_understand(self, message: str) -> dict:
        entities = {"transaction_id": None, "amount": None, "merchant_hint": None}
        txn_match = TXN_ID_PATTERN.search(message)
        upi_ref_match = UPI_REF_PATTERN.search(message)
        if txn_match:
            entities["transaction_id"] = txn_match.group(0).upper()
        elif upi_ref_match:
            entities["transaction_id"] = upi_ref_match.group(0)
        amount_match = AMOUNT_PATTERN.search(message)
        if amount_match:
            try:
                entities["amount"] = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                pass

        has_sensitive = contains_sensitive_credential(message)
        intent = "UNKNOWN"
        confidence = "LOW"
        lowered = message.lower()
        follow_up_phrases = ["abhi tak", "nahi aaya", "nahi aaye", "still not", "haven't received", "not received"]
        if not has_sensitive:
            if entities["amount"] or "fail" in lowered or "kat" in lowered or "refund" in lowered:
                intent = "FAILED_PAYMENT" if (entities["amount"] or entities["transaction_id"]) else "FOLLOW_UP_ON_EXISTING_CASE"
                confidence = "MEDIUM"
            elif any(phrase in lowered for phrase in follow_up_phrases):
                intent = "FOLLOW_UP_ON_EXISTING_CASE"
                confidence = "MEDIUM"

        return {
            "intent": intent,
            "extracted_entities": entities,
            "contains_sensitive_credential": has_sensitive,
            "confidence": confidence,
            "degraded": True,
        }

    def generate_response(self, verified_facts: dict, language: str = "English", semantic_context: list[str] | None = None) -> str:
        """`semantic_context` (optional): plain-text snippets from Cognee's
        semantic memory, passed as background color only. Explicitly NOT
        part of verified_facts — the prompt tells the model these are
        historical context, not authoritative, so it can't be mistaken for
        a financial fact to restate (architectural rule: Cognee never
        overrides verified facts)."""
        provider = self._get_provider()
        language = normalize_language(language)
        if provider is not None:
            try:
                user_prompt = (
                    f"Customer's selected response language (fixed on the landing page — MUST be used "
                    f"for this entire reply regardless of what language the customer's own message was "
                    f"in): {language}\n\n"
                    f"Verified facts (JSON) — the only source of financial/status truth: {json.dumps(verified_facts)}"
                )
                if semantic_context:
                    user_prompt += (
                        "\n\nRelevant history (context only, NOT authoritative — do not treat as current "
                        f"status): {json.dumps(semantic_context)}"
                    )
                return provider.complete_text(prompts.RESPONSE_SYSTEM_PROMPT, user_prompt).strip()
            except Exception:
                logger.exception("LLM generate_response failed; using template fallback")

        return self._fallback_response(verified_facts, language)

    def _fallback_response(self, facts: dict, language: str) -> str:
        # Deterministic templates in all 3 supported languages so the core
        # loop still works end-to-end, uniformly, when no LLM key is
        # configured (spec section 43). `language` must already be
        # normalize_language()'d by the caller.
        situation = facts.get("situation")

        if situation == "case_created":
            if language == "Hindi":
                return (
                    f"मैंने आपका ट्रांजेक्शन चेक किया है। ₹{facts['amount']:.0f} डेबिट हो चुका है, लेकिन "
                    f"मर्चेंट को पेमेंट प्राप्त नहीं हुआ है। रिफंड की अपेक्षित तारीख {facts['deadline']} है। "
                    f"मैं उस तारीख को स्वचालित रूप से दोबारा जांच करूंगा।"
                )
            if language == "Hinglish":
                return (
                    f"Maine aapka transaction check kiya. ₹{facts['amount']:.0f} debit hua hai, "
                    f"lekin merchant ko payment receive nahi hua. Expected refund date "
                    f"{facts['deadline']} hai. Main us date par automatically dobara check karunga."
                )
            return (
                f"I checked your transaction. ₹{facts['amount']:.0f} was debited but the merchant "
                f"hasn't received it yet. Expected refund date is {facts['deadline']}. "
                f"I'll automatically recheck on that date."
            )

        if situation == "dispute_raised":
            compensation = facts.get("compensation", 0)
            if language == "Hindi":
                return (
                    f"रिफंड अभी तक प्राप्त नहीं हुआ है, इसलिए मैंने आपके केस के लिए डिस्प्यूट दर्ज कर दिया है। "
                    f"देरी का मुआवज़ा ₹{compensation:.0f} है। मैंने केस अपडेट कर दिया है।"
                )
            if language == "Hinglish":
                return (
                    "Refund abhi tak receive nahi hua, isliye maine aapke case ke liye dispute raise "
                    f"kar diya hai. Delay compensation ₹{compensation:.0f} hai. "
                    "Maine case update kar diya hai."
                )
            return (
                "The refund hasn't arrived, so I've raised a dispute for your case. "
                f"Delay compensation is ₹{compensation:.0f}. I've updated your case."
            )

        if situation == "resolved":
            if language == "Hindi":
                return "आपका रिफंड प्राप्त हो गया है। केस अब समाधान हो चुका है।"
            if language == "Hinglish":
                return "Aapka refund receive ho gaya hai. Case ab resolved hai."
            return "Your refund has been received. The case is now resolved."

        if situation == "human_escalated":
            if language == "Hindi":
                return (
                    "यह मामला अधिक मूल्य का है इसलिए मैंने इसे हमारी सपोर्ट टीम के पास समीक्षा के लिए भेज "
                    "दिया है। वे जल्द ही आपसे संपर्क करेंगे।"
                )
            if language == "Hinglish":
                return (
                    "Yeh case zyada value ka hai isliye maine ise humare support team ko review ke liye "
                    "bhej diya hai. Woh jaldi hi aapse contact karenge."
                )
            return (
                "This case needs human review, so I've routed it to our support team. "
                "They'll follow up with you shortly."
            )

        if situation == "clarification_needed":
            return facts.get("clarification_question", "Could you share more detail about the transaction?")

        return "I've noted your message and I'm looking into it."

    def summarize_case(self, case_context: dict) -> str:
        provider = self._get_provider()
        if provider is not None:
            try:
                return provider.complete_text(
                    prompts.SUMMARY_SYSTEM_PROMPT, json.dumps(case_context)
                ).strip()
            except Exception:
                logger.exception("LLM summarize_case failed; using fallback summary")

        return (
            f"Case {case_context.get('case_id')} — {case_context.get('status')}. "
            f"Escalation reason: {case_context.get('escalation_reason') or 'n/a'}."
        )


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM response")
    return raw[start : end + 1]


llm_service = LLMService()
