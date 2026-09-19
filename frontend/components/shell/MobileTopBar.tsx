"use client";

import Link from "next/link";
import { useState } from "react";
import { useCustomer } from "@/lib/customer-context";
import LanguageSelector from "@/components/home/LanguageSelector";
import WaveExitOverlay from "@/components/transition/WaveExitOverlay";
import { useWaveNavigate } from "@/components/transition/useWaveNavigate";
import Wordmark from "./Wordmark";
import { BellIcon, HomeIcon, SearchIcon, SparkleIcon, UserIcon } from "./icons";
import SearchModal from "./SearchModal";

export default function MobileTopBar() {
  const { customer } = useCustomer();
  const [profileOpen, setProfileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const { active: waveActive, navigate: waveNavigate, handleCovered } = useWaveNavigate();

  return (
    <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-border">
      <WaveExitOverlay active={waveActive} onCovered={handleCovered} />
      <div className="flex items-center justify-between h-14 px-4">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => waveNavigate("/", "Welcome back to Paytm", "Recharges, bills and payments — all in one place.")}
            className="tap-target flex items-center justify-center"
            aria-label="Back to Paytm"
            title="Back to Paytm"
          >
            <HomeIcon className="w-5 h-5 text-ink-secondary" />
          </button>
          <Link href="/nishchint" className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-xs">
              N
            </span>
            <Wordmark className="font-bold" />
          </Link>
        </div>
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
            onClick={() => setProfileOpen(true)}
            className="tap-target flex items-center justify-center rounded-full bg-brand-light text-brand-dark"
            aria-label={`${customer.name}'s profile`}
          >
            <UserIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {profileOpen && (
        <div className="fixed inset-0 z-40 flex items-end" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/30" onClick={() => setProfileOpen(false)} />
          <div className="relative w-full bg-white rounded-t-2xl p-4 pb-[calc(env(safe-area-inset-bottom)+16px)]">
            <h2 className="text-sm font-semibold text-ink mb-1">{customer.name}</h2>
            <p className="text-xs text-ink-secondary mb-4">Reply language</p>
            <div className="mb-4">
              <LanguageSelector variant="compact" />
            </div>
            <Link
              href="/profile"
              onClick={() => setProfileOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-sm text-brand-dark hover:bg-surface border-t border-border pt-4"
            >
              View profile
            </Link>
          </div>
        </div>
      )}
      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
    </header>
  );
}
