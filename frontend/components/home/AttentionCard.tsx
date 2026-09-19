import Link from "next/link";
import type { AttentionItem } from "@/types";
import { SparkleIcon } from "@/components/shell/icons";

const TYPE_LABEL: Record<AttentionItem["type"], string> = {
  CASE: "Payment",
  TRANSACTION: "Payment",
  BILL: "Bill",
  FASTAG: "FASTag",
  AUTOPAY: "AutoPay",
  REFUND: "Refund",
};

export default function AttentionCard({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <div className="card p-5 flex items-center gap-3 animate-pop-in">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-success-light text-success">✓</span>
        <div>
          <div className="text-sm font-semibold text-ink">You&apos;re all caught up</div>
          <div className="text-xs text-ink-secondary">Nishchint isn&apos;t watching any exceptions right now.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 px-5 pt-5">
        <SparkleIcon className="w-4 h-4 text-brand-dark animate-pulse" />
        <h2 className="text-sm font-semibold text-ink">
          Nishchint is watching {items.length} thing{items.length > 1 ? "s" : ""} for you
        </h2>
      </div>
      <ul className="divide-y divide-border mt-3 stagger-list">
        {items.map((item) => (
          <li key={`${item.type}-${item.id}`} className="stagger-item">
            <Link
              href={item.cta_href}
              className="group flex items-center justify-between gap-3 px-5 py-4 transition-colors duration-150 hover:bg-surface active:bg-brand-light/40"
            >
              <div className="min-w-0">
                <div className="badge bg-brand-light text-brand-dark mb-1">{TYPE_LABEL[item.type]}</div>
                <div className="text-sm font-medium text-ink truncate">{item.title}</div>
                {item.subtitle && <div className="text-xs text-ink-secondary mt-0.5">{item.subtitle}</div>}
              </div>
              <span className="shrink-0 text-xs font-medium text-brand-dark whitespace-nowrap transition-transform duration-150 group-hover:translate-x-0.5">
                {item.cta_label} →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
