"use client";

import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import type { ContextUsed } from "@/types";
import MicButton from "@/components/MicButton";
import { CloseIcon, SparkleIcon } from "./icons";

interface LocalMessage {
  sender: "CUSTOMER" | "ASSISTANT";
  text: string;
  contextUsed?: ContextUsed | null;
}

export default function AssistantLauncher() {
  const { pageContext, open, setOpen } = useAssistant();
  const { customerId, customer } = useCustomer();
  const [caseId, setCaseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Fresh conversation whenever the demo customer changes.
    setCaseId(null);
    setMessages([]);
  }, [customerId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setInput("");
    setMessages((m) => [...m, { sender: "CUSTOMER", text: trimmed }]);
    setSending(true);
    try {
      const resp = await sendChatMessage(customerId, trimmed, caseId);
      setMessages((m) => [...m, { sender: "ASSISTANT", text: resp.message, contextUsed: resp.context_used }]);
      if (resp.case_id) setCaseId(resp.case_id);
    } catch {
      setMessages((m) => [...m, { sender: "ASSISTANT", text: "Sorry, I couldn't reach the server just now." }]);
    } finally {
      setSending(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed z-40 right-4 bottom-20 lg:bottom-6 flex items-center gap-2 rounded-full bg-brand-dark text-white pl-4 pr-5 py-3 shadow-lg hover:bg-brand-navy transition-colors"
        aria-label="Open Nishchint assistant"
      >
        <SparkleIcon className="w-5 h-5" />
        <span className="text-sm font-medium hidden sm:inline">Nishchint</span>
      </button>
    );
  }

  return (
    <div className="fixed z-50 right-0 bottom-0 lg:right-6 lg:bottom-6 w-full lg:w-96 h-[85vh] lg:h-[600px] lg:rounded-2xl bg-white shadow-2xl flex flex-col border border-border">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-brand-dark text-white lg:rounded-t-2xl">
        <div className="flex items-center gap-2">
          <SparkleIcon className="w-4 h-4" />
          <div>
            <div className="text-sm font-semibold">Nishchint</div>
            <div className="text-[11px] text-white/70">Autonomous resolution assistant</div>
          </div>
        </div>
        <button onClick={() => setOpen(false)} className="tap-target flex items-center justify-center" aria-label="Close assistant">
          <CloseIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-3">
            <div className="rounded-2xl bg-surface px-4 py-3 text-sm text-ink">
              {pageContext ? `I can help with ${pageContext.summary}.` : `Hi ${customer.name.split(" ")[0]}. How can I help?`}
            </div>
            {pageContext && (
              <button
                onClick={() => send(pageContext.suggestedMessage)}
                className="w-full text-left rounded-xl border border-brand-light bg-brand-light/60 px-4 py-3 text-sm text-brand-dark font-medium hover:bg-brand-light"
              >
                {pageContext.suggestedMessage}
              </button>
            )}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.sender === "CUSTOMER" ? "items-end" : "items-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                m.sender === "CUSTOMER" ? "bg-brand-dark text-white rounded-br-sm" : "bg-surface text-ink rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
            {m.sender === "ASSISTANT" && m.contextUsed && (m.contextUsed.previous_case_found || m.contextUsed.semantic_memory_hits > 0) && (
              <span className="mt-1 text-[11px] text-brand-dark bg-brand-light rounded-full px-2 py-0.5">
                🧠 {m.contextUsed.previous_case_found ? "Previous case found" : `${m.contextUsed.semantic_memory_hits} memory match(es)`}
              </span>
            )}
          </div>
        ))}
        {sending && <div className="text-xs text-ink-secondary">Nishchint is checking…</div>}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-border p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Type in English, Hindi, or Hinglish…"
          className="flex-1 rounded-lg border border-border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand"
        />
        <MicButton onTranscribed={(text) => setInput((prev) => (prev ? `${prev} ${text}` : text))} />
        <button
          onClick={() => send(input)}
          disabled={sending}
          className="rounded-lg bg-brand-dark text-white px-4 py-2 text-sm font-medium hover:bg-brand-navy disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
