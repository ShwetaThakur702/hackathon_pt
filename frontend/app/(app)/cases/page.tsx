"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listCases } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { CaseListItem } from "@/types";
import StatusBadge from "@/components/StatusBadge";

export default function CaseCenterPage() {
  const { customerId } = useCustomer();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listCases({ customerId }).then(setCases).catch(console.error).finally(() => setLoading(false));
  }, [customerId]);

  const open = cases.filter((c) => c.status !== "RESOLVED");
  const resolved = cases.filter((c) => c.status === "RESOLVED");

  return (
    <div className="page-shell space-y-6">
      <div>
        <h1 className="text-xl font-bold text-ink">Your cases</h1>
        <p className="text-sm text-ink-secondary mt-1">Everything Nishchint is (or was) working on for you.</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <div key={i} className="h-16 rounded-xl skeleton" />
          ))}
        </div>
      ) : (
        <>
          <section>
            <h2 className="text-sm font-semibold text-ink-secondary mb-2">Open cases</h2>
            {open.length === 0 ? (
              <div className="card p-6 text-sm text-ink-secondary">No open cases.</div>
            ) : (
              <div className="card divide-y divide-border overflow-hidden stagger-list">
                {open.map((c) => (
                  <Link key={c.id} href={`/cases/${c.id}`} className="stagger-item flex items-center justify-between px-5 py-4 transition-colors duration-150 hover:bg-surface active:bg-brand-light/40">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-ink">
                        {c.id}
                        {c.merchant_name && <span className="text-ink-secondary"> · {c.merchant_name}</span>}
                      </div>
                      <div className="text-xs text-ink-secondary mt-0.5">
                        {(c.intent || "Case").replaceAll("_", " ")}
                        {c.upi_ref_no && <span className="font-mono"> · UPI Ref {c.upi_ref_no}</span>}
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      {c.amount !== null && <div className="text-sm font-semibold text-ink">₹{c.amount.toLocaleString("en-IN")}</div>}
                      {c.current_compensation !== null && c.current_compensation > 0 && (
                        <div className="text-xs font-medium text-danger">+₹{c.current_compensation.toLocaleString("en-IN")} comp.</div>
                      )}
                      <StatusBadge status={c.status} />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-sm font-semibold text-ink-secondary mb-2">Resolved</h2>
            {resolved.length === 0 ? (
              <div className="card p-6 text-sm text-ink-secondary">Nothing resolved yet.</div>
            ) : (
              <div className="card divide-y divide-border overflow-hidden stagger-list">
                {resolved.map((c) => (
                  <Link key={c.id} href={`/cases/${c.id}`} className="stagger-item flex items-center justify-between px-5 py-4 transition-colors duration-150 hover:bg-surface active:bg-brand-light/40">
                    <div className="text-sm font-medium text-ink">{c.id}</div>
                    <StatusBadge status={c.status} />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
