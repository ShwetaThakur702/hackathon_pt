const STATUS_STYLES: Record<string, string> = {
  NEW: "bg-slate-100 text-slate-700",
  INVESTIGATING: "bg-blue-100 text-blue-700",
  DECIDED: "bg-blue-100 text-blue-700",
  ACTION_TAKEN: "bg-blue-100 text-blue-700",
  FOLLOW_UP_SCHEDULED: "bg-amber-100 text-amber-700",
  WAITING_FOR_RESOLUTION: "bg-amber-100 text-amber-700",
  RECHECKING: "bg-amber-100 text-amber-700",
  RESOLVED: "bg-emerald-100 text-emerald-700",
  DISPUTE_RAISED: "bg-rose-100 text-rose-700",
  HUMAN_ESCALATED: "bg-violet-100 text-violet-700",
};

export default function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return null;
  const style = STATUS_STYLES[status] || "bg-slate-100 text-slate-700";
  return <span className={`badge ${style}`}>{status.replaceAll("_", " ")}</span>;
}
