"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getCase, getTransaction, listCases, sendChatMessage } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import { displayStatus } from "@/lib/transaction-status";
import type { CaseDetail, CaseListItem, Transaction } from "@/types";
import AutonomousLoopStrip from "@/components/AutonomousLoopStrip";
import { SparkleIcon } from "@/components/shell/icons";
import CopyReferenceId from "@/components/CopyReferenceId";

function CheckRow({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <motion.span
        key={String(done)}
        initial={done ? { scale: 0.5, opacity: 0 } : false}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 15 }}
        className={done ? "text-success" : "text-border"}
      >
        {done ? "✓" : "○"}
      </motion.span>
      <span className={done ? "text-ink" : "text-ink-secondary"}>{label}</span>
    </div>
  );
}

export default function TransactionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { customerId } = useCustomer();
  const { setPageContext } = useAssistant();

  const [txn, setTxn] = useState<Transaction | null>(null);
  const [existingCase, setExistingCase] = useState<CaseListItem | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [resolveActions, setResolveActions] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const transaction = await getTransaction(params.id);
      setTxn(transaction);
      const cases = await listCases({ customerId: transaction.customer_id });
      const match = cases.find((c) => c.transaction_id === transaction.id && c.status !== "RESOLVED") || null;
      setExistingCase(match);
      if (match) setCaseDetail(await getCase(match.id));
    } catch {
      setError("I'm unable to verify this transaction right now. I haven't taken any action.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!txn) return;
    setPageContext({
      summary: `this ₹${txn.amount.toLocaleString("en-IN")} ${txn.merchant_name ? txn.merchant_name + " " : ""}payment`,
      suggestedMessage: `I have an issue with my ₹${txn.amount} payment${txn.merchant_name ? " to " + txn.merchant_name : ""} (UPI Reference ID ${txn.upi_ref_no}).`,
    });
    return () => setPageContext(null);
  }, [txn, setPageContext]);

  async function investigateAndResolve() {
    if (!txn) return;
    setResolving(true);
    setResolveActions([]);
    try {
      const message = `I have an issue with my ₹${txn.amount} payment${txn.merchant_name ? " to " + txn.merchant_name : ""} (UPI Reference ID ${txn.upi_ref_no}). It shows as ${txn.status.toLowerCase()}.`;
      const resp = await sendChatMessage(customerId, message, null);
      setResolveActions(resp.actions);
      await load();
    } catch {
      setError("I couldn't reach the transaction service right now. I haven't taken any financial action.");
    } finally {
      setResolving(false);
    }
  }

  if (loading) {
    return (
      <div className="page-shell space-y-4">
        <div className="h-32 rounded-xl skeleton" />
        <div className="h-48 rounded-xl skeleton" />
      </div>
    );
  }

  if (error && !txn) {
    return <div className="page-shell text-sm text-danger">{error}</div>;
  }
  if (!txn) return null;

  const status = displayStatus(txn);
  const needsAttention = status === "Needs attention";

  return (
    <div className="page-shell space-y-5">
      <button onClick={() => router.back()} className="text-sm text-brand-dark hover:-translate-x-0.5 transition-transform duration-150 inline-flex items-center gap-1">
        ← Back
      </button>

      <div className="card p-6">
        <div className="text-xs text-ink-secondary mb-1">Payment details</div>
        <div className="text-3xl font-bold text-ink">₹{txn.amount.toLocaleString("en-IN")}</div>
        <div className="text-sm text-ink-secondary mt-1">{txn.merchant_name || "P2P transfer"}</div>
        <span className={`badge mt-3 ${needsAttention ? "bg-danger-light text-danger" : "bg-success-light text-success"}`}>{status}</span>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6 text-sm">
          <div>
            <div className="text-ink-secondary text-xs">UPI Reference ID</div>
            <div className="mt-1">
              <CopyReferenceId value={txn.upi_ref_no} />
            </div>
          </div>
          <div>
            <div className="text-ink-secondary text-xs">Date</div>
            <div className="mt-1">{new Date(txn.transaction_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</div>
          </div>
          <div>
            <div className="text-ink-secondary text-xs">Payment method</div>
            <div className="mt-1">UPI</div>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-ink mb-4">Transaction timeline</h2>
        <div className="space-y-2.5">
          <CheckRow label="Payment initiated" done />
          <CheckRow label="Bank authorization" done={txn.debited} />
          <CheckRow label="Merchant confirmation" done={txn.merchant_credited === true} />
          <div className="text-sm flex items-center gap-2">
            <span className="text-ink-secondary">→</span>
            <span className="text-ink-secondary">Payment status:</span>
            <span className="font-medium text-ink">{txn.status}</span>
          </div>
          {txn.refund_status !== "NOT_APPLICABLE" && (
            <div className="text-sm flex items-center gap-2">
              <span className="text-ink-secondary">→</span>
              <span className="text-ink-secondary">Amount reversal:</span>
              <span className="font-medium text-ink">{txn.refund_status}</span>
            </div>
          )}
        </div>
      </div>

      {error && <div className="card p-4 text-sm text-danger bg-danger-light border-danger/20">{error}</div>}

      <div className="card p-6">
        <div className="flex items-center gap-2 mb-3">
          <SparkleIcon className="w-4 h-4 text-brand-dark" />
          <h2 className="text-sm font-semibold text-ink">Nishchint</h2>
        </div>

        {caseDetail ? (
          <div className="space-y-4">
            <p className="text-sm text-ink">You&apos;re already being taken care of.</p>
            <AutonomousLoopStrip status={caseDetail.status} />
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-ink-secondary text-xs">Case</div>
                <div className="font-medium">{caseDetail.id}</div>
              </div>
              <div>
                <div className="text-ink-secondary text-xs">Status</div>
                <div className="font-medium">{caseDetail.status.replaceAll("_", " ")}</div>
              </div>
              {caseDetail.policy_result?.deadline && (
                <div>
                  <div className="text-ink-secondary text-xs">Expected refund</div>
                  <div className="font-medium">{caseDetail.policy_result.deadline}</div>
                </div>
              )}
              {caseDetail.followup && (
                <div>
                  <div className="text-ink-secondary text-xs">Next automated check</div>
                  <div className="font-medium">
                    {new Date(caseDetail.followup.scheduled_for).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </div>
                </div>
              )}
            </div>
            <Link href={`/cases/${caseDetail.id}`} className="inline-flex items-center text-sm font-medium text-brand-dark hover:underline transition-all">
              View full case →
            </Link>
          </div>
        ) : needsAttention ? (
          <div className="space-y-4">
            <p className="text-sm text-ink">
              I&apos;ve detected a payment exception: ₹{txn.amount.toLocaleString("en-IN")} was debited but the payment
              did not complete.
            </p>
            {resolveActions === null ? (
              <button onClick={investigateAndResolve} disabled={resolving} className="btn-primary btn-lg">
                {resolving ? "Investigating…" : "Investigate & Resolve"}
              </button>
            ) : (
              <div className="space-y-2 animate-fade-in-up">
                <CheckRow label="Identified transaction" done />
                <CheckRow label="Verified current status" done />
                <CheckRow label="Checked previous support history" done />
                <CheckRow label="Checked applicable resolution policy" done={resolveActions.length > 0} />
                <CheckRow label="Created resolution case" done={resolveActions.includes("TICKET_CREATED")} />
                {resolveActions.includes("FOLLOWUP_SCHEDULED") && (
                  <p className="text-sm text-ink pt-2">You don&apos;t need to keep checking — I&apos;ll monitor this automatically.</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-secondary">This payment looks fine — nothing for me to act on here.</p>
        )}
      </div>
    </div>
  );
}
