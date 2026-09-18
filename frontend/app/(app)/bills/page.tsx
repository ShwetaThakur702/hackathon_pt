"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getBills, investigateBill } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { Bill } from "@/types";

const CATEGORY_LABEL: Record<string, string> = {
  ELECTRICITY: "Electricity", WATER: "Water", GAS: "Gas", MOBILE: "Mobile",
  DTH: "DTH", BROADBAND: "Broadband", INSURANCE: "Insurance", LOAN: "Loan / EMI", OTHER: "Other",
};

function BillCard({ bill, highlighted, onInvestigated }: { bill: Bill; highlighted: boolean; onInvestigated: (bill: Bill) => void }) {
  const [investigating, setInvestigating] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [error, setError] = useState(false);

  async function handleInvestigate() {
    setInvestigating(true);
    setError(false);
    try {
      const result = await investigateBill(bill.id);
      setCaseId(result.case_id);
      // Update this bill in place from the response — no full-list reload,
      // which would flip the page back into its loading skeleton and wipe
      // this "case created" confirmation right after showing it.
      onInvestigated(result.bill);
    } catch {
      setError(true);
    } finally {
      setInvestigating(false);
    }
  }

  return (
    <div className={`card p-5 ${highlighted ? "ring-2 ring-brand" : ""}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-ink-secondary">{CATEGORY_LABEL[bill.category] || bill.category}</div>
          <div className="text-sm font-medium text-ink mt-0.5">{bill.provider_name}</div>
        </div>
        <div className="text-right">
          <div className="amount">₹{bill.amount.toLocaleString("en-IN")}</div>
          <span className={`badge mt-1 ${bill.status === "PAID" ? "bg-success-light text-success" : "bg-warning-light text-warning"}`}>
            {bill.status === "PAID" ? "Paid" : "Pending"}
          </span>
        </div>
      </div>

      {bill.nishchint_insight.has_issue && (
        <div className="mt-4 rounded-lg bg-brand-light px-3 py-3">
          <p className="text-xs text-brand-dark">{bill.nishchint_insight.message}</p>
          {caseId ? (
            <p className="text-xs text-success mt-2 font-medium">✓ Case {caseId} created — I&apos;m monitoring this.</p>
          ) : (
            <button
              onClick={handleInvestigate}
              disabled={investigating}
              className="mt-2 text-xs font-medium text-white bg-brand-dark rounded-lg px-3 py-1.5 hover:bg-brand-navy disabled:opacity-50"
            >
              {investigating ? "Investigating…" : "Investigate"}
            </button>
          )}
          {error && <p className="text-xs text-danger mt-2">Couldn&apos;t start the investigation. Please try again.</p>}
        </div>
      )}
    </div>
  );
}

export default function BillsPage() {
  return (
    <Suspense fallback={<div className="page-shell h-32 rounded-xl bg-surface animate-pulse" />}>
      <BillsPageInner />
    </Suspense>
  );
}

function BillsPageInner() {
  const { customerId } = useCustomer();
  const searchParams = useSearchParams();
  const highlight = searchParams.get("highlight");
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    getBills(customerId).then(setBills).catch(console.error).finally(() => setLoading(false));
  }

  useEffect(load, [customerId]);

  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Bills</h1>
        <p className="text-sm text-ink-secondary mt-1">Nishchint checks that your payments and provider records agree.</p>
      </div>

      {loading ? (
        <div className="grid sm:grid-cols-2 gap-4">
          {[0, 1].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-surface animate-pulse" />
          ))}
        </div>
      ) : bills.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-secondary">No bills on file.</div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {bills.map((b) => (
            <BillCard
              key={b.id}
              bill={b}
              highlighted={b.id === highlight}
              onInvestigated={(updated) => setBills((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
