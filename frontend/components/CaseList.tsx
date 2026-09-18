import Link from "next/link";
import type { CaseListItem } from "@/types";
import StatusBadge from "./StatusBadge";

export default function CaseList({ cases, selectedId, onSelect }: { cases: CaseListItem[]; selectedId: string | null; onSelect: (id: string) => void }) {
  if (cases.length === 0) {
    return <div className="text-sm text-slate-400 p-4">No cases yet.</div>;
  }

  return (
    <ul className="divide-y divide-slate-100">
      {cases.map((c) => (
        <li key={c.id}>
          <button
            onClick={() => onSelect(c.id)}
            className={`w-full text-left px-4 py-3 hover:bg-slate-50 ${selectedId === c.id ? "bg-brand-light" : ""}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{c.id}</span>
              <StatusBadge status={c.status} />
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
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
    <Link href={`/cases/${caseId}`} className="text-xs text-brand hover:underline">
      Open full timeline →
    </Link>
  );
}
