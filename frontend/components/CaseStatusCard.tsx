import Link from "next/link";
import type { CaseDetail } from "@/types";
import StatusBadge from "./StatusBadge";

const STEP_ORDER = [
  "NEW",
  "INVESTIGATING",
  "DECIDED",
  "ACTION_TAKEN",
  "FOLLOW_UP_SCHEDULED",
  "WAITING_FOR_RESOLUTION",
  "RECHECKING",
];

function reached(status: string, current: string) {
  const currentIdx = STEP_ORDER.indexOf(current);
  const stepIdx = STEP_ORDER.indexOf(status);
  if (currentIdx === -1) return true; // terminal states (RESOLVED/DISPUTE_RAISED/HUMAN_ESCALATED) — show all done
  return stepIdx <= currentIdx;
}

export default function CaseStatusCard({ detail }: { detail: CaseDetail }) {
  const txn = detail.transaction;
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <Link href={`/cases/${detail.id}`} className="text-sm font-semibold text-brand hover:underline">
          CASE #{detail.id}
        </Link>
        <StatusBadge status={detail.status} />
      </div>

      {txn && (
        <div className="mt-2">
          <div className="text-2xl font-bold">₹{txn.amount.toLocaleString("en-IN")}</div>
          <div className="text-sm text-slate-500">
            Failed {txn.type === "MERCHANT" ? "Merchant" : "P2P"} Payment
            {txn.merchant_name ? ` · ${txn.merchant_name}` : ""}
          </div>
        </div>
      )}

      <ul className="mt-4 space-y-1.5 text-sm">
        <li className={reached("INVESTIGATING", detail.status) ? "text-slate-700" : "text-slate-300"}>
          {reached("INVESTIGATING", detail.status) ? "✓" : "○"} Transaction checked
        </li>
        <li className={reached("DECIDED", detail.status) ? "text-slate-700" : "text-slate-300"}>
          {reached("DECIDED", detail.status) ? "✓" : "○"} Policy evaluated
        </li>
        <li className={reached("ACTION_TAKEN", detail.status) ? "text-slate-700" : "text-slate-300"}>
          {reached("ACTION_TAKEN", detail.status) ? "✓" : "○"} Ticket created
        </li>
        <li className={detail.followup ? "text-slate-700" : "text-slate-300"}>
          {detail.followup ? "✓" : "○"} Follow-up scheduled
        </li>
      </ul>

      {detail.policy_result?.deadline && (
        <div className="mt-4 rounded-lg bg-brand-light px-3 py-2">
          <div className="text-xs text-slate-500">Expected refund</div>
          <div className="text-sm font-semibold text-brand-dark">{detail.policy_result.deadline}</div>
        </div>
      )}

      {detail.dispute && (
        <div className="mt-3 rounded-lg bg-rose-50 px-3 py-2">
          <div className="text-xs text-rose-500">Dispute raised</div>
          <div className="text-sm font-semibold text-rose-700">
            Compensation ₹{detail.dispute.compensation_amount.toLocaleString("en-IN")}
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-slate-400">
        Status: {detail.status === "WAITING_FOR_RESOLUTION" ? "Waiting for refund" : detail.status.replaceAll("_", " ")}
      </div>
    </div>
  );
}
