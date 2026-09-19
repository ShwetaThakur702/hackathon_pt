"use client";

import Link from "next/link";
import SimulationControls from "@/components/SimulationControls";

export default function CaseTracker({
  caseId,
  resolved,
  resolvedText,
  onChanged,
}: {
  caseId: string;
  resolved: boolean;
  resolvedText: string;
  onChanged: () => void;
}) {
  return (
    <div className="mt-2 space-y-3 animate-fade-in-up">
      <p className="text-xs text-success font-medium">
        ✓ Case {caseId} {resolved ? "resolved" : "created — I'm monitoring this."}{" "}
        <Link href={`/cases/${caseId}`} className="text-brand-dark underline">
          View case →
        </Link>
      </p>
      {resolved ? (
        <p className="text-xs text-ink">{resolvedText}</p>
      ) : (
        <SimulationControls caseId={caseId} onChanged={onChanged} />
      )}
    </div>
  );
}
