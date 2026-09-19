"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getCase, listCases, overrideCase } from "@/lib/api";
import type { CaseDetail, CaseListItem } from "@/types";
import AutonomousLoopStrip from "@/components/AutonomousLoopStrip";
import CaseList, { CaseListLink } from "@/components/CaseList";
import StatusBadge from "@/components/StatusBadge";
import Timeline from "@/components/Timeline";
import SimulationControls from "@/components/SimulationControls";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4 text-center">
      <div className="text-2xl font-bold text-brand-dark">{value}</div>
      <div className="text-xs text-ink-secondary">{label}</div>
    </div>
  );
}

function averageResolutionHours(cases: CaseListItem[]): string {
  const resolved = cases.filter((c) => c.closed_at);
  if (resolved.length === 0) return "—";
  const totalHours = resolved.reduce((sum, c) => {
    const ms = new Date(c.closed_at as string).getTime() - new Date(c.created_at).getTime();
    return sum + ms / 3_600_000;
  }, 0);
  const avg = totalHours / resolved.length;
  return avg < 24 ? `${avg.toFixed(1)}h` : `${(avg / 24).toFixed(1)}d`;
}

function decisionExplanation(detail: CaseDetail): { decision: string; why: string[]; actionsTaken: string[] } {
  const why: string[] = [];
  let decision = "MONITOR";

  if (detail.status === "HUMAN_ESCALATED") {
    decision = "ESCALATE";
    if (detail.escalation_reason === "HIGH_VALUE_TRANSACTION") why.push("Transaction amount exceeds the configured high-value threshold.");
    else if (detail.escalation_reason) why.push(`Flagged: ${detail.escalation_reason.replaceAll("_", " ").toLowerCase()}.`);
    why.push("Current transaction state verified against the mock Paytm service.");
  } else if (detail.status === "DISPUTE_RAISED") {
    decision = "RAISE DISPUTE";
    why.push("Refund remained unresolved beyond the applicable policy deadline.");
    if (detail.policy_result?.compensation) why.push(`Compensation of ₹${detail.policy_result.compensation} calculated per configured policy.`);
  } else if (detail.status === "RESOLVED") {
    decision = "RESOLVE";
    why.push("Verified current status matches a resolved outcome.");
  } else {
    why.push("Case is within its policy window — automatic follow-up is scheduled.");
  }

  const actionsTaken = Array.from(new Set(detail.timeline.map((e) => e.event_type))).filter((t) =>
    ["TICKET_CREATED", "FOLLOW_UP_SCHEDULED", "DISPUTE_RAISED", "ESCALATION_CREATED", "NOTIFICATION_SENT", "HUMAN_OVERRIDE"].includes(t)
  );

  return { decision, why, actionsTaken };
}

export default function OperationsPage() {
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [overriding, setOverriding] = useState(false);
  const [note, setNote] = useState("");

  const refreshList = useCallback(async () => {
    const rows = await listCases();
    setCases(rows);
    if (!selectedId && rows.length > 0) {
      setSelectedId(rows[0].id);
    }
  }, [selectedId]);

  const refreshDetail = useCallback(async (id: string) => {
    const data = await getCase(id);
    setDetail(data);
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    if (selectedId) refreshDetail(selectedId);
  }, [selectedId, refreshDetail]);

  async function handleAction(action: "APPROVE" | "OVERRIDE", newStatus?: string) {
    if (!selectedId) return;
    setOverriding(true);
    try {
      await overrideCase(selectedId, action, newStatus, note || undefined);
      setNote("");
      await refreshDetail(selectedId);
      await refreshList();
    } catch (err) {
      console.error(err);
      alert("Override failed.");
    } finally {
      setOverriding(false);
    }
  }

  const metrics = {
    active: cases.filter((c) => !["RESOLVED"].includes(c.status)).length,
    followups: cases.filter((c) => ["FOLLOW_UP_SCHEDULED", "WAITING_FOR_RESOLUTION", "RECHECKING"].includes(c.status)).length,
    escalations: cases.filter((c) => c.status === "HUMAN_ESCALATED").length,
    resolved: cases.filter((c) => c.status === "RESOLVED").length,
  };
  const avgResolution = useMemo(() => averageResolutionHours(cases), [cases]);

  const highPriority = cases.filter((c) => c.priority === "HIGH");
  const explanation = detail ? decisionExplanation(detail) : null;

  return (
    <div className="page-shell max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-ink">Operations</h1>
          <p className="text-sm text-ink-secondary">Human oversight for Nishchint&apos;s autonomous cases.</p>
        </div>
        <Link href="/nishchint" className="text-sm text-brand-dark hover:underline">
          ← Customer view
        </Link>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        <Metric label="Active Cases" value={metrics.active} />
        <Metric label="Follow-ups" value={metrics.followups} />
        <Metric label="Escalations" value={metrics.escalations} />
        <Metric label="Resolved" value={metrics.resolved} />
        <Metric label="Avg. Resolution" value={avgResolution} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <div className="card overflow-hidden">
          {highPriority.length > 0 && (
            <div className="bg-brand-light px-4 py-2 text-xs font-semibold text-brand-dark uppercase tracking-wide">
              High Priority
            </div>
          )}
          <CaseList cases={cases} selectedId={selectedId} onSelect={setSelectedId} />
        </div>

        <div className="space-y-4">
          <SimulationControls onChanged={() => { refreshList(); if (selectedId) refreshDetail(selectedId); }} />

          {detail ? (
            <div className="card p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-ink">{detail.id}</h2>
                  <div className="text-sm text-ink-secondary">{detail.customer?.name}</div>
                </div>
                <StatusBadge status={detail.status} />
              </div>

              <AutonomousLoopStrip status={detail.status} />

              {detail.escalation_reason && (
                <div className="rounded-lg bg-brand-light px-3 py-2 text-sm text-brand-dark">
                  <div className="font-semibold">AI Recommendation: Human review required</div>
                  <div className="text-xs">Reason: {detail.escalation_reason.replaceAll("_", " ")}</div>
                </div>
              )}

              {detail.transaction && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-ink-secondary text-xs">UPI Ref No</div>
                    <div className="font-mono text-xs">{detail.transaction.upi_ref_no}</div>
                  </div>
                  <div>
                    <div className="text-ink-secondary text-xs">Amount</div>
                    <div className="amount">₹{detail.transaction.amount.toLocaleString("en-IN")}</div>
                  </div>
                  <div>
                    <div className="text-ink-secondary text-xs">Merchant</div>
                    <div className="text-ink">{detail.transaction.merchant_name || "P2P"}</div>
                  </div>
                  <div>
                    <div className="text-ink-secondary text-xs">Refund status</div>
                    <div className="text-ink">{detail.transaction.refund_status}</div>
                  </div>
                </div>
              )}

              {explanation && (
                <div className="rounded-lg border border-border p-4">
                  <div className="text-xs font-semibold text-ink-secondary mb-2">AI decision</div>
                  <div className="text-sm font-bold text-ink mb-2">{explanation.decision}</div>
                  <ul className="text-xs text-ink-secondary space-y-1 mb-2 list-disc pl-4">
                    {explanation.why.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                  <div className="text-[11px] text-ink-secondary">
                    Sources: Transaction service · Policy engine · Customer memory
                  </div>
                  {explanation.actionsTaken.length > 0 && (
                    <div className="text-[11px] text-ink-secondary mt-1">
                      Actions taken: {explanation.actionsTaken.map((a) => a.replaceAll("_", " ").toLowerCase()).join(", ")}
                    </div>
                  )}
                </div>
              )}

              <div>
                <div className="text-xs font-semibold text-ink-secondary mb-2">Human actions</div>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Optional note to customer"
                  className="w-full rounded-lg border border-border px-3 py-1.5 text-sm mb-2"
                />
                <div className="flex gap-2">
                  <button
                    disabled={overriding}
                    onClick={() => handleAction("APPROVE")}
                    className="rounded-lg bg-success text-white text-sm px-4 py-1.5 hover:opacity-90 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    disabled={overriding}
                    onClick={() => {
                      const target = prompt("Override to which status? (e.g. RESOLVED, DISPUTE_RAISED)");
                      if (target) handleAction("OVERRIDE", target);
                    }}
                    className="rounded-lg border border-border text-ink text-sm px-4 py-1.5 hover:bg-surface disabled:opacity-50"
                  >
                    Override
                  </button>
                  <CaseListLink caseId={detail.id} />
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-ink-secondary mb-2">Audit trail</div>
                <div className="max-h-64 overflow-y-auto">
                  <Timeline events={detail.timeline} />
                </div>
              </div>
            </div>
          ) : (
            <div className="card p-6 text-sm text-ink-secondary">Select a case to review.</div>
          )}
        </div>
      </div>
    </div>
  );
}
