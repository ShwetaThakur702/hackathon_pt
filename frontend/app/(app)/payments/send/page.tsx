"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { sendPayment } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import type { Transaction } from "@/types";
import CopyReferenceId from "@/components/CopyReferenceId";
import { SparkleIcon } from "@/components/shell/icons";

interface Recipient {
  name: string;
  type: "CONTACT" | "MERCHANT";
  /** Only merchants suggest a default amount — a contact starts blank. */
  suggestedAmount?: number;
}

const RECIPIENTS: Recipient[] = [
  { name: "Rohit", type: "CONTACT" },
  { name: "Ananya", type: "CONTACT" },
  { name: "Karan", type: "CONTACT" },
  { name: "Apollo Medicals", type: "MERCHANT", suggestedAmount: 2400 },
];

type Step = "recipient" | "amount" | "processing" | "result";
type NishchintPhase = "idle" | "detecting" | "checking" | "revealed";

const EASE = [0.16, 1, 0.3, 1] as const;
const stepMotion = {
  initial: { opacity: 0, x: 16 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -16 },
  transition: { duration: 0.25, ease: EASE },
};

const CHECK_STEPS = ["Transaction identified", "Current status verified", "Resolution policy checked"];

export default function SendMoneyPage() {
  const { customerId } = useCustomer();
  const { setPageContext, setOpen } = useAssistant();
  const [step, setStep] = useState<Step>("recipient");
  const [recipient, setRecipient] = useState<Recipient | null>(null);
  const [amount, setAmount] = useState("");
  const [result, setResult] = useState<Transaction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nishchintPhase, setNishchintPhase] = useState<NishchintPhase>("idle");

  function pickRecipient(r: Recipient) {
    setRecipient(r);
    setAmount(r.suggestedAmount ? String(r.suggestedAmount) : "");
    setStep("amount");
  }

  async function pay() {
    const numericAmount = Number(amount);
    if (!recipient || !numericAmount || numericAmount <= 0) return;
    setStep("processing");
    setError(null);
    try {
      // Real backend call — the outcome (and the UPI Reference ID) comes
      // from the mock payment gateway, never simulated only in React state.
      const txn = await sendPayment(customerId, recipient.name, recipient.type, numericAmount);
      setResult(txn);
      setStep("result");
    } catch {
      setError("I couldn't reach the payment service just now. Nothing was charged.");
      setStep("amount");
    }
  }

  useEffect(() => {
    if (step !== "result" || !result) return;
    if (result.status === "FAILED") {
      setPageContext({
        summary: `this ₹${result.amount.toLocaleString("en-IN")} ${result.merchant_name || "payment"} that just failed`,
        suggestedMessage: `I have an issue with my ₹${result.amount} payment${result.merchant_name ? " to " + result.merchant_name : ""} (UPI Reference ID ${result.upi_ref_no}).`,
      });
    }
    return () => setPageContext(null);
  }, [step, result, setPageContext]);

  // Staged reveal: Nishchint visibly "notices" the failure, then works
  // through it, before the resolution CTA appears — same real detection,
  // just paced so it's felt rather than snapped into place.
  useEffect(() => {
    if (step !== "result" || result?.status !== "FAILED") {
      setNishchintPhase("idle");
      return;
    }
    setNishchintPhase("detecting");
    const t1 = setTimeout(() => setNishchintPhase("checking"), 900);
    const t2 = setTimeout(() => setNishchintPhase("revealed"), 900 + CHECK_STEPS.length * 450 + 300);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [step, result]);

  function startOver() {
    setStep("recipient");
    setRecipient(null);
    setAmount("");
    setResult(null);
    setError(null);
  }

  return (
    <div className="page-shell max-w-xl space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">Send Money</h1>
        {step !== "recipient" && step !== "processing" && (
          <button onClick={startOver} className="text-sm text-brand-dark font-medium hover:underline transition-all">
            Start over
          </button>
        )}
      </div>

      <AnimatePresence mode="wait">
        {step === "recipient" && (
          <motion.div key="recipient" {...stepMotion} className="card p-5">
            <h2 className="text-sm font-semibold text-ink-secondary mb-3">Contacts</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 stagger-list">
              {RECIPIENTS.map((r) => (
                <motion.button
                  key={r.name}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => pickRecipient(r)}
                  className="stagger-item tap-target flex flex-col items-center gap-2 rounded-xl border border-border py-5 px-2 text-sm text-ink
                    transition-colors duration-200 hover:border-brand hover:bg-brand-light/40 hover:shadow-sm"
                >
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-light text-brand-dark text-lg font-semibold">
                    {r.name.charAt(0)}
                  </span>
                  <span className="font-medium text-center">{r.name}</span>
                  <span className="badge bg-surface text-ink-secondary text-[10px]">{r.type === "MERCHANT" ? "Merchant" : "Contact"}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {step === "amount" && recipient && (
          <motion.div key="amount" {...stepMotion} className="card p-6 space-y-5">
            <div className="flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-light text-brand-dark text-lg font-semibold">
                {recipient.name.charAt(0)}
              </span>
              <div>
                <div className="text-sm font-semibold text-ink">{recipient.name}</div>
                <div className="text-xs text-ink-secondary">{recipient.type === "MERCHANT" ? "Merchant" : "Contact"}</div>
              </div>
            </div>

            <div>
              <label className="text-xs text-ink-secondary" htmlFor="amount">
                Amount
              </label>
              <div className="flex items-center gap-1 mt-1 border-b-2 border-brand-dark pb-1 transition-colors duration-200 focus-within:border-brand">
                <span className="text-2xl font-bold text-ink">₹</span>
                <input
                  id="amount"
                  type="number"
                  min={1}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0"
                  autoFocus
                  className="text-2xl font-bold text-ink outline-none w-full bg-transparent"
                />
              </div>
            </div>

            <div className="text-xs text-ink-secondary">Payment method: UPI</div>

            {error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-danger">
                {error}
              </motion.div>
            )}

            <button onClick={pay} disabled={!amount || Number(amount) <= 0} className="btn-primary btn-lg w-full">
              Pay ₹{amount || "0"}
            </button>
          </motion.div>
        )}

        {step === "processing" && (
          <motion.div key="processing" {...stepMotion} className="card p-10 flex flex-col items-center gap-3 text-center">
            <motion.div
              className="h-10 w-10 rounded-full border-[3px] border-brand-light border-t-brand-dark"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
            />
            <p className="text-sm text-ink-secondary">Processing payment…</p>
          </motion.div>
        )}

        {step === "result" && result && (
          <motion.div key="result" {...stepMotion} className="space-y-4">
            <div className="card p-6 text-center">
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 15, delay: 0.1 }}
                className={`inline-flex h-14 w-14 items-center justify-center rounded-full text-2xl mb-3 ${
                  result.status === "FAILED" ? "bg-danger-light text-danger" : "bg-success-light text-success"
                }`}
              >
                {result.status === "FAILED" ? "!" : "✓"}
              </motion.span>
              <div className="text-2xl font-bold text-ink">₹{result.amount.toLocaleString("en-IN")}</div>
              <div className="text-sm text-ink-secondary mt-1">{result.merchant_name || "Payment"}</div>
              <div className={`badge mt-3 ${result.status === "FAILED" ? "bg-danger-light text-danger" : "bg-success-light text-success"}`}>
                {result.status === "FAILED" ? "Payment Failed" : "Payment Successful"}
              </div>
              {result.debited && result.status === "FAILED" && (
                <p className="text-xs text-danger mt-2 font-medium">Amount debited from your account</p>
              )}

              <div className="mt-5 pt-4 border-t border-border text-left">
                <div className="text-ink-secondary text-xs mb-1">UPI Reference ID</div>
                <CopyReferenceId value={result.upi_ref_no} />
              </div>
            </div>

            {result.status === "FAILED" ? (
              <AnimatePresence mode="wait">
                {nishchintPhase === "detecting" && (
                  <motion.div
                    key="detecting"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-3 rounded-xl border border-brand-light bg-brand-light/40 px-5 py-4"
                  >
                    <motion.span
                      animate={{ rotate: [0, 20, -15, 0], scale: [1, 1.15, 1] }}
                      transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-dark text-white"
                    >
                      <SparkleIcon className="w-4 h-4" />
                    </motion.span>
                    <div className="text-sm text-brand-dark font-medium">
                      Nishchint noticed a problem with this payment
                      <span className="inline-flex gap-0.5 ml-1 align-middle">
                        {[0, 1, 2].map((i) => (
                          <motion.span
                            key={i}
                            className="h-1 w-1 rounded-full bg-brand-dark inline-block"
                            animate={{ opacity: [0.25, 1, 0.25] }}
                            transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                          />
                        ))}
                      </span>
                    </div>
                  </motion.div>
                )}

                {nishchintPhase === "checking" && (
                  <motion.div
                    key="checking"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="card p-5 border-2 border-brand-light"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <SparkleIcon className="w-4 h-4 text-brand-dark" />
                      <h2 className="text-sm font-semibold text-ink">Nishchint is investigating…</h2>
                    </div>
                    <div className="space-y-2">
                      {CHECK_STEPS.map((label, i) => (
                        <motion.div
                          key={label}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.45, duration: 0.3, ease: EASE }}
                          className="flex items-center gap-2 text-sm text-ink"
                        >
                          <motion.span
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: i * 0.45 + 0.15, type: "spring", stiffness: 400, damping: 15 }}
                            className="text-success"
                          >
                            ✓
                          </motion.span>
                          {label}
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}

                {nishchintPhase === "revealed" && (
                  <motion.div
                    key="revealed"
                    initial={{ opacity: 0, y: 16, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ type: "spring", stiffness: 260, damping: 20 }}
                    className="card p-5 border-2 border-brand-light relative overflow-hidden"
                  >
                    <motion.div
                      initial={{ opacity: 0.5 }}
                      animate={{ opacity: 0 }}
                      transition={{ duration: 0.8 }}
                      className="absolute inset-0 bg-brand-light"
                      aria-hidden
                    />
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-2">
                        <motion.span
                          initial={{ rotate: -20, scale: 0.5 }}
                          animate={{ rotate: 0, scale: 1 }}
                          transition={{ type: "spring", stiffness: 300, damping: 12 }}
                        >
                          <SparkleIcon className="w-4 h-4 text-brand-dark" />
                        </motion.span>
                        <h2 className="text-sm font-semibold text-ink">Nishchint</h2>
                      </div>
                      <p className="text-sm text-ink mb-1">I caught a problem with this payment.</p>
                      <p className="text-sm text-ink-secondary mb-4">
                        Payment failed, but the amount was debited. You don&apos;t need to raise a ticket manually —
                        I&apos;ve already checked the transaction.
                      </p>
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
                        <Link href={`/transactions/${result.id}`} className="btn-nishchint btn-md" onClick={() => setOpen(false)}>
                          <span>Investigate &amp; Resolve</span>
                          <span className="btn-nishchint-arrow">→</span>
                        </Link>
                      </motion.div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            ) : (
              <Link href="/nishchint" className="btn-outline btn-md w-full">
                Back to Home
              </Link>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
