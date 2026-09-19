"use client";

import { useEffect, useState } from "react";
import { getRefunds, investigateRefund } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import type { Refund } from "@/types";
import CaseTracker from "@/components/CaseTracker";

function RefundCard({ refund, onInvestigated, onRefresh }: { refund: Refund; onInvestigated: (refund: Refund) => void; onRefresh: () => void }) {
  const [investigating, setInvestigating] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [error, setError] = useState(false);

  async function handleInvestigate() {
    setInvestigating(true);
    setError(false);
    try {
      const result = await investigateRefund(refund.id);
      setCaseId(result.case_id);
      // Update this refund in place — a full-list reload would flip the
      // page back to its loading skeleton and unmount this card, wiping
      // the confirmation we just set.
      onInvestigated(result.refund);
    } catch {
      setError(true);
    } finally {
      setInvestigating(false);
    }
  }

  return (
    <div className="stagger-item card card-hover p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium text-ink">{refund.merchant_name}</div>
          <div className="text-xs text-ink-secondary mt-0.5">
            Merchant status: {refund.merchant_status === "COMPLETED" ? "Refund completed" : "Pending"}
          </div>
        </div>
        <div className="text-right">
          <div className="amount">₹{refund.amount.toLocaleString("en-IN")}</div>
          <span className={`badge mt-1 ${refund.customer_received ? "bg-success-light text-success" : "bg-danger-light text-danger"}`}>
            {refund.customer_received ? "Received" : "Not received"}
          </span>
        </div>
      </div>

      {(refund.nishchint_insight.has_issue || caseId) && (
        <div className="mt-4 rounded-lg bg-brand-light px-3 py-3">
          {refund.nishchint_insight.has_issue && <p className="text-xs text-brand-dark">{refund.nishchint_insight.message}</p>}
          {caseId ? (
            <CaseTracker
              caseId={caseId}
              resolved={!refund.nishchint_insight.has_issue}
              resolvedText={`Your ₹${refund.amount.toLocaleString("en-IN")} refund from ${refund.merchant_name} has reached your account.`}
              onChanged={onRefresh}
            />
          ) : (
            <button onClick={handleInvestigate} disabled={investigating} className="btn-primary btn-sm mt-2">
              {investigating ? "Investigating…" : "Investigate Refund"}
            </button>
          )}
          {error && <p className="text-xs text-danger mt-2">Couldn&apos;t start the investigation. Please try again.</p>}
        </div>
      )}
    </div>
  );
}

export default function RefundsPage() {
  const { customerId } = useCustomer();
  const { setPageContext } = useAssistant();
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    getRefunds(customerId).then(setRefunds).catch(console.error).finally(() => setLoading(false));
  }

  function refresh() {
    getRefunds(customerId).then(setRefunds).catch(console.error);
  }

  useEffect(load, [customerId]);

  useEffect(() => {
    const flagged = refunds.find((r) => r.nishchint_insight.has_issue);
    if (!flagged) {
      setPageContext(null);
      return;
    }
    setPageContext({
      summary: `your ₹${flagged.amount.toLocaleString("en-IN")} ${flagged.merchant_name} refund`,
      suggestedMessage: "The merchant marked my refund complete, but the amount hasn't reached my account.",
    });
    return () => setPageContext(null);
  }, [refunds, setPageContext]);

  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Refunds</h1>
        <p className="text-sm text-ink-secondary mt-1">Nishchint cross-checks merchant claims against what actually reached your account.</p>
      </div>

      {loading ? (
        <div className="h-32 rounded-xl skeleton" />
      ) : refunds.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-secondary">No refunds on file.</div>
      ) : (
        <div className="space-y-4 stagger-list">
          {refunds.map((r) => (
            <RefundCard
              key={r.id}
              refund={r}
              onRefresh={refresh}
              onInvestigated={(updated) => setRefunds((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
