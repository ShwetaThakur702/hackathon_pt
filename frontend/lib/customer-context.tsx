"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { getCustomer, updateCustomerLanguage, type PreferredLanguage } from "@/lib/api";

export const DEMO_CUSTOMERS = [
  { id: "CUST001", name: "Priya Sharma" },
  { id: "CUST002", name: "Arjun Mehta" },
  { id: "CUST003", name: "Rahul Verma" },
] as const;

interface CustomerContextValue {
  customerId: string;
  setCustomerId: (id: string) => void;
  customer: { id: string; name: string; preferred_language: PreferredLanguage };
  /** Persists to the backend (the single source of truth every
   * LLM-generated response reads from) and updates local state
   * immediately so the whole app reflects the choice without a reload. */
  setPreferredLanguage: (language: PreferredLanguage) => Promise<void>;
}

const CustomerContext = createContext<CustomerContextValue | null>(null);

const STORAGE_KEY = "nishchint.demo_customer_id";

export function CustomerProvider({ children }: { children: React.ReactNode }) {
  const [customerId, setCustomerIdState] = useState<string>(DEMO_CUSTOMERS[0].id);
  const [preferredLanguage, setPreferredLanguageState] = useState<PreferredLanguage>("English");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored && DEMO_CUSTOMERS.some((c) => c.id === stored)) {
        setCustomerIdState(stored);
      }
    } catch {
      // localStorage unavailable (private window etc.) — fine, default customer stands.
    }
  }, []);

  // The backend is the single source of truth for response language, so
  // whenever the active customer changes we re-fetch it rather than
  // trusting any stale local guess.
  useEffect(() => {
    let cancelled = false;
    getCustomer(customerId)
      .then((c) => {
        if (!cancelled) setPreferredLanguageState(c.preferred_language);
      })
      .catch(() => {
        // network hiccup — keep whatever language was already set rather
        // than silently resetting the customer's choice.
      });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  function setCustomerId(id: string) {
    setCustomerIdState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // per-viewer convenience only; safe to ignore.
    }
  }

  async function setPreferredLanguage(language: PreferredLanguage) {
    const previous = preferredLanguage;
    setPreferredLanguageState(language); // optimistic — every consumer (chat, assistant) updates immediately
    try {
      await updateCustomerLanguage(customerId, language);
    } catch {
      setPreferredLanguageState(previous); // roll back only on a real persistence failure
      throw new Error("Could not save language preference");
    }
  }

  const demoCustomer = DEMO_CUSTOMERS.find((c) => c.id === customerId) ?? DEMO_CUSTOMERS[0];
  const customer = { ...demoCustomer, preferred_language: preferredLanguage };

  return (
    <CustomerContext.Provider value={{ customerId, setCustomerId, customer, setPreferredLanguage }}>
      {children}
    </CustomerContext.Provider>
  );
}

export function useCustomer() {
  const ctx = useContext(CustomerContext);
  if (!ctx) throw new Error("useCustomer must be used within CustomerProvider");
  return ctx;
}
