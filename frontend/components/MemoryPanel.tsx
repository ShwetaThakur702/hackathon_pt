import type { MemorySection } from "@/types";

export default function MemoryPanel({ memory, loading = false }: { memory: MemorySection | null; loading?: boolean }) {
  if (loading) {
    return (
      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-ink">Relevant history</h3>
          <span className="badge bg-surface text-ink-secondary">Loading…</span>
        </div>
        <div className="space-y-2">
          <div className="h-3 w-3/4 rounded skeleton" />
          <div className="h-3 w-1/2 rounded skeleton" />
        </div>
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-ink mb-1">Relevant history</h3>
        <p className="text-xs text-ink-secondary">Couldn&apos;t load your history right now — the rest of the case is unaffected.</p>
      </div>
    );
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-ink">Relevant history</h3>
        {memory.cognee_configured && <span className="badge bg-success-light text-success">Previous interaction found</span>}
      </div>

      {!memory.cognee_configured && (
        <p className="text-xs text-ink-secondary">Nothing on file yet for this account.</p>
      )}

      {memory.cognee_configured && (
        <div className="space-y-3">
          <div>
            <div className="text-xs font-semibold text-ink-secondary mb-1">Previous interactions</div>
            {memory.previous_interactions.length === 0 ? (
              <div className="text-xs text-ink-secondary">None found.</div>
            ) : (
              <ul className="space-y-1">
                {memory.previous_interactions.map((item, i) => (
                  <li key={i} className="text-xs text-ink border-l-2 border-brand-light pl-2">
                    {item.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <div className="text-xs font-semibold text-ink-secondary mb-1">Related merchant incidents</div>
            {memory.related_incidents.length === 0 ? (
              <div className="text-xs text-ink-secondary">None found.</div>
            ) : (
              <ul className="space-y-1">
                {memory.related_incidents.map((item, i) => (
                  <li key={i} className="text-xs text-ink border-l-2 border-brand-light pl-2">
                    {item.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
