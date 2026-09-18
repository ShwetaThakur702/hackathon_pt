"use client";

import { useEffect, useState } from "react";
import { getFastagAccount, investigateFastag } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import type { FastagAccount } from "@/types";
import { FastagIcon } from "@/components/shell/icons";

export default function FastagPage() {
  const { customerId } = useCustomer();
  const [account, setAccount] = useState<FastagAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [error, setError] = useState(false);

  function load() {
    setLoading(true);
    getFastagAccount(customerId)
      .then(setAccount)
      .catch(() => setAccount(null))
      .finally(() => setLoading(false));
  }

  useEffect(load, [customerId]);

  async function handleInvestigate() {
    if (!account) return;
    setInvestigating(true);
    setError(false);
    try {
      const result = await investigateFastag(account.id);
      setCaseId(result.case_id);
      // Update from the response directly — calling load() here would flip
      // `loading` back to true and unmount this card (wiping caseId) right
      // after we just set it.
      setAccount(result.account);
    } catch {
      setError(true);
    } finally {
      setInvestigating(false);
    }
  }

  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">FASTag</h1>
        <p className="text-sm text-ink-secondary mt-1">Toll balance and recharge status.</p>
      </div>

      {loading ? (
        <div className="h-40 rounded-xl bg-surface animate-pulse" />
      ) : !account ? (
        <div className="card p-8 text-center text-sm text-ink-secondary">No FASTag account linked.</div>
      ) : (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-light text-brand-dark">
              <FastagIcon className="w-5 h-5" />
            </span>
            <div>
              <div className="text-xs text-ink-secondary">FASTag balance</div>
              <div className="text-2xl font-bold text-ink">₹{account.balance.toLocaleString("en-IN")}</div>
            </div>
          </div>

          {account.last_recharge_amount && (
            <div className="text-sm text-ink-secondary border-t border-border pt-4">
              Recent activity: +₹{account.last_recharge_amount.toLocaleString("en-IN")} recharge
            </div>
          )}

          {account.nishchint_insight.has_issue && (
            <div className="mt-4 rounded-lg bg-brand-light px-4 py-3">
              <p className="text-sm text-brand-dark">{account.nishchint_insight.message}</p>
              {caseId ? (
                <p className="text-xs text-success mt-2 font-medium">✓ Case {caseId} created — I&apos;m monitoring this.</p>
              ) : (
                <button
                  onClick={handleInvestigate}
                  disabled={investigating}
                  className="mt-2 text-xs font-medium text-white bg-brand-dark rounded-lg px-3 py-1.5 hover:bg-brand-navy disabled:opacity-50"
                >
                  {investigating ? "Resolving…" : "Resolve"}
                </button>
              )}
              {error && <p className="text-xs text-danger mt-2">Couldn&apos;t start the investigation. Please try again.</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
