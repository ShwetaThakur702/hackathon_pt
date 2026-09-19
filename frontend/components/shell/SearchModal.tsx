"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCustomerTransactions, listCases } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { CaseListItem, Transaction } from "@/types";
import { CloseIcon } from "./icons";

interface Result {
  key: string;
  label: string;
  sublabel: string;
  href: string;
}

export default function SearchModal({ onClose }: { onClose: () => void }) {
  const { customerId } = useCustomer();
  const [query, setQuery] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getCustomerTransactions(customerId), listCases({ customerId })])
      .then(([txns, caseList]) => {
        if (cancelled) return;
        setTransactions(txns);
        setCases(caseList);
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  const q = query.trim().toLowerCase();
  const results: Result[] = q
    ? [
        ...transactions
          .filter((t) => t.upi_ref_no.includes(q) || t.merchant_name?.toLowerCase().includes(q) || String(t.amount).includes(q))
          .map((t) => ({
            key: `txn-${t.id}`,
            label: `₹${t.amount.toLocaleString("en-IN")} · ${t.merchant_name || "P2P"}`,
            sublabel: `UPI Reference ID ${t.upi_ref_no}`,
            href: `/transactions/${t.id}`,
          })),
        ...cases
          .filter((c) => c.id.toLowerCase().includes(q))
          .map((c) => ({
            key: `case-${c.id}`,
            label: c.id,
            sublabel: c.status.replaceAll("_", " "),
            href: `/cases/${c.id}`,
          })),
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-lg card p-4">
        <div className="flex items-center gap-2 border border-border rounded-lg px-3 py-2 mb-3">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search UPI Reference ID, merchant, amount, or case ID"
            className="flex-1 text-sm outline-none"
          />
          <button onClick={onClose} aria-label="Close search">
            <CloseIcon className="w-4 h-4 text-ink-secondary" />
          </button>
        </div>

        {loading && <div className="text-sm text-ink-secondary px-2">Loading your data…</div>}
        {!loading && q && results.length === 0 && <div className="text-sm text-ink-secondary px-2">No matches for &quot;{query}&quot;.</div>}
        {!loading && !q && <div className="text-sm text-ink-secondary px-2">Try a UPI Reference ID, merchant, amount, or case ID.</div>}

        <ul className="max-h-72 overflow-y-auto divide-y divide-border">
          {results.map((r) => (
            <li key={r.key}>
              <Link href={r.href} onClick={onClose} className="flex items-center justify-between px-2 py-3 hover:bg-surface rounded-lg">
                <span className="text-sm font-medium text-ink">{r.label}</span>
                <span className="text-xs text-ink-secondary font-mono">{r.sublabel}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
