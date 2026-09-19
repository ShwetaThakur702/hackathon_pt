"use client";

import { useEffect, useState } from "react";
import { cancelMandate, getAutoPayMandates, reviewMandate } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import type { AutoPayMandate } from "@/types";

function MandateCard({ mandate, onChanged }: { mandate: AutoPayMandate; onChanged: (mandate: AutoPayMandate) => void }) {
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  async function handleReview() {
    setBusy(true);
    setError(false);
    try {
      await reviewMandate(mandate.id);
      setReviewed(true);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    setError(false);
    try {
      const cancelled = await cancelMandate(mandate.id);
      // Update this mandate in place — a full-list reload would flip the
      // page back to its loading skeleton and unmount this card, wiping
      // the "reviewed" state we just showed.
      onChanged(cancelled);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stagger-item card card-hover p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium text-ink">{mandate.biller_name}</div>
          <div className="text-xs text-ink-secondary mt-0.5">
            {mandate.frequency.charAt(0) + mandate.frequency.slice(1).toLowerCase()} · Next charge{" "}
            {new Date(mandate.next_charge_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
          </div>
        </div>
        <div className="text-right">
          <div className="amount">₹{mandate.amount.toLocaleString("en-IN")}</div>
          <span className={`badge mt-1 ${mandate.status === "ACTIVE" ? "bg-success-light text-success" : "bg-surface text-ink-secondary"}`}>
            {mandate.status === "ACTIVE" ? "Active" : "Cancelled"}
          </span>
        </div>
      </div>

      {mandate.nishchint_insight.has_issue && (
        <div className="mt-4 rounded-lg bg-warning-light px-3 py-3 space-y-2">
          <p className="text-xs text-ink">{mandate.nishchint_insight.message}</p>
          {reviewed && (
            <div className="text-xs text-ink space-y-1 animate-fade-in-up">
              <div>✓ Payment verified</div>
              <div>✓ AutoPay mandate found</div>
              <div>✓ Duplicate risk detected</div>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            {!reviewed && (
              <button onClick={handleReview} disabled={busy} className="btn-secondary btn-sm">
                Review AutoPay
              </button>
            )}
            {reviewed && (
              <button onClick={handleCancel} disabled={busy} className="btn-danger btn-sm">
                {busy ? "Cancelling…" : "Cancel Upcoming AutoPay"}
              </button>
            )}
          </div>
          {error && <p className="text-xs text-danger">Something went wrong. Please try again.</p>}
        </div>
      )}
    </div>
  );
}

export default function AutoPayPage() {
  const { customerId } = useCustomer();
  const { setPageContext } = useAssistant();
  const [mandates, setMandates] = useState<AutoPayMandate[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    getAutoPayMandates(customerId).then(setMandates).catch(console.error).finally(() => setLoading(false));
  }

  useEffect(load, [customerId]);

  useEffect(() => {
    if (!mandates.some((m) => m.nishchint_insight.has_issue)) {
      setPageContext(null);
      return;
    }
    setPageContext({
      summary: "your AutoPay mandate that looks like a duplicate-payment risk",
      suggestedMessage: "You've already made this payment, but AutoPay is still scheduled — can you check on this?",
    });
    return () => setPageContext(null);
  }, [mandates, setPageContext]);

  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">AutoPay</h1>
        <p className="text-sm text-ink-secondary mt-1">Active mandates, checked against your recent manual payments.</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <div key={i} className="h-28 rounded-xl skeleton" />
          ))}
        </div>
      ) : mandates.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-secondary">No AutoPay mandates set up.</div>
      ) : (
        <div className="space-y-4 stagger-list">
          {mandates.map((m) => (
            <MandateCard
              key={m.id}
              mandate={m}
              onChanged={(updated) => setMandates((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
