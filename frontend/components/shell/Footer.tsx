import Link from "next/link";
import { PRIMARY_NAV, MORE_NAV } from "./nav-items";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="hidden lg:block border-t border-border bg-white mt-12">
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="grid grid-cols-4 gap-8">
          <div className="col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-sm">
                N
              </span>
              <span className="font-bold text-lg text-brand-dark tracking-tight">Nishchint</span>
            </Link>
            <p className="text-sm text-ink-secondary mt-3 max-w-xs">
              Your autonomous payment &amp; service resolution assistant — Nishchint notices, investigates, acts and
              follows up so you don&apos;t have to keep checking.
            </p>
          </div>

          <div>
            <div className="text-xs font-semibold text-ink-secondary uppercase tracking-wide mb-3">Services</div>
            <ul className="space-y-2">
              {PRIMARY_NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-sm text-ink hover:text-brand-dark transition-colors duration-150">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="text-xs font-semibold text-ink-secondary uppercase tracking-wide mb-3">More</div>
            <ul className="space-y-2">
              {MORE_NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-sm text-ink hover:text-brand-dark transition-colors duration-150">
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <Link href="/operations" className="text-sm text-ink hover:text-brand-dark transition-colors duration-150">
                  Operations Console
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-between mt-10 pt-6 border-t border-border">
          <p className="text-xs text-ink-secondary">© {year} Nishchint. Prototype — not a real payments product.</p>
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            <span className="text-xs text-ink-secondary">All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
