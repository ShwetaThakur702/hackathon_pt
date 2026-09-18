"use client";

import { useState } from "react";
import { advanceTime, advanceToDeadline, resetDemo } from "@/lib/api";

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
        <h3 className="text-sm font-semibold text-slate-700">Demo Clock</h3>
        {currentTime && (
          <span className="text-xs text-slate-500">
            {new Date(currentTime).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          disabled={!!busy}
          onClick={() => run("advance1", () => advanceTime(1))}
          className="rounded-lg bg-brand text-white text-sm py-2 px-3 hover:bg-brand-dark disabled:opacity-50"
        >
          {busy === "advance1" ? "Advancing…" : "+1 Day"}
        </button>
        <button
          disabled={!!busy}
          onClick={() => run("deadline", () => advanceToDeadline())}
          className="rounded-lg bg-brand text-white text-sm py-2 px-3 hover:bg-brand-dark disabled:opacity-50"
        >
          {busy === "deadline" ? "Advancing…" : "Advance to Deadline"}
        </button>
        <button
          disabled={!!busy}
          onClick={() => run("advance5", () => advanceTime(5))}
          className="rounded-lg border border-brand text-brand text-sm py-2 px-3 hover:bg-brand-light disabled:opacity-50"
        >
          {busy === "advance5" ? "Advancing…" : "Advance 5 Days"}
        </button>
        <button
          disabled={!!busy}
          onClick={() => run("reset", () => resetDemo())}
          className="rounded-lg border border-rose-300 text-rose-600 text-sm py-2 px-3 hover:bg-rose-50 disabled:opacity-50"
        >
          {busy === "reset" ? "Resetting…" : "Reset Demo"}
        </button>
      </div>
    </div>
  );
}
