"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { MORE_NAV, PRIMARY_NAV } from "./nav-items";
import { CloseIcon, MoreIcon } from "./icons";

export default function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <>
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-border pb-[env(safe-area-inset-bottom)]">
        <div className="grid grid-cols-5">
          {PRIMARY_NAV.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`tap-target flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] ${
                  active ? "text-brand-dark" : "text-ink-secondary"
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
          <button
            onClick={() => setMoreOpen(true)}
            className="tap-target flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] text-ink-secondary"
          >
            <MoreIcon className="w-5 h-5" />
            More
          </button>
        </div>
      </nav>

      {moreOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex items-end" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMoreOpen(false)} />
          <div className="relative w-full bg-white rounded-t-2xl p-4 pb-[calc(env(safe-area-inset-bottom)+16px)]">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-ink">More services</h2>
              <button onClick={() => setMoreOpen(false)} className="tap-target flex items-center justify-center" aria-label="Close">
                <CloseIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {MORE_NAV.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className="flex flex-col items-center gap-2 rounded-xl border border-border py-4 text-xs text-ink hover:border-brand"
                  >
                    <Icon className="w-5 h-5 text-brand-dark" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
