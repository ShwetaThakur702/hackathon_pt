import { motion } from "framer-motion";

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
 * status — never auto-animated forward, never further along than the case
 * truly is. Only the *presentation* of a real status change animates. */
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
              <motion.span
                layout
                initial={false}
                animate={active ? { scale: [1, 1.15, 1] } : { scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className={`relative flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold ${
                  done
                    ? "bg-success text-white"
                    : active
                      ? "bg-brand-dark text-white"
                      : "bg-surface text-ink-secondary border border-border"
                }`}
              >
                {active && (
                  <motion.span
                    className="absolute inset-0 rounded-full bg-brand-dark"
                    animate={{ scale: [1, 1.8], opacity: [0.5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
                  />
                )}
                <span className="relative">{done ? "✓" : active ? "●" : "○"}</span>
              </motion.span>
              <span className={`text-[10px] text-center leading-tight ${active ? "text-ink font-medium" : "text-ink-secondary"}`}>
                {label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div className="h-px w-6 bg-border relative overflow-hidden">
                <motion.div
                  className="absolute inset-0 bg-success origin-left"
                  initial={false}
                  animate={{ scaleX: i < currentStage ? 1 : 0 }}
                  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
