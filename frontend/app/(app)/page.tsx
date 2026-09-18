"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getAttention, getCustomerTransactions } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { AttentionItem, Transaction } from "@/types";
import AttentionCard from "@/components/home/AttentionCard";
import QuickServices from "@/components/home/QuickServices";
import TransactionRow from "@/components/TransactionRow";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function HomePage() {
  const { customerId, customer } = useCustomer();
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

  return (
    <div className="page-shell space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">
          {greeting()}, {customer.name.split(" ")[0]}
        </h1>
        <p className="text-sm text-ink-secondary mt-1">Here&apos;s what&apos;s happening with your money.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Send Money", href: "/payments" },
          { label: "Scan & Pay", href: "/payments" },
          { label: "Recharge", href: "/bills" },
          { label: "Pay Bills", href: "/bills" },
        ].map((a) => (
          <Link
            key={a.label}
            href={a.href}
            className="tap-target rounded-xl bg-brand-dark text-white text-sm font-medium px-4 py-3 text-center hover:bg-brand-navy transition-colors"
          >
            {a.label}
          </Link>
        ))}
      </div>

      {loading ? (
        <div className="card p-5 h-24 animate-pulse bg-surface" aria-hidden />
      ) : (
        <AttentionCard items={items} />
      )}

      <QuickServices />

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5 pb-1">
          <h2 className="text-sm font-semibold text-ink">Recent transactions</h2>
          <Link href="/payments" className="text-xs font-medium text-brand-dark">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="p-5 space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-10 rounded-lg bg-surface animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-border mt-2">
            {transactions.slice(0, 4).map((t) => (
              <TransactionRow key={t.id} txn={t} />
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
            <div key={offer} className="shrink-0 w-48 rounded-lg bg-white border border-border px-3 py-3 text-xs text-ink">
              {offer}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
