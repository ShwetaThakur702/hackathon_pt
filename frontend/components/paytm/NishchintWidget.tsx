"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { getAttention } from "@/lib/api";
import { CUSTOMER_ID } from "@/lib/customer-context";
import type { AttentionItem, Transaction } from "@/types";
import CopyReferenceId from "@/components/CopyReferenceId";
import { CloseIcon, SparkleIcon } from "@/components/shell/icons";
import Wordmark from "@/components/shell/Wordmark";
import WaveExitOverlay from "@/components/transition/WaveExitOverlay";
import { useWaveNavigate } from "@/components/transition/useWaveNavigate";

type Mode = "idle" | "attention-peek" | "detecting" | "checking" | "revealed" | "dismissed";

const EASE = [0.16, 1, 0.3, 1] as const;
const CHECK_STEPS = ["Transaction identified", "Current status verified", "Resolution policy checked"];

/**
 * Nishchint as a global widget — the same role a real embedded support
 * widget plays inside a host app: mostly a quiet corner icon, but it
 * surfaces itself unprompted the moment something needs attention
 * (spec: "pops up on its own on the trigger of any issue that has
 * occurred, not just payment"). Clicking it with nothing active opens the
 * full Nishchint app (/nishchint) — everything built so far lives there;
 * this widget is deliberately thin, not a second app.
 */
export default function NishchintWidget({ failedPayment }: { failedPayment: Transaction | null }) {
  const { active: waveActive, navigate: waveNavigate, handleCovered } = useWaveNavigate();
  const [mode, setMode] = useState<Mode>("idle");
  const [attentionItems, setAttentionItems] = useState<AttentionItem[]>([]);

  // Ambient signal: ANY exception Nishchint already tracks (failed
  // payment, bill/provider mismatch, FASTag balance, AutoPay duplicate
  // risk, refund mismatch) — not only a payment the customer just made.
  useEffect(() => {
    let cancelled = false;
    getAttention(CUSTOMER_ID)
      .then((res) => {
        if (cancelled || res.items.length === 0) return;
        setAttentionItems(res.items);
        const t = setTimeout(() => setMode((m) => (m === "idle" ? "attention-peek" : m)), 1400);
        return () => clearTimeout(t);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // A payment just failed live on this page — this takes priority over
  // the ambient attention peek and plays the full detect -> investigate
  // -> respond sequence right where the customer is, no navigation away.
  useEffect(() => {
    if (!failedPayment) return;
    setMode("detecting");
    const t1 = setTimeout(() => setMode("checking"), 900);
    const t2 = setTimeout(() => setMode("revealed"), 900 + CHECK_STEPS.length * 450 + 300);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [failedPayment]);

  function openFullApp(path = "/nishchint") {
    waveNavigate(path, "Welcome to Nishchint", "Your autonomous payment & service resolution assistant.");
  }

  const isBusy = mode === "detecting" || mode === "checking" || mode === "revealed";

  return (
    <div className="fixed z-40 right-4 bottom-4 sm:right-6 sm:bottom-6 w-[calc(100%-2rem)] sm:w-auto flex flex-col items-end gap-3">
      <WaveExitOverlay active={waveActive} onCovered={handleCovered} />
      <AnimatePresence mode="wait">
        {mode === "attention-peek" && (
          <motion.div
            key="peek"
            initial={{ opacity: 0, y: 16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 300, damping: 22 }}
            className="w-full sm:w-80 card p-4 border-2 border-brand-light relative"
          >
            <button
              onClick={() => setMode("dismissed")}
              className="absolute top-3 right-3 text-ink-secondary hover:text-ink transition-colors"
              aria-label="Dismiss"
            >
              <CloseIcon className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2 mb-1.5 pr-5">
              <motion.span
                animate={{ rotate: [0, 15, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 1.5 }}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-dark text-white"
              >
                <SparkleIcon className="w-3.5 h-3.5" />
              </motion.span>
              <h3 className="text-sm font-semibold"><Wordmark /></h3>
            </div>
            <p className="text-sm text-ink">
              I&apos;m watching {attentionItems.length} thing{attentionItems.length > 1 ? "s" : ""} that may need your
              attention.
            </p>
            {attentionItems[0] && <p className="text-xs text-ink-secondary mt-1 truncate">{attentionItems[0].title}</p>}
            <button
              onClick={() => openFullApp(attentionItems.length === 1 ? attentionItems[0].cta_href : "/nishchint")}
              className="btn-nishchint btn-sm w-full mt-3"
            >
              <span>{attentionItems.length === 1 ? attentionItems[0].cta_label : "Review with Nishchint"}</span>
              <span className="btn-nishchint-arrow">→</span>
            </button>
          </motion.div>
        )}

        {mode === "detecting" && (
          <motion.div
            key="detecting"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="w-full sm:w-80 flex items-center gap-3 rounded-xl border border-brand-light bg-brand-light/60 px-4 py-3 shadow-lg"
          >
            <motion.span
              animate={{ rotate: [0, 20, -15, 0], scale: [1, 1.15, 1] }}
              transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-dark text-white"
            >
              <SparkleIcon className="w-4 h-4" />
            </motion.span>
            <div className="text-sm text-brand-dark font-medium">
              Nishchint noticed a problem
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

        {mode === "checking" && (
          <motion.div
            key="checking"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="w-full sm:w-80 card p-4 border-2 border-brand-light shadow-lg"
          >
            <div className="flex items-center gap-2 mb-3">
              <SparkleIcon className="w-4 h-4 text-brand-dark" />
              <h3 className="text-sm font-semibold text-ink">Nishchint is investigating…</h3>
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

        {mode === "revealed" && failedPayment && (
          <motion.div
            key="revealed"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="w-full sm:w-80 card p-4 border-2 border-brand-light shadow-lg relative overflow-hidden"
          >
            <motion.div
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 0 }}
              transition={{ duration: 0.8 }}
              className="absolute inset-0 bg-brand-light"
              aria-hidden
            />
            <div className="relative">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <motion.span
                    initial={{ rotate: -20, scale: 0.5 }}
                    animate={{ rotate: 0, scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 12 }}
                  >
                    <SparkleIcon className="w-4 h-4 text-brand-dark" />
                  </motion.span>
                  <h3 className="text-sm font-semibold"><Wordmark /></h3>
                </div>
                <button onClick={() => setMode("dismissed")} className="text-ink-secondary hover:text-ink transition-colors" aria-label="Dismiss">
                  <CloseIcon className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-ink mb-1">I caught a problem with this payment.</p>
              <p className="text-xs text-ink-secondary mb-2">
                ₹{failedPayment.amount.toLocaleString("en-IN")} to {failedPayment.merchant_name} — failed, amount
                debited. You don&apos;t need to raise a ticket manually.
              </p>
              <div className="mb-3 text-xs">
                <CopyReferenceId value={failedPayment.upi_ref_no} />
              </div>
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                onClick={() => openFullApp(`/transactions/${failedPayment.id}`)}
                className="btn-nishchint btn-sm w-full"
              >
                <span>Investigate &amp; Resolve</span>
                <span className="btn-nishchint-arrow">→</span>
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        onClick={() => {
          // The pill itself is always clickable — it takes you to whatever
          // Nishchint is currently most relevant about, not just when idle.
          if (mode === "revealed" && failedPayment) {
            openFullApp(`/transactions/${failedPayment.id}`);
          } else if (mode === "attention-peek" && attentionItems.length === 1) {
            openFullApp(attentionItems[0].cta_href);
          } else {
            openFullApp();
          }
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="tap-target self-end flex items-center gap-2 rounded-full bg-brand-dark text-white pl-4 pr-5 py-3 shadow-lg hover:bg-brand-navy transition-colors"
        aria-label="Open Nishchint"
      >
        <motion.span
          animate={isBusy ? { rotate: 360 } : { rotate: [0, 15, -10, 0] }}
          transition={isBusy ? { duration: 1.2, repeat: Infinity, ease: "linear" } : { duration: 2.5, repeat: Infinity, repeatDelay: 2 }}
        >
          <SparkleIcon className="w-5 h-5" />
        </motion.span>
        <span className="text-sm font-medium hidden sm:inline">Nishchint</span>
        {(mode === "attention-peek" || mode === "revealed") && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="h-2 w-2 rounded-full bg-danger"
          />
        )}
      </motion.button>
    </div>
  );
}
