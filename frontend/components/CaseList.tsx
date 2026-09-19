import Link from "next/link";
import type { CaseListItem } from "@/types";
import StatusBadge from "./StatusBadge";

export default function CaseList({ cases, selectedId, onSelect }: { cases: CaseListItem[]; selectedId: string | null; onSelect: (id: string) => void }) {
  if (cases.length === 0) {
    return <div className="text-sm text-ink-secondary p-4">No cases yet.</div>;
  }

  return (
    <ul className="divide-y divide-border stagger-list">
      {cases.map((c) => (
        <li key={c.id} className="stagger-item">
          <button
            onClick={() => onSelect(c.id)}
            className={`w-full text-left px-4 py-3 transition-colors duration-150 hover:bg-surface ${
              selectedId === c.id ? "bg-brand-light" : ""
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">{c.id}</span>
              <StatusBadge status={c.status} />
            </div>
            <div className="text-xs text-ink-secondary mt-0.5">
              {c.customer_id}
              {c.escalation_reason ? ` · ${c.escalation_reason.replaceAll("_", " ")}` : ""}
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}

export function CaseListLink({ caseId }: { caseId: string }) {
  return (
    <Link href={`/cases/${caseId}`} className="text-xs text-brand-dark hover:underline transition-all">
      Open full timeline →
    </Link>
  );
}
