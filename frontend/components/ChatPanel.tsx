"use client";

import { useEffect, useRef, useState } from "react";
import { getCase, sendChatMessage } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { CaseDetail, ContextUsed } from "@/types";
import CaseStatusCard from "./CaseStatusCard";
import MicButton from "./MicButton";
import SimulationControls from "./SimulationControls";

interface LocalMessage {
  sender: "CUSTOMER" | "ASSISTANT";
  text: string;
  contextUsed?: ContextUsed | null;
}

function contextBadgeLabel(ctx: ContextUsed): string | null {
  const parts: string[] = [];
  if (ctx.previous_case_found) parts.push("Previous case found");
  if (ctx.semantic_memory_hits > 0) parts.push(`${ctx.semantic_memory_hits} memory match${ctx.semantic_memory_hits > 1 ? "es" : ""}`);
  return parts.length ? parts.join(" · ") : null;
}

export default function ChatPanel() {
  const { customerId, customer } = useCustomer();
  const [caseId, setCaseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCaseId(null);
    setMessages([]);
    setCaseDetail(null);
  }, [customerId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshCase(id: string) {
    try {
      const detail = await getCase(id);
      setCaseDetail(detail);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [...m, { sender: "CUSTOMER", text }]);
    setSending(true);
    try {
      const resp = await sendChatMessage(customerId, text, caseId);
      setMessages((m) => [...m, { sender: "ASSISTANT", text: resp.message, contextUsed: resp.context_used }]);
      if (resp.case_id) {
        setCaseId(resp.case_id);
        await refreshCase(resp.case_id);
      }
    } catch (err) {
      console.error(err);
      setMessages((m) => [...m, { sender: "ASSISTANT", text: "Sorry, something went wrong reaching the server." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
      <div className="card flex flex-col h-[70vh]">
        <div className="flex items-center justify-between border-b border-border p-4">
          <div>
            <div className="font-semibold text-ink">Nishchint</div>
            <div className="text-xs text-ink-secondary">Your autonomous resolution assistant</div>
          </div>
          <span className="badge bg-surface text-ink-secondary">{customer.name}</span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-sm text-ink-secondary italic">Hi {customer.name.split(" ")[0]}. How can I help?</div>
          )}
          {messages.map((m, i) => {
            const badge = m.sender === "ASSISTANT" && m.contextUsed ? contextBadgeLabel(m.contextUsed) : null;
            return (
              <div key={i} className={`flex flex-col ${m.sender === "CUSTOMER" ? "items-end" : "items-start"}`}>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                    m.sender === "CUSTOMER" ? "bg-brand-dark text-white rounded-br-sm" : "bg-surface text-ink rounded-bl-sm"
                  }`}
                >
                  {m.text}
                </div>
                {badge && (
                  <span className="mt-1 text-[11px] text-brand-dark bg-brand-light rounded-full px-2 py-0.5">
                    🧠 {badge}
                  </span>
                )}
              </div>
            );
          })}
          {sending && <div className="text-xs text-ink-secondary">Nishchint is investigating…</div>}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-border p-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Message… (e.g. Mere 2400 kat gaye but payment fail dikha raha hai)"
            className="flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
          />
          <MicButton onTranscribed={(text) => setInput((prev) => (prev ? `${prev} ${text}` : text))} />
          <button
            onClick={handleSend}
            disabled={sending}
            className="rounded-lg bg-brand-dark text-white px-4 py-2 text-sm font-medium hover:bg-brand-navy disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {caseDetail ? (
          <CaseStatusCard detail={caseDetail} />
        ) : (
          <div className="card p-5 text-sm text-ink-secondary">No active case yet.</div>
        )}
        <SimulationControls onChanged={() => caseId && refreshCase(caseId)} />
      </div>
    </div>
  );
}
