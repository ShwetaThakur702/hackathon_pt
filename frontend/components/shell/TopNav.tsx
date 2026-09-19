"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useCustomer } from "@/lib/customer-context";
import LanguageSelector from "@/components/home/LanguageSelector";
import WaveExitOverlay from "@/components/transition/WaveExitOverlay";
import { useWaveNavigate } from "@/components/transition/useWaveNavigate";
import Wordmark from "./Wordmark";
import { MORE_NAV, PRIMARY_NAV } from "./nav-items";
import { BellIcon, HomeIcon, MoreIcon, SearchIcon, SparkleIcon, UserIcon } from "./icons";
import SearchModal from "./SearchModal";

const dropdownMotion = {
  initial: { opacity: 0, y: -6, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -6, scale: 0.98 },
  transition: { duration: 0.15, ease: [0.16, 1, 0.3, 1] as const },
};

export default function TopNav() {
  const pathname = usePathname();
  const { customer } = useCustomer();
  const [searchOpen, setSearchOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const { active: waveActive, navigate: waveNavigate, handleCovered } = useWaveNavigate();

  const moreActive = MORE_NAV.some((item) => item.href === pathname);

  return (
    <header className="hidden lg:block sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-border">
      <WaveExitOverlay active={waveActive} onCovered={handleCovered} />
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center h-16 gap-6">
          <button
            onClick={() => waveNavigate("/", "Welcome back to Paytm", "Recharges, bills and payments — all in one place.")}
            className="btn-outline btn-sm text-ink-secondary shrink-0"
            title="Back to Paytm"
          >
            <HomeIcon className="w-4 h-4" />
            <span>Paytm</span>
          </button>

          <Link href="/nishchint" className="flex items-center gap-2 shrink-0">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-sm">
              N
            </span>
            <Wordmark className="font-bold text-lg tracking-tight" />
          </Link>

          <nav className="flex items-center gap-1">
            {PRIMARY_NAV.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors duration-150 ${
                    active ? "text-brand-dark" : "text-ink-secondary hover:bg-surface hover:text-ink"
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="topnav-active"
                      className="absolute inset-0 rounded-lg bg-brand-light"
                      transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    />
                  )}
                  <span className="relative">{item.label}</span>
                </Link>
              );
            })}

            <div className="relative">
              <button
                onClick={() => setMoreOpen((v) => !v)}
                className={`relative flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors duration-150 ${
                  moreActive || moreOpen ? "text-brand-dark" : "text-ink-secondary hover:bg-surface hover:text-ink"
                }`}
                aria-haspopup="true"
                aria-expanded={moreOpen}
              >
                {(moreActive || moreOpen) && (
                  <motion.span layoutId="topnav-active" className="absolute inset-0 rounded-lg bg-brand-light" transition={{ type: "spring", stiffness: 500, damping: 35 }} />
                )}
                <span className="relative flex items-center gap-1">
                  More
                  <MoreIcon className="w-3.5 h-3.5" />
                </span>
              </button>
              <AnimatePresence>
                {moreOpen && (
                  <motion.div
                    {...dropdownMotion}
                    className="absolute left-0 mt-2 w-48 card p-1.5 z-40 origin-top-left"
                    onMouseLeave={() => setMoreOpen(false)}
                  >
                    {MORE_NAV.map((item) => {
                      const active = pathname === item.href;
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setMoreOpen(false)}
                          className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors duration-150 ${
                            active ? "bg-brand-light text-brand-dark font-medium" : "text-ink hover:bg-surface"
                          }`}
                        >
                          <Icon className="w-4 h-4 text-brand-dark" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </nav>

          <div className="flex-1" />

          <button
            onClick={() => setSearchOpen(true)}
            className="btn-outline btn-sm text-ink-secondary"
          >
            <SearchIcon className="w-4 h-4" />
            <span>Search</span>
          </button>

          <Link
            href="/customer"
            className={`btn btn-sm gap-1.5 rounded-full ${
              pathname === "/customer" ? "bg-brand-light text-brand-dark" : "bg-brand-dark text-white hover:bg-brand-navy shadow-sm hover:shadow-md hover:-translate-y-px"
            }`}
          >
            <SparkleIcon className="w-4 h-4" />
            <span>Assistant</span>
          </Link>

          <Link
            href="/notifications"
            className={`tap-target flex items-center justify-center rounded-full transition-colors duration-150 ${
              pathname === "/notifications" ? "bg-brand-light text-brand-dark" : "hover:bg-surface"
            }`}
            aria-label="Notifications"
          >
            <BellIcon />
          </Link>

          <div className="relative">
            <button
              onClick={() => setProfileOpen((v) => !v)}
              className="tap-target flex items-center gap-2 rounded-full pl-1 pr-3 py-1 hover:bg-surface transition-colors duration-150"
              aria-haspopup="true"
              aria-expanded={profileOpen}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-light text-brand-dark">
                <UserIcon className="w-4 h-4" />
              </span>
              <span className="text-sm font-medium text-ink">{customer.name.split(" ")[0]}</span>
            </button>
            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  {...dropdownMotion}
                  className="absolute right-0 mt-2 w-56 card p-2 z-40 origin-top-right"
                  onMouseLeave={() => setProfileOpen(false)}
                >
                  <div className="px-2 py-1.5 text-xs text-ink-secondary">Reply language</div>
                  <div className="px-2 pb-2">
                    <LanguageSelector variant="compact" />
                  </div>
                  <Link
                    href="/profile"
                    onClick={() => setProfileOpen(false)}
                    className="block px-2 py-2 mt-1 rounded-lg text-sm text-brand-dark hover:bg-surface border-t border-border transition-colors duration-150"
                  >
                    View profile
                  </Link>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
    </header>
  );
}
