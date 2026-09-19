"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getAttention, getCustomerTransactions } from "@/lib/api";
import { useAssistant } from "@/lib/assistant-context";
import { useCustomer } from "@/lib/customer-context";
import type { AttentionItem, Transaction } from "@/types";
import AnimatedNumber from "@/components/AnimatedNumber";
import AttentionCard from "@/components/home/AttentionCard";
import QuickServices from "@/components/home/QuickServices";
import TransactionRow from "@/components/TransactionRow";
import WaveEntranceOverlay from "@/components/transition/WaveEntranceOverlay";
import { BillsIcon, FastagIcon, PaymentsIcon } from "@/components/shell/icons";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

export default function HomePage() {
  const { customerId, customer } = useCustomer();
  const { setPageContext } = useAssistant();
  const [items, setItems] = useState<AttentionItem[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [attention, txns] = await Promise.all([getAttention(customerId), getCustomerTransactions(customerId)]);
      setItems(attention.items);
      setTransactions(txns);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (loading) return;
    if (items.length === 0) {
      setPageContext(null);
      return;
    }
    setPageContext({
      summary: "the things I found that may need your attention",
      suggestedMessage:
        items.length === 1
          ? `Tell me more about ${items[0].title}.`
          : `I found something that may need your attention — can you walk me through it?`,
    });
    return () => setPageContext(null);
  }, [loading, items, setPageContext]);

  const totalSpent = transactions.filter((t) => t.debited).reduce((sum, t) => sum + t.amount, 0);

  return (
    <div className="page-shell space-y-6">
      <WaveEntranceOverlay />
      <div className="relative overflow-hidden rounded-2xl gradient-brand text-white p-6 animate-fade-in-up">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/5" aria-hidden />
        <div className="absolute -right-4 bottom-0 h-24 w-24 rounded-full bg-brand/20" aria-hidden />
        <div className="relative">
          <h1 className="text-2xl font-bold">
            {greeting()}, {customer.name.split(" ")[0]}
          </h1>
          <p className="text-sm text-white/70 mt-1">Here&apos;s what&apos;s happening with your money.</p>

          <div className="flex flex-wrap gap-8 mt-6 pt-5 border-t border-white/15">
            <div className="text-center">
              <div className="text-xs text-white/60">Transactions</div>
              {loading ? (
                <div className="h-6 w-10 mx-auto rounded skeleton bg-white/10 mt-1" />
              ) : (
                <AnimatedNumber value={transactions.length} className="text-xl font-semibold tabular-nums" />
              )}
            </div>
            <div className="text-center">
              <div className="text-xs text-white/60">Total activity</div>
              {loading ? (
                <div className="h-6 w-16 mx-auto rounded skeleton bg-white/10 mt-1" />
              ) : (
                <AnimatedNumber value={totalSpent} prefix="₹" className="text-xl font-semibold tabular-nums" />
              )}
            </div>
            <div className="text-center">
              <div className="text-xs text-white/60">Nishchint is watching</div>
              {loading ? (
                <div className="h-6 w-10 mx-auto rounded skeleton bg-white/10 mt-1" />
              ) : (
                <AnimatedNumber value={items.length} className="text-xl font-semibold tabular-nums" />
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 stagger-list">
        {[
          { label: "Send Money", href: "/payments/send", icon: PaymentsIcon },
          { label: "Scan & Pay", href: "/payments/send", icon: PaymentsIcon },
          { label: "Recharge", href: "/bills", icon: BillsIcon },
          { label: "Pay Bills", href: "/bills", icon: BillsIcon },
          { label: "FASTag", href: "/fastag", icon: FastagIcon },
        ].map((a) => {
          const Icon = a.icon;
          return (
            <Link
              key={a.label}
              href={a.href}
              className="stagger-item tap-target group flex flex-col items-center justify-center gap-2 rounded-xl gradient-brand text-white text-sm font-medium py-4 text-center
                transition-all duration-200 hover:brightness-110 hover:-translate-y-0.5 hover:shadow-lg active:scale-95"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15 transition-transform duration-200 group-hover:scale-110">
                <Icon className="w-5 h-5" />
              </span>
              {a.label}
            </Link>
          );
        })}
      </div>

      {loading ? (
        <div className="card p-5 h-24 skeleton" aria-hidden />
      ) : (
        <div className="animate-fade-in-up">
          <AttentionCard items={items} />
        </div>
      )}

      <QuickServices />

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5 pb-1">
          <h2 className="text-sm font-semibold text-ink">Recent transactions</h2>
          <Link href="/payments" className="text-xs font-medium text-brand-dark hover:underline transition-all">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="p-5 space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-10 rounded-lg skeleton" />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-border mt-2 stagger-list">
            {transactions.slice(0, 4).map((t) => (
              <div key={t.id} className="stagger-item">
                <TransactionRow txn={t} />
              </div>
            ))}
            {transactions.length === 0 && <div className="px-5 py-6 text-sm text-ink-secondary">No transactions yet.</div>}
          </div>
        )}
      </div>

      <div className="card p-5 bg-gradient-to-br from-brand-light to-white">
        <h2 className="text-sm font-semibold text-ink mb-1">Rewards &amp; offers</h2>
        <p className="text-xs text-ink-secondary mb-3">Cashback and coupons picked for you.</p>
        <div className="flex gap-3 overflow-x-auto">
          {["5% cashback on electricity bills", "₹50 off on your next FASTag recharge", "Zero-fee AutoPay setup this month"].map((offer) => (
            <div
              key={offer}
              className="shrink-0 w-48 rounded-lg bg-white border border-border px-3 py-3 text-xs text-ink transition-all duration-200 hover:shadow-sm hover:-translate-y-0.5 hover:border-brand-light"
            >
              {offer}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
