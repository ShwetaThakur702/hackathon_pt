"use client";

import { useCustomer, DEMO_CUSTOMERS } from "@/lib/customer-context";
import { UserIcon } from "@/components/shell/icons";

export default function ProfilePage() {
  const { customerId, customer, setCustomerId } = useCustomer();

  return (
    <div className="page-shell space-y-5 max-w-xl">
      <div className="card p-6 flex items-center gap-4">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-light text-brand-dark">
          <UserIcon className="w-7 h-7" />
        </span>
        <div>
          <div className="text-lg font-semibold text-ink">{customer.name}</div>
          <div className="text-sm text-ink-secondary">{customerId} · Preferred language: {customer.preferred_language}</div>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-ink mb-3">Demo customer</h2>
        <p className="text-xs text-ink-secondary mb-3">
          This prototype has no real authentication — switch between the three seeded demo customers here or from the
          profile icon in the navigation.
        </p>
        <div className="space-y-2">
          {DEMO_CUSTOMERS.map((c) => (
            <button
              key={c.id}
              onClick={() => setCustomerId(c.id)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm ${
                c.id === customerId ? "bg-brand-light text-brand-dark font-medium" : "hover:bg-surface text-ink"
              }`}
            >
              {c.name} <span className="text-xs text-ink-secondary">({c.id})</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
