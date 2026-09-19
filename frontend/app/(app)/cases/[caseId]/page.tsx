"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getCase, getCaseMemory } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import type { CaseDetail, MemorySection } from "@/types";
import AnimatedNumber from "@/components/AnimatedNumber";
import AutonomousLoopStrip from "@/components/AutonomousLoopStrip";
import CopyReferenceId from "@/components/CopyReferenceId";
import StatusBadge from "@/components/StatusBadge";
import Timeline from "@/components/Timeline";
import SimulationControls from "@/components/SimulationControls";
import MemoryPanel from "@/components/MemoryPanel";

export default function CaseTimelinePage() {
  const params = useParams<{ caseId: string }>();
  const router = useRouter();
  const { setPageContext } = useAssistant();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [memory, setMemory] = useState<MemorySection | null>(null);
  const [memoryLoading, setMemoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getCase(params.caseId);
      setDetail(data);
      setError(null);
    } catch (err) {
      setError("Could not load this case. Is the backend running?");
    }
  }, [params.caseId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!detail || detail.status === "RESOLVED") {
      setPageContext(null);
      return;
    }
    setPageContext({
      summary: `case ${detail.id}, which I'm still monitoring`,
      suggestedMessage: "Abhi tak paise nahi aaye — what's the current status of this case?",
    });
    return () => setPageContext(null);
  }, [detail, setPageContext]);

  useEffect(() => {
    // Fetched separately from the case itself — this can hit Cognee Cloud
    // and take a few seconds; it must never hold up the rest of the page.
    setMemoryLoading(true);
    getCaseMemory(params.caseId)
      .then(setMemory)
      .catch(() => setMemory(null))
      .finally(() => setMemoryLoading(false));
  }, [params.caseId]);

  if (error) {
    return (
      <div className="page-shell max-w-4xl">
        <div className="card p-6 text-danger text-sm">{error}</div>
      </div>
    );
  }
  if (!detail) {
    return (
      <div className="page-shell max-w-4xl space-y-6">
        <div className="h-8 w-40 rounded skeleton" />
        <div className="h-56 rounded-xl skeleton" />
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
          <div className="h-72 rounded-xl skeleton" />
          <div className="h-72 rounded-xl skeleton" />
        </div>
      </div>
    );
  }

  const txn = detail.transaction;
  const hasCompensation = detail.current_compensation !== null && detail.current_compensation > 0;

  return (
    <div className="page-shell max-w-4xl space-y-6">
      <button
        onClick={() => router.back()}
        className="text-sm text-brand-dark hover:-translate-x-0.5 transition-transform duration-150 inline-flex items-center gap-1"
      >
        ← Back
      </button>

      <div className="card p-6 animate-fade-in-up">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-bold text-ink">Case {detail.id}</h1>
          <StatusBadge status={detail.status} />
        </div>

        <AutonomousLoopStrip status={detail.status} />

        {hasCompensation && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-6 rounded-xl bg-gradient-to-br from-danger-light to-white border border-danger/15 px-5 py-4 flex items-center justify-between"
          >
            <div>
              <div className="text-xs text-danger font-medium">Current applicable compensation</div>
              <AnimatedNumber
                value={detail.current_compensation!}
                prefix="₹"
                className="text-3xl font-bold text-danger tabular-nums"
              />
            </div>
            {detail.days_overdue !== null && detail.days_overdue > 0 && (
              <div className="text-right">
                <div className="text-xs text-ink-secondary">Days overdue</div>
                <div className="text-xl font-semibold text-ink">{detail.days_overdue}</div>
              </div>
            )}
          </motion.div>
        )}

        {txn && (
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm border-t border-border pt-4">
            <div>
              <div className="text-ink-secondary text-xs">Amount</div>
              <div className="amount">₹{txn.amount.toLocaleString("en-IN")}</div>
            </div>
            <div>
              <div className="text-ink-secondary text-xs">Type</div>
              <div className="font-semibold text-ink">{txn.type === "MERCHANT" ? "Failed Merchant Payment" : "Failed P2P Payment"}</div>
            </div>
            <div>
              <div className="text-ink-secondary text-xs">Customer</div>
              <div className="font-semibold text-ink">{detail.customer?.name}</div>
            </div>
            <div>
              <div className="text-ink-secondary text-xs">Merchant</div>
              <div className="font-semibold text-ink">{txn.merchant_name || "—"}</div>
            </div>
            <div>
              <div className="text-ink-secondary text-xs">UPI Reference ID</div>
              <div className="mt-1">
                <CopyReferenceId value={txn.upi_ref_no} />
              </div>
            </div>
            {detail.policy_result?.deadline && (
              <div>
                <div className="text-ink-secondary text-xs">Resolution deadline</div>
                <div className="font-semibold text-ink">{detail.policy_result.deadline}</div>
              </div>
            )}
            {detail.policy_result?.applicable && (
              <div>
                <div className="text-ink-secondary text-xs">Current demo date</div>
                <div className="font-semibold text-ink">{detail.current_demo_time.slice(0, 10)}</div>
              </div>
            )}
            {detail.escalation_reason && (
              <div>
                <div className="text-ink-secondary text-xs">Escalation reason</div>
                <div className="font-semibold text-brand-dark">{detail.escalation_reason.replaceAll("_", " ")}</div>
              </div>
            )}
          </div>
        )}
        {!txn && detail.intent && (
          <div className="mt-6 text-sm border-t border-border pt-4">
            <div className="text-ink-secondary text-xs">Issue type</div>
            <div className="font-semibold text-ink">{detail.intent.replaceAll("_", " ")}</div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-ink mb-4">Timeline</h2>
          <Timeline events={detail.timeline} />
        </div>
        <div className="space-y-4">
          <SimulationControls onChanged={load} caseId={detail.id} />
          <div className="card p-4">
            <h3 className="text-sm font-semibold text-ink mb-2">Conversation</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {detail.messages.map((m, i) => (
                <div key={i} className="text-xs">
                  <span className="font-semibold">{m.sender}:</span> {m.message}
                </div>
              ))}
              {detail.messages.length === 0 && <div className="text-xs text-ink-secondary">No messages recorded.</div>}
            </div>
          </div>
          <MemoryPanel memory={memory} loading={memoryLoading} />
        </div>
      </div>
    </div>
  );
}
