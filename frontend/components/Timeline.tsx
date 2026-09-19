import { AnimatePresence, motion } from "framer-motion";
import type { TimelineEvent } from "@/types";

const EVENT_LABELS: Record<string, string> = {
  COMPLAINT_RECEIVED: "Complaint received",
  CONTEXT_RETRIEVED: "Customer context retrieved",
  TRANSACTION_VERIFIED: "Transaction verified",
  TRANSACTION_RECHECKED: "Transaction rechecked",
  RULE_EVALUATED: "Policy rule applied",
  DECISION_MADE: "Decision made",
  TICKET_CREATED: "Ticket created",
  CASE_STATUS_CHANGED: "Case status updated",
  FOLLOW_UP_SCHEDULED: "Follow-up scheduled",
  FOLLOW_UP_EXECUTED: "Follow-up executed",
  FOLLOW_UP_FAILED: "Follow-up failed",
  DISPUTE_RAISED: "Dispute raised",
  COMPENSATION_CALCULATED: "Compensation calculated",
  ESCALATION_CREATED: "Escalated to human",
  HUMAN_OVERRIDE: "Human override",
  NOTIFICATION_SENT: "Customer notified",
  SENSITIVE_CREDENTIAL_DETECTED: "Sensitive credential detected & blocked",
  SIM_CLOCK_ADVANCED: "Demo clock advanced",
  N8N_CALLBACK_RECEIVED: "n8n workflow callback received",
};

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return <div className="text-sm text-ink-secondary">No events yet.</div>;
  }

  return (
    <ol className="relative border-l-2 border-border ml-2">
      <AnimatePresence initial={false}>
        {events.map((e, i) => (
          <motion.li
            key={`${e.event_type}-${e.timestamp}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: Math.min(i * 0.03, 0.3) }}
            className="mb-5 ml-4"
          >
            <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-brand-dark ring-4 ring-white" />
            <time className="text-xs text-ink-secondary">
              {new Date(e.timestamp).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
            </time>
            <div className="text-sm font-medium text-ink">{EVENT_LABELS[e.event_type] || e.event_type}</div>
            <div className="text-xs text-ink-secondary">by {e.actor}</div>
          </motion.li>
        ))}
      </AnimatePresence>
    </ol>
  );
}
