"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { sendPayment } from "@/lib/api";
import { CUSTOMER_ID } from "@/lib/customer-context";
import type { Transaction } from "@/types";
import NishchintWidget from "@/components/paytm/NishchintWidget";
import WaveEntranceOverlay from "@/components/transition/WaveEntranceOverlay";
import Wordmark from "@/components/shell/Wordmark";
import { AutoPayIcon, BillsIcon, BusIcon, FastagIcon, PaymentsIcon, PlaneIcon, RefundsIcon, TrainIcon, UserIcon } from "@/components/shell/icons";

const BILL_SERVICES = [
  { label: "Mobile Recharge", href: "/bills", icon: PaymentsIcon },
  { label: "Electricity Bill", href: "/bills", icon: BillsIcon },
  { label: "FASTag Recharge", href: "/fastag", icon: FastagIcon },
  { label: "AutoPay Mandates", href: "/autopay", icon: AutoPayIcon },
  { label: "Refunds", href: "/refunds", icon: RefundsIcon },
  { label: "All Services", href: "/nishchint", icon: PaymentsIcon },
];

const TRAVEL_TABS = [
  { label: "Flights", icon: PlaneIcon },
  { label: "Trains", icon: TrainIcon },
  { label: "Bus", icon: BusIcon },
];

export default function PaytmStyleLanding() {
  const [payState, setPayState] = useState<"idle" | "paying" | "done">("idle");
  const [failedPayment, setFailedPayment] = useState<Transaction | null>(null);
  const [travelTab, setTravelTab] = useState(0);

  async function quickPay() {
    setPayState("paying");
    setFailedPayment(null);
    try {
      const txn = await sendPayment(CUSTOMER_ID, "Apollo Medicals", "MERCHANT", 2400);
      setPayState("done");
      if (txn.status === "FAILED") {
        setFailedPayment(txn);
      }
      setTimeout(() => setPayState("idle"), 2500);
    } catch {
      setPayState("idle");
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <WaveEntranceOverlay />
      {/* Header — Paytm-style layout, original Nishchint branding (not a clone) */}
      <header className="bg-white border-b border-border sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center gap-8">
          <div className="flex items-center gap-2 shrink-0">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-dark text-white font-bold text-sm">
              P
            </span>
            <span className="font-bold text-lg tracking-tight">
              <span className="text-brand-dark">Pay</span>
              <span className="text-brand">tm</span>
            </span>
            <span className="hidden sm:inline text-ink-secondary">·</span>
            <span className="hidden sm:inline text-sm text-ink-secondary">UPI</span>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-ink flex-1">
            {["Recharge & Bills", "Ticket Booking", "Payments & Services", "For Business"].map((label) => (
              <span key={label} className="flex items-center gap-1 text-ink-secondary hover:text-ink cursor-default transition-colors">
                {label}
                <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            ))}
          </nav>

          <div className="flex-1 md:hidden" />

          <Link href="/nishchint" className="flex items-center gap-2 rounded-full pl-1 pr-3 py-1 hover:bg-surface transition-colors">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-light text-brand-dark">
              <UserIcon className="w-4 h-4" />
            </span>
            <span className="text-sm font-medium text-ink hidden sm:inline">Priya Sharma</span>
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="grid lg:grid-cols-[2fr_1fr] gap-6">
          {/* Recharges & Bill Payments */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-6">
            <h1 className="text-lg font-bold text-ink mb-5">Recharges &amp; Bill Payments</h1>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-4 stagger-list">
              {BILL_SERVICES.map((s) => {
                const Icon = s.icon;
                return (
                  <Link
                    key={s.label}
                    href={s.href}
                    className="stagger-item flex flex-col items-center gap-2 text-center group"
                  >
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-white transition-all duration-200 group-hover:border-brand group-hover:shadow-md group-hover:-translate-y-0.5">
                      <Icon className="w-6 h-6 text-brand-dark" />
                    </span>
                    <span className="text-xs text-ink leading-tight">{s.label}</span>
                  </Link>
                );
              })}
            </div>
          </motion.div>

          {/* Quick pay demo — the flagship failed-payment scenario, live on this page */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="card p-6 gradient-brand text-white flex flex-col"
          >
            <div className="text-xs text-white/60 mb-1">Quick Pay</div>
            <div className="text-lg font-semibold mb-1">Apollo Medicals</div>
            <div className="text-3xl font-bold mb-4">₹2,400</div>
            <p className="text-xs text-white/70 mb-5 flex-1">
              UPI payment to a saved merchant. If anything goes wrong, Nishchint steps in automatically — no ticket
              to raise.
            </p>
            <button
              onClick={quickPay}
              disabled={payState === "paying"}
              className="btn btn-md bg-white text-brand-dark hover:bg-brand-light disabled:opacity-70"
            >
              {payState === "paying" ? "Processing…" : payState === "done" ? "Done — see Nishchint ↘" : "Pay ₹2,400"}
            </button>
          </motion.div>
        </div>

        {/* Travel widget — decorative, matching the layout only */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-6">
              {TRAVEL_TABS.map((t, i) => {
                const Icon = t.icon;
                const active = i === travelTab;
                return (
                  <button
                    key={t.label}
                    onClick={() => setTravelTab(i)}
                    className={`flex flex-col items-center gap-1 pb-2 border-b-2 transition-colors duration-150 ${
                      active ? "border-brand-dark text-brand-dark" : "border-transparent text-ink-secondary hover:text-ink"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-xs font-medium">{t.label}</span>
                  </button>
                );
              })}
            </div>
            <div className="hidden sm:flex items-center gap-1.5 font-bold">
              <Wordmark className="text-lg tracking-tight" />
              <span className="text-ink-secondary font-normal text-sm">travel</span>
            </div>
          </div>

          <div className="rounded-xl border border-border p-4 grid sm:grid-cols-4 gap-4 items-end">
            <div>
              <div className="text-xs text-ink-secondary mb-1">From</div>
              <div className="text-sm font-semibold text-ink">Delhi (DEL)</div>
            </div>
            <div>
              <div className="text-xs text-ink-secondary mb-1">To</div>
              <div className="text-sm font-semibold text-ink">Mumbai (BOM)</div>
            </div>
            <div>
              <div className="text-xs text-ink-secondary mb-1">Depart</div>
              <div className="text-sm font-semibold text-ink">Today</div>
            </div>
            <Link href="/travel" className="btn-primary btn-md w-full">
              Search {TRAVEL_TABS[travelTab].label}
            </Link>
          </div>
        </motion.div>

        <p className="text-xs text-ink-secondary text-center pb-4">
          This is a prototype landing page styled to demonstrate Nishchint embedded as a widget inside a larger
          fintech app — not affiliated with or a copy of any real product.
        </p>
      </main>

      <NishchintWidget failedPayment={failedPayment} />
    </div>
  );
}
