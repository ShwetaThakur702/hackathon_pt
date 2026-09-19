"use client";

import { useCustomer } from "@/lib/customer-context";
import LanguageSelector from "@/components/home/LanguageSelector";
import { UserIcon } from "@/components/shell/icons";

export default function ProfilePage() {
  const { customer } = useCustomer();

  return (
    <div className="page-shell space-y-5 max-w-xl">
      <div className="card p-6 flex items-center gap-4">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-light text-brand-dark">
          <UserIcon className="w-7 h-7" />
        </span>
        <div>
          <div className="text-lg font-semibold text-ink">{customer.name}</div>
          <div className="text-sm text-ink-secondary">Preferred language: {customer.preferred_language}</div>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-ink mb-3">Reply language</h2>
        <p className="text-xs text-ink-secondary mb-3">
          Every response from Nishchint — chat, the floating assistant, and follow-up notifications — uses this
          setting, no matter what language your own messages are in.
        </p>
        <LanguageSelector variant="compact" />
      </div>
    </div>
  );
}
