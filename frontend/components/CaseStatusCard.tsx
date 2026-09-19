import Link from "next/link";
import { motion } from "framer-motion";
import type { CaseDetail } from "@/types";
import AnimatedNumber from "./AnimatedNumber";
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

function StepRow({ label, done }: { label: string; done: boolean }) {
  return (
    <li className={`flex items-center gap-2 ${done ? "text-ink" : "text-ink-secondary/60"}`}>
      <motion.span
        initial={false}
        animate={done ? { scale: [0.6, 1.15, 1] } : { scale: 1 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className={done ? "text-success" : ""}
      >
        {done ? "✓" : "○"}
      </motion.span>
      {label}
    </li>
  );
}

export default function CaseStatusCard({ detail }: { detail: CaseDetail }) {
  const txn = detail.transaction;
  return (
    <div className="card p-5 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <Link href={`/cases/${detail.id}`} className="text-sm font-semibold text-brand-dark hover:underline transition-all">
          CASE #{detail.id}
        </Link>
        <StatusBadge status={detail.status} />
      </div>

      {txn && (
        <div className="mt-2">
          <div className="text-2xl font-bold text-ink">₹{txn.amount.toLocaleString("en-IN")}</div>
          <div className="text-sm text-ink-secondary">
            Failed {txn.type === "MERCHANT" ? "Merchant" : "P2P"} Payment
            {txn.merchant_name ? ` · ${txn.merchant_name}` : ""}
          </div>
        </div>
      )}

      <ul className="mt-4 space-y-1.5 text-sm">
        <StepRow label="Transaction checked" done={reached("INVESTIGATING", detail.status)} />
        <StepRow label="Policy evaluated" done={reached("DECIDED", detail.status)} />
        <StepRow label="Ticket created" done={reached("ACTION_TAKEN", detail.status)} />
        <StepRow label="Follow-up scheduled" done={!!detail.followup} />
      </ul>

      {detail.policy_result?.deadline && (
        <div className="mt-4 rounded-lg bg-brand-light px-3 py-2">
          <div className="text-xs text-ink-secondary">Expected refund</div>
          <div className="text-sm font-semibold text-brand-dark">{detail.policy_result.deadline}</div>
        </div>
      )}

      {detail.dispute && detail.current_compensation !== null && detail.current_compensation > 0 && (
        <div className="mt-3 rounded-lg bg-danger-light px-3 py-2 animate-pop-in">
          <div className="text-xs text-danger">Dispute raised</div>
          <div className="text-sm font-semibold text-danger flex items-baseline gap-1">
            Compensation <AnimatedNumber value={detail.current_compensation} prefix="₹" />
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-ink-secondary">
        Status: {detail.status === "WAITING_FOR_RESOLUTION" ? "Waiting for refund" : detail.status.replaceAll("_", " ")}
      </div>
    </div>
  );
}
