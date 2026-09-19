const STATUS_STYLES: Record<string, string> = {
  NEW: "bg-surface text-ink-secondary",
  INVESTIGATING: "bg-brand-light text-brand-dark",
  DECIDED: "bg-brand-light text-brand-dark",
  ACTION_TAKEN: "bg-brand-light text-brand-dark",
  FOLLOW_UP_SCHEDULED: "bg-warning-light text-warning",
  WAITING_FOR_RESOLUTION: "bg-warning-light text-warning",
  RECHECKING: "bg-warning-light text-warning",
  RESOLVED: "bg-success-light text-success",
  DISPUTE_RAISED: "bg-danger-light text-danger",
  HUMAN_ESCALATED: "bg-danger text-white",
};

const LIVE_STATUSES = new Set(["INVESTIGATING", "DECIDED", "ACTION_TAKEN", "RECHECKING", "WAITING_FOR_RESOLUTION"]);

export default function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return null;
  const style = STATUS_STYLES[status] || "bg-surface text-ink-secondary";
  return (
    <span className={`badge gap-1.5 ${style}`}>
      {LIVE_STATUSES.has(status) && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
      {status.replaceAll("_", " ")}
    </span>
  );
}
