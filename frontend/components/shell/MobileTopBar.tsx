"use client";

import Link from "next/link";
import { useState } from "react";
import { useCustomer, DEMO_CUSTOMERS } from "@/lib/customer-context";
import LanguageSelector from "@/components/home/LanguageSelector";
import { BellIcon, SearchIcon, SparkleIcon, UserIcon } from "./icons";
import SearchModal from "./SearchModal";

export default function MobileTopBar() {
  const { customerId, setCustomerId, customer } = useCustomer();
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-border">
      <div className="flex items-center justify-between h-14 px-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-xs">
            N
          </span>
          <span className="font-bold text-brand-dark">Nishchint</span>
        </Link>
        <div className="flex items-center gap-1">
          <button onClick={() => setSearchOpen(true)} className="tap-target flex items-center justify-center" aria-label="Search">
            <SearchIcon className="w-5 h-5 text-ink-secondary" />
          </button>
          <Link
            href="/customer"
            className="tap-target flex items-center justify-center rounded-full bg-brand-dark text-white"
            aria-label="Open Nishchint assistant"
          >
            <SparkleIcon className="w-4 h-4" />
          </Link>
          <Link href="/notifications" className="tap-target flex items-center justify-center" aria-label="Notifications">
            <BellIcon className="w-5 h-5 text-ink-secondary" />
          </Link>
          <button
            onClick={() => setSwitcherOpen(true)}
            className="tap-target flex items-center justify-center rounded-full bg-brand-light text-brand-dark"
            aria-label={`Switch demo customer, currently ${customer.name}`}
          >
            <UserIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {switcherOpen && (
        <div className="fixed inset-0 z-40 flex items-end" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSwitcherOpen(false)} />
          <div className="relative w-full bg-white rounded-t-2xl p-4 pb-[calc(env(safe-area-inset-bottom)+16px)]">
            <h2 className="text-sm font-semibold text-ink mb-2">Reply language</h2>
            <div className="mb-4">
              <LanguageSelector variant="compact" />
            </div>
            <h2 className="text-sm font-semibold text-ink mb-3">Demo customer</h2>
            {DEMO_CUSTOMERS.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  setCustomerId(c.id);
                  setSwitcherOpen(false);
                }}
                className={`w-full text-left px-3 py-3 rounded-lg text-sm mb-1 ${
                  c.id === customerId ? "bg-brand-light text-brand-dark font-medium" : "hover:bg-surface text-ink"
                }`}
              >
                {c.name}
                <span className="block text-xs text-ink-secondary">{c.id}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
    </header>
  );
}
