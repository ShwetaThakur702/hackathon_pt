"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCustomerTransactions } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import { displayStatus } from "@/lib/transaction-status";
import type { Transaction } from "@/types";
import TransactionRow from "@/components/TransactionRow";

const FILTERS = ["All", "UPI", "P2P", "Needs attention"] as const;
type Filter = (typeof FILTERS)[number];

export default function PaymentsPage() {
  const { customerId } = useCustomer();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filter, setFilter] = useState<Filter>("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCustomerTransactions(customerId)
      .then(setTransactions)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [customerId]);

  const filtered = transactions.filter((t) => {
    if (filter === "All") return true;
    if (filter === "UPI") return t.type === "MERCHANT";
    if (filter === "P2P") return t.type === "PERSON";
    if (filter === "Needs attention") return displayStatus(t) === "Needs attention";
    return true;
  });

  return (
    <div className="page-shell space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-ink">Payments</h1>
          <p className="text-sm text-ink-secondary mt-1">Your UPI activity, verified against live transaction state.</p>
        </div>
        <Link href="/payments/send" className="btn-primary btn-md shrink-0">
          Send Money
        </Link>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`shrink-0 tap-target rounded-full px-4 py-1.5 text-sm font-medium border transition-all duration-150 active:scale-95 ${
              filter === f ? "bg-brand-dark text-white border-brand-dark shadow-sm" : "border-border text-ink-secondary hover:border-brand hover:text-brand-dark"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-5 space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-10 rounded-lg skeleton" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-sm text-ink-secondary">No transactions match this filter.</div>
        ) : (
          <div className="divide-y divide-border stagger-list">
            {filtered.map((t) => (
              <div key={t.id} className="stagger-item">
                <TransactionRow txn={t} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
