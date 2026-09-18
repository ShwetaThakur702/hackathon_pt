"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getCase, getCaseMemory } from "@/lib/api";
import type { CaseDetail, MemorySection } from "@/types";
import AutonomousLoopStrip from "@/components/AutonomousLoopStrip";
import StatusBadge from "@/components/StatusBadge";
import Timeline from "@/components/Timeline";
import SimulationControls from "@/components/SimulationControls";
import MemoryPanel from "@/components/MemoryPanel";

export default function CaseTimelinePage() {
  const params = useParams<{ caseId: string }>();
  const router = useRouter();
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
    // Fetched separately from the case itself — this can hit Cognee Cloud
    // and take a few seconds; it must never hold up the rest of the page.
    setMemoryLoading(true);
    getCaseMemory(params.caseId)
      .then(setMemory)
      .catch(() => setMemory(null))
      .finally(() => setMemoryLoading(false));
  }, [params.caseId]);

  if (error) {
    return <div className="page-shell max-w-4xl text-danger">{error}</div>;
  }
  if (!detail) {
    return <div className="page-shell max-w-4xl text-ink-secondary">Loading case…</div>;
  }

  const txn = detail.transaction;

  return (
    <div className="page-shell max-w-4xl space-y-6">
      <button onClick={() => router.back()} className="text-sm text-brand-dark">
        ← Back
      </button>

      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-bold text-ink">Case {detail.id}</h1>
          <StatusBadge status={detail.status} />
        </div>

        <AutonomousLoopStrip status={detail.status} />

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
              <div className="text-ink-secondary text-xs">UPI Ref No</div>
              <div className="font-mono text-xs mt-1">{txn.upi_ref_no}</div>
            </div>
            {detail.policy_result?.deadline && (
              <div>
                <div className="text-ink-secondary text-xs">Deadline</div>
                <div className="font-semibold text-ink">{detail.policy_result.deadline}</div>
              </div>
            )}
            {detail.dispute && (
              <div>
                <div className="text-ink-secondary text-xs">Compensation</div>
                <div className="font-semibold text-danger">₹{detail.dispute.compensation_amount.toLocaleString("en-IN")}</div>
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
          <SimulationControls onChanged={load} />
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
