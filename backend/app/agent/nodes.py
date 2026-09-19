"""LangGraph node functions implementing the core loop (spec section 12.2).

LLM understands. Rules decide policy. Tools act. Database remembers.
Every node either calls the LLM (understanding/response text only) or calls
a tool/service — never both invents *and* records a financial fact.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.agent import tools
from app.agent.state import NishchintState
from app.integrations.llm.llm_service import contains_sensitive_credential, is_greeting, llm_service, normalize_language
from app.rules.engine import get_policy_engine
from app.services.case_service import case_service
from app.services.memory_service import memory_service
from app.services.simulation_clock import simulation_clock_service

policy_engine = get_policy_engine()

SUSPICIOUS_KEYWORDS = ["hack", "fraud", "unauthorized", "not me", "maine nahi kiya", "chori"]

SECURITY_WARNING_EN = "For your security, please don't share your UPI PIN or OTP. I don't need it to investigate your transaction."
SECURITY_WARNING_HI = "अपनी सुरक्षा के लिए कृपया अपना यूपीआई पिन या ओटीपी साझा न करें। आपका ट्रांजेक्शन जांचने के लिए मुझे इसकी आवश्यकता नहीं है।"
SECURITY_WARNING_HINGLISH = "Aapki suraksha ke liye, kripya apna UPI PIN ya OTP share na karein. Transaction investigate karne ke liye mujhe iski zaroorat nahi hai."

GREETING_RESPONSE_EN = "Hi! What's your query?"
GREETING_RESPONSE_HI = "नमस्ते! आपकी क्या समस्या है?"
GREETING_RESPONSE_HINGLISH = "Hi! Aapki kya query hai?"

OFF_TOPIC_RESPONSE_EN = "I can only help with Paytm payments, bills, and account support. What can I help you with on that front?"
OFF_TOPIC_RESPONSE_HI = "मैं सिर्फ Paytm पेमेंट्स, बिल्स और अकाउंट सपोर्ट में मदद कर सकता हूं। इसमें आपकी क्या मदद कर सकता हूं?"
OFF_TOPIC_RESPONSE_HINGLISH = "Main sirf Paytm payments, bills aur account support mein madad kar sakta hoon. Isme aapki kya madad kar sakta hoon?"


def understand_complaint(state: NishchintState) -> dict:
    db = state["db"]
    message = state["user_message"]

    if contains_sensitive_credential(message):
        tools.write_audit_event(
            db, event_type="SENSITIVE_CREDENTIAL_DETECTED", actor="AGENT",
            case_id=state.get("case_id"), customer_id=state["customer_id"],
        )
        return {
            "contains_sensitive_credential": True,
            "intent": "SECURITY_GUARD",
            "extracted_entities": {},
        }

    # Zero-LLM, zero-DB fast path for a bare "hi"/"hello" — the common case,
    # and it must not fall into decide_next_action's NEEDS_CLARIFICATION
    # branch, which would nonsensically ask a greeting for a transaction ID.
    if is_greeting(message):
        return {
            "intent": "GREETING",
            "extracted_entities": {},
            "contains_sensitive_credential": False,
            "is_fast_reply": True,
        }

    result = llm_service.understand_complaint(message, {})
    intent = result.get("intent", "UNKNOWN")
    return {
        "intent": intent,
        "extracted_entities": result.get("extracted_entities", {}),
        "contains_sensitive_credential": False,
        # OFF_TOPIC still needed one LLM call to classify, but from here it
        # skips context assembly, transaction lookup, and the second
        # (response-generation) LLM call — spec: stay scoped to Paytm
        # payments support, don't deep-engage outside that.
        "is_fast_reply": intent == "OFF_TOPIC",
    }


def retrieve_context(state: NishchintState) -> dict:
    db = state["db"]
    context = tools.assemble_context(db, state["customer_id"], state["user_message"], state.get("case_id"))
    tools.write_audit_event(
        db, event_type="CONTEXT_RETRIEVED", actor="AGENT", customer_id=state["customer_id"],
        metadata={
            "open_cases": len(context.get("active_cases", [])),
            "semantic_memory_hits": len(context.get("semantic_memory", [])),
        },
    )
    return {"customer_context": context}


def identify_transaction(state: NishchintState) -> dict:
    db = state["db"]
    entities = state.get("extracted_entities", {}) or {}
    match = tools.find_relevant_transaction(
        db,
        state["customer_id"],
        transaction_id=entities.get("transaction_id"),
        amount=entities.get("amount"),
        merchant_hint=entities.get("merchant_hint"),
    )
    return {
        "transaction_match_status": match["status"],
        "transaction": match["transaction"],
        "transaction_candidates": match["candidates"],
    }


def investigate_transaction(state: NishchintState) -> dict:
    db = state["db"]
    transaction = state.get("transaction")
    if not transaction:
        return {"transaction": None}
    verified = tools.get_transaction(db, transaction["id"])
    tools.write_audit_event(
        db, event_type="TRANSACTION_VERIFIED", actor="AGENT",
        case_id=state.get("case_id"), customer_id=state["customer_id"],
        metadata={"transaction_id": verified["id"], "status": verified["status"]},
    )
    return {"transaction": verified}


def evaluate_policy(state: NishchintState) -> dict:
    db = state["db"]
    transaction = state.get("transaction")
    if not transaction:
        return {"policy_result": None}
    now = simulation_clock_service.now(db)
    policy_result = tools.evaluate_policy(transaction, now)
    tools.write_audit_event(
        db, event_type="RULE_EVALUATED", actor="RULE_ENGINE",
        case_id=state.get("case_id"), customer_id=state["customer_id"],
        metadata=policy_result,
    )
    return {"policy_result": policy_result}


def decide_next_action(state: NishchintState) -> dict:
    db = state["db"]
    message = state["user_message"].lower()
    transaction = state.get("transaction")
    match_status = state.get("transaction_match_status")

    if match_status in ("AMBIGUOUS", "NOT_FOUND"):
        return {"decision": "NEEDS_CLARIFICATION", "next_action": "ASK_CUSTOMER"}

    if any(kw in message for kw in SUSPICIOUS_KEYWORDS):
        return {"decision": "ESCALATE_HUMAN", "escalation_reason": "SUSPICIOUS_LANGUAGE"}

    if transaction and policy_engine.is_high_value(transaction["amount"]):
        return {"decision": "ESCALATE_HUMAN", "escalation_reason": "HIGH_VALUE_TRANSACTION"}

    policy_result = state.get("policy_result") or {}
    if not policy_result.get("applicable"):
        return {"decision": "RESOLVED", "next_action": "INFORM_CUSTOMER"}

    if policy_result.get("is_breached"):
        return {"decision": "RAISE_DISPUTE", "next_action": "RAISE_DISPUTE"}

    return {"decision": "FOLLOW_UP", "next_action": "SCHEDULE_FOLLOWUP"}


def execute_action(state: NishchintState) -> dict:
    db = state["db"]
    customer_id = state["customer_id"]
    decision = state.get("decision")
    transaction = state.get("transaction")
    actions_taken: list[str] = []

    customer_context = state.get("customer_context") or {}
    customer_name = (customer_context.get("customer") or {}).get("name") or customer_id

    case_id = state.get("case_id")
    is_new_case = False
    if not case_id and transaction is not None:
        ticket = tools.create_ticket(db, customer_id, transaction["id"], state.get("intent") or "FAILED_PAYMENT")
        case_id = ticket["case_id"]
        is_new_case = ticket["created"]
        actions_taken.append("TICKET_CREATED")

    updates: dict = {"case_id": case_id, "actions_taken": actions_taken, "is_new_case": is_new_case}

    if case_id is None:
        # No transaction identified (clarification path) — nothing to act on yet.
        return updates

    if is_new_case:
        # Memory write point 2 (spec section 8): case created. Only on a
        # genuinely new case — a reused open case (contextual follow-up)
        # doesn't get a duplicate "case created" memory.
        memory_service.remember_case_event(
            db, customer_name, case_id, transaction, state.get("policy_result"), event_type="CASE_CREATED"
        )

    if decision == "ESCALATE_HUMAN":
        tools.escalate_to_human(db, case_id, state.get("escalation_reason") or "AMBIGUOUS_CASE")
        actions_taken.append("HUMAN_ESCALATED")

    elif decision == "RAISE_DISPUTE":
        policy_result = state.get("policy_result") or {}
        case_service.advance_to(db, case_id, "ACTION_TAKEN", actor="AGENT")
        dispute = tools.raise_dispute(
            db, case_id, transaction["id"], "REFUND_DEADLINE_BREACHED", policy_result.get("compensation") or 0
        )
        case_service.advance_to(db, case_id, "DISPUTE_RAISED", actor="AGENT", metadata={"dispute_id": dispute["dispute_id"]})
        updates["dispute_id"] = dispute["dispute_id"]
        actions_taken.append("DISPUTE_RAISED")
        # Memory write point 4 (spec section 8): dispute raised.
        memory_service.remember_resolution(
            db, case_id, transaction, "DISPUTE_RAISED", policy_result, dispute_id=dispute["dispute_id"]
        )

    elif decision == "RESOLVED":
        case_service.advance_to(db, case_id, "ACTION_TAKEN", actor="AGENT")
        case_service.advance_to(db, case_id, "RESOLVED", actor="AGENT")
        actions_taken.append("RESOLVED")
        # Memory write point 6 (spec section 8): case resolved.
        memory_service.remember_resolution(db, case_id, transaction, "RESOLVED")

    elif decision == "FOLLOW_UP":
        case_service.advance_to(db, case_id, "ACTION_TAKEN", actor="AGENT")
        actions_taken.append("ACTION_TAKEN")

    updates["actions_taken"] = actions_taken
    return updates


def schedule_followup_node(state: NishchintState) -> dict:
    db = state["db"]
    if state.get("decision") != "FOLLOW_UP":
        return {"followup_id": state.get("followup_id")}
    case_id = state["case_id"]
    policy_result = state.get("policy_result") or {}
    deadline = policy_result.get("deadline")
    scheduled_for = (
        datetime.fromisoformat(deadline).replace(hour=9, minute=0, second=0)
        if deadline
        else simulation_clock_service.now(db) + timedelta(days=1)
    )
    followup = tools.schedule_followup(db, case_id, scheduled_for)
    case_service.advance_to(db, case_id, "WAITING_FOR_RESOLUTION", actor="AGENT")
    actions_taken = list(state.get("actions_taken") or [])
    actions_taken.append("FOLLOWUP_SCHEDULED")
    return {"followup_id": followup["followup_id"], "actions_taken": actions_taken}


def write_audit(state: NishchintState) -> dict:
    db = state["db"]
    tools.write_audit_event(
        db, event_type="DECISION_MADE", actor="AGENT",
        case_id=state.get("case_id"), customer_id=state["customer_id"],
        metadata={"decision": state.get("decision"), "intent": state.get("intent")},
    )
    return {"decision": state.get("decision")}


def generate_response(state: NishchintState) -> dict:
    customer_context = state.get("customer_context") or {}
    # Fast-path replies (greeting/off-topic/sensitive-credential) skip
    # retrieve_context entirely, so customer_context won't have the
    # customer's language — fall back to what chat.py loaded up front.
    language = normalize_language(
        (customer_context.get("customer") or {}).get("preferred_language") or state.get("preferred_language")
    )
    decision = state.get("decision")
    transaction = state.get("transaction")
    policy_result = state.get("policy_result") or {}
    semantic_hits = customer_context.get("semantic_memory") or []
    semantic_context = [h["text"] for h in semantic_hits if h.get("text")] or None

    if state.get("contains_sensitive_credential"):
        warning = {"Hindi": SECURITY_WARNING_HI, "Hinglish": SECURITY_WARNING_HINGLISH}.get(language, SECURITY_WARNING_EN)
        return {"assistant_response": warning}

    if state.get("intent") == "GREETING":
        return {"assistant_response": {"Hindi": GREETING_RESPONSE_HI, "Hinglish": GREETING_RESPONSE_HINGLISH}.get(language, GREETING_RESPONSE_EN)}

    if state.get("intent") == "OFF_TOPIC":
        return {"assistant_response": {"Hindi": OFF_TOPIC_RESPONSE_HI, "Hinglish": OFF_TOPIC_RESPONSE_HINGLISH}.get(language, OFF_TOPIC_RESPONSE_EN)}

    if decision == "NEEDS_CLARIFICATION":
        candidates = state.get("transaction_candidates") or []
        if candidates:
            options = "; ".join(f"₹{c['amount']:.0f} ({c.get('merchant_name') or 'P2P'})" for c in candidates)
            if language == "Hindi":
                question = f"क्या आप इनमें से किसी एक ट्रांजेक्शन की बात कर रहे हैं: {options}?"
            elif language == "Hinglish":
                question = f"Kya aap in transactions me se kisi ek ki baat kar rahe hain: {options}?"
            else:
                question = f"Are you referring to one of these transactions: {options}?"
        else:
            if language == "Hindi":
                question = "कृपया ट्रांजेक्शन आईडी या राशि बताएं ताकि मैं इसकी जांच कर सकूं।"
            elif language == "Hinglish":
                question = "Kripya transaction ID ya amount bataiye taaki main isko check kar sakoon."
            else:
                question = "Could you share the transaction ID or the amount so I can look into it?"
        return {"assistant_response": question}

    if decision == "ESCALATE_HUMAN":
        facts = {"situation": "human_escalated"}
        return {"assistant_response": llm_service.generate_response(facts, language, semantic_context)}

    if decision == "RAISE_DISPUTE":
        facts = {"situation": "dispute_raised", "compensation": policy_result.get("compensation") or 0}
        return {"assistant_response": llm_service.generate_response(facts, language, semantic_context)}

    if decision == "RESOLVED":
        facts = {"situation": "resolved"}
        return {"assistant_response": llm_service.generate_response(facts, language, semantic_context)}

    if decision == "FOLLOW_UP" and transaction:
        facts = {"situation": "case_created", "amount": transaction["amount"], "deadline": policy_result.get("deadline")}
        return {"assistant_response": llm_service.generate_response(facts, language, semantic_context)}

    return {"assistant_response": "I've noted your message and I'm looking into it."}
