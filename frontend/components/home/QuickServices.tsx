import Link from "next/link";
import { AutoPayIcon, BillsIcon, FastagIcon, PaymentsIcon, PlaneIcon, RefundsIcon } from "@/components/shell/icons";

const SERVICES = [
  { label: "UPI", href: "/payments", icon: PaymentsIcon },
  { label: "Bills", href: "/bills", icon: BillsIcon },
  { label: "FASTag", href: "/fastag", icon: FastagIcon },
  { label: "AutoPay", href: "/autopay", icon: AutoPayIcon },
  { label: "Refunds", href: "/refunds", icon: RefundsIcon },
  { label: "Travel", href: "/travel", icon: PlaneIcon },
];

export default function QuickServices() {
  return (
    <div className="card p-5">
      <h2 className="text-sm font-semibold text-ink mb-4">Quick services</h2>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 stagger-list">
        {SERVICES.map((s) => {
          const Icon = s.icon;
          return (
            <Link
              key={s.label}
              href={s.href}
              className="stagger-item tap-target group flex flex-col items-center gap-2 rounded-xl border border-border py-4 text-xs text-ink
                transition-all duration-200 hover:border-brand hover:bg-brand-light/40 hover:-translate-y-0.5 hover:shadow-sm active:scale-95"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-light text-brand-dark transition-transform duration-200 group-hover:scale-110">
                <Icon className="w-5 h-5" />
              </span>
              {s.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
