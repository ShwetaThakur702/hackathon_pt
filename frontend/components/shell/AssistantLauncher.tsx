"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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

const EASE = [0.16, 1, 0.3, 1] as const;

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

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            key="fab"
            initial={{ opacity: 0, scale: 0.7, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.7, y: 20 }}
            transition={{ duration: 0.25, ease: EASE }}
            whileHover={{ scale: 1.05, boxShadow: "0 12px 24px -8px rgba(0,41,112,0.35)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setOpen(true)}
            className="fixed z-40 right-4 bottom-20 lg:bottom-6 flex items-center gap-2 rounded-full bg-brand-dark text-white pl-4 pr-5 py-3 shadow-lg"
            aria-label="Open Nishchint assistant"
          >
            <motion.span
              animate={{ rotate: [0, 15, -10, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, repeatDelay: 2, ease: "easeInOut" }}
            >
              <SparkleIcon className="w-5 h-5" />
            </motion.span>
            <span className="text-sm font-medium hidden sm:inline">Nishchint</span>
            {pageContext && <span className="h-2 w-2 rounded-full bg-brand animate-pulse" />}
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.97 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="fixed z-50 right-0 bottom-0 lg:right-6 lg:bottom-6 w-full lg:w-96 h-[85vh] lg:h-[600px] lg:rounded-2xl bg-white shadow-2xl flex flex-col border border-border origin-bottom-right"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-brand-dark text-white lg:rounded-t-2xl shrink-0">
              <div className="flex items-center gap-2">
                <SparkleIcon className="w-4 h-4" />
                <div>
                  <div className="text-sm font-semibold">Nishchint</div>
                  <div className="text-[11px] text-white/70">Autonomous resolution assistant</div>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="tap-target flex items-center justify-center rounded-full hover:bg-white/10 transition-colors duration-150"
                aria-label="Close assistant"
              >
                <CloseIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: EASE }}
                  className="space-y-3"
                >
                  <div className="rounded-2xl bg-surface px-4 py-3 text-sm text-ink">
                    {pageContext ? `I can help with ${pageContext.summary}.` : `Hi ${customer.name.split(" ")[0]}. How can I help?`}
                  </div>
                  {pageContext && (
                    <motion.button
                      whileHover={{ scale: 1.015 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => send(pageContext.suggestedMessage)}
                      className="w-full text-left rounded-xl border border-brand-light bg-brand-light/60 px-4 py-3 text-sm text-brand-dark font-medium hover:bg-brand-light transition-colors duration-150"
                    >
                      {pageContext.suggestedMessage}
                    </motion.button>
                  )}
                </motion.div>
              )}
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.25, ease: EASE }}
                  className={`flex flex-col ${m.sender === "CUSTOMER" ? "items-end" : "items-start"}`}
                >
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
                </motion.div>
              ))}
              {sending && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-1.5 text-xs text-ink-secondary"
                >
                  <span>Nishchint is checking</span>
                  <span className="flex gap-0.5">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="h-1 w-1 rounded-full bg-ink-secondary"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </span>
                </motion.div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="border-t border-border p-3 flex gap-2 shrink-0">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(input)}
                placeholder="Type in English, Hindi, or Hinglish…"
                className="flex-1 rounded-lg border border-border px-3 py-2 text-sm outline-none transition-shadow duration-150 focus:ring-2 focus:ring-brand focus:border-transparent"
              />
              <MicButton onTranscribed={(text) => setInput((prev) => (prev ? `${prev} ${text}` : text))} />
              <button onClick={() => send(input)} disabled={sending} className="btn-primary btn-md">
                Send
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
