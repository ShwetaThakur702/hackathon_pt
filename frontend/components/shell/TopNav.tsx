"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useCustomer, DEMO_CUSTOMERS } from "@/lib/customer-context";
import LanguageSelector from "@/components/home/LanguageSelector";
import { ALL_NAV } from "./nav-items";
import { BellIcon, SearchIcon, SparkleIcon, UserIcon } from "./icons";
import SearchModal from "./SearchModal";

export default function TopNav() {
  const pathname = usePathname();
  const { customerId, setCustomerId, customer } = useCustomer();
  const [searchOpen, setSearchOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="hidden lg:block sticky top-0 z-30 bg-white border-b border-border">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center h-16 gap-8">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-sm">
              N
            </span>
            <span className="font-bold text-lg text-brand-dark tracking-tight">Nishchint</span>
          </Link>

          <nav className="flex items-center gap-1 flex-1">
            {ALL_NAV.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active ? "bg-brand-light text-brand-dark" : "text-ink-secondary hover:bg-surface hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <button
            onClick={() => setSearchOpen(true)}
            className="tap-target flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm text-ink-secondary hover:border-brand"
          >
            <SearchIcon className="w-4 h-4" />
            <span>Search</span>
          </button>

          <Link
            href="/customer"
            className={`tap-target flex items-center gap-1.5 rounded-full pl-2.5 pr-3 py-1.5 text-sm font-medium transition-colors ${
              pathname === "/customer" ? "bg-brand-light text-brand-dark" : "bg-brand-dark text-white hover:bg-brand-navy"
            }`}
          >
            <SparkleIcon className="w-4 h-4" />
            <span>Assistant</span>
          </Link>

          <Link href="/notifications" className="tap-target flex items-center justify-center rounded-full hover:bg-surface" aria-label="Notifications">
            <BellIcon />
          </Link>

          <div className="relative">
            <button
              onClick={() => setProfileOpen((v) => !v)}
              className="tap-target flex items-center gap-2 rounded-full pl-1 pr-3 py-1 hover:bg-surface"
              aria-haspopup="true"
              aria-expanded={profileOpen}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-light text-brand-dark">
                <UserIcon className="w-4 h-4" />
              </span>
              <span className="text-sm font-medium text-ink">{customer.name.split(" ")[0]}</span>
            </button>
            {profileOpen && (
              <div className="absolute right-0 mt-2 w-56 card p-2 z-40" onMouseLeave={() => setProfileOpen(false)}>
                <div className="px-2 py-1.5 text-xs text-ink-secondary">Reply language</div>
                <div className="px-2 pb-2">
                  <LanguageSelector variant="compact" />
                </div>
                <div className="px-2 py-1.5 text-xs text-ink-secondary border-t border-border pt-2">Demo customer</div>
                {DEMO_CUSTOMERS.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setCustomerId(c.id);
                      setProfileOpen(false);
                    }}
                    className={`w-full text-left px-2 py-2 rounded-lg text-sm ${
                      c.id === customerId ? "bg-brand-light text-brand-dark font-medium" : "hover:bg-surface text-ink"
                    }`}
                  >
                    {c.name}
                    <span className="block text-xs text-ink-secondary">{c.id}</span>
                  </button>
                ))}
                <Link
                  href="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="block px-2 py-2 mt-1 rounded-lg text-sm text-brand-dark hover:bg-surface border-t border-border"
                >
                  View profile
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
    </header>
  );
}
