"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { getCustomer, updateCustomerLanguage, type PreferredLanguage } from "@/lib/api";

/** Single signed-in customer for this prototype (spec: one customer, no
 * switcher, no "choose customer" screen — the product should feel like a
 * real customer using a real fintech app, not an operator browsing demo
 * customers). Matches the sole seeded customer in backend/app/database/
 * seed.py. */
export const CUSTOMER_ID = "CUST-001";
const FALLBACK_NAME = "Priya Sharma";

interface CustomerContextValue {
  customerId: string;
  customer: { id: string; name: string; preferred_language: PreferredLanguage };
  /** Persists to the backend (the single source of truth every
   * LLM-generated response reads from) and updates local state
   * immediately so the whole app reflects the choice without a reload. */
  setPreferredLanguage: (language: PreferredLanguage) => Promise<void>;
}

const CustomerContext = createContext<CustomerContextValue | null>(null);

export function CustomerProvider({ children }: { children: React.ReactNode }) {
  const [name, setName] = useState(FALLBACK_NAME);
  const [preferredLanguage, setPreferredLanguageState] = useState<PreferredLanguage>("English");

  // The backend is the single source of truth for the customer's name and
  // response language — fetched once on load rather than hardcoded twice.
  useEffect(() => {
    let cancelled = false;
    getCustomer(CUSTOMER_ID)
      .then((c) => {
        if (cancelled) return;
        setName(c.name);
        setPreferredLanguageState(c.preferred_language);
      })
      .catch(() => {
        // network hiccup on first load — fall back values stand, retried
        // implicitly the next time a page using this context mounts.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function setPreferredLanguage(language: PreferredLanguage) {
    const previous = preferredLanguage;
    setPreferredLanguageState(language); // optimistic — every consumer (chat, assistant) updates immediately
    try {
      await updateCustomerLanguage(CUSTOMER_ID, language);
    } catch {
      setPreferredLanguageState(previous); // roll back only on a real persistence failure
      throw new Error("Could not save language preference");
    }
  }

  const customer = { id: CUSTOMER_ID, name, preferred_language: preferredLanguage };

  return (
    <CustomerContext.Provider value={{ customerId: CUSTOMER_ID, customer, setPreferredLanguage }}>
      {children}
    </CustomerContext.Provider>
  );
}

export function useCustomer() {
  const ctx = useContext(CustomerContext);
  if (!ctx) throw new Error("useCustomer must be used within CustomerProvider");
  return ctx;
}
