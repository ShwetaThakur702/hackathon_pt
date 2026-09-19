"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { advanceTime, advanceToDeadline, resetDemo } from "@/lib/api";

function Spinner() {
  return (
    <motion.span
      className="inline-block h-3.5 w-3.5 rounded-full border-2 border-white/40 border-t-white"
      animate={{ rotate: 360 }}
      transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
    />
  );
}

export default function SimulationControls({ onChanged }: { onChanged?: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string | null>(null);

  async function run(label: string, action: () => Promise<{ current_time: string }>) {
    setBusy(label);
    try {
      const result = await action();
      setCurrentTime(result.current_time);
      onChanged?.();
    } catch (err) {
      console.error(err);
      alert("Simulation action failed. Is the backend running?");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink">Demo Clock</h3>
        <AnimatePresence mode="wait">
          {currentTime && (
            <motion.span
              key={currentTime}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="text-xs text-ink-secondary tabular-nums"
            >
              {new Date(currentTime).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button disabled={!!busy} onClick={() => run("advance1", () => advanceTime(1))} className="btn-primary btn-sm">
          {busy === "advance1" ? <Spinner /> : "+1 Day"}
        </button>
        <button disabled={!!busy} onClick={() => run("deadline", () => advanceToDeadline())} className="btn-primary btn-sm">
          {busy === "deadline" ? <Spinner /> : "Advance to Deadline"}
        </button>
        <button disabled={!!busy} onClick={() => run("advance5", () => advanceTime(5))} className="btn-secondary btn-sm">
          {busy === "advance5" ? <Spinner /> : "Advance 5 Days"}
        </button>
        <button
          disabled={!!busy}
          onClick={() => run("reset", () => resetDemo())}
          className="btn btn-sm bg-white text-danger border border-danger/30 hover:bg-danger-light"
        >
          {busy === "reset" ? (
            <motion.span
              className="inline-block h-3.5 w-3.5 rounded-full border-2 border-danger/30 border-t-danger"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
            />
          ) : (
            "Reset Demo"
          )}
        </button>
      </div>
    </div>
  );
}
