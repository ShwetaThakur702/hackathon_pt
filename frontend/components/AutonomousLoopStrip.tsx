const STAGES = ["Understood", "Investigated", "Decision made", "Action taken", "Monitoring", "Resolution"];

const STATUS_TO_STAGE: Record<string, number> = {
  NEW: 0,
  INVESTIGATING: 1,
  DECIDED: 2,
  ACTION_TAKEN: 3,
  FOLLOW_UP_SCHEDULED: 4,
  WAITING_FOR_RESOLUTION: 4,
  RECHECKING: 4,
  RESOLVED: 5,
  DISPUTE_RAISED: 5,
  HUMAN_ESCALATED: 5,
};

/** Renders the UNDERSTAND→...→RESOLVE loop reflecting a real case's actual
 * status — never auto-animated, never further along than the case truly is. */
export default function AutonomousLoopStrip({ status }: { status: string }) {
  const currentStage = STATUS_TO_STAGE[status] ?? 0;

  return (
    <div className="flex items-center overflow-x-auto">
      {STAGES.map((label, i) => {
        const done = i < currentStage;
        const active = i === currentStage;
        return (
          <div key={label} className="flex items-center shrink-0">
            <div className="flex flex-col items-center gap-1 w-20">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold ${
                  done
                    ? "bg-success text-white"
                    : active
                      ? "bg-brand-dark text-white"
                      : "bg-surface text-ink-secondary border border-border"
                }`}
              >
                {done ? "✓" : active ? "●" : "○"}
              </span>
              <span className={`text-[10px] text-center leading-tight ${active ? "text-ink font-medium" : "text-ink-secondary"}`}>
                {label}
              </span>
            </div>
            {i < STAGES.length - 1 && <div className={`h-px w-6 ${i < currentStage ? "bg-success" : "bg-border"}`} />}
          </div>
        );
      })}
    </div>
  );
}
