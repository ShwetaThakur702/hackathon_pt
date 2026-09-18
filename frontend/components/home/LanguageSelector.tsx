"use client";

import { useState } from "react";
import { useCustomer } from "@/lib/customer-context";
import type { PreferredLanguage } from "@/lib/api";

const OPTIONS: { value: PreferredLanguage; label: string; hint: string }[] = [
  { value: "English", label: "English", hint: "Replies in English" },
  { value: "Hindi", label: "हिंदी", hint: "हिंदी में जवाब" },
  { value: "Hinglish", label: "Hinglish", hint: "Roman-script mix" },
];

const INDEX: Record<PreferredLanguage, number> = { English: 0, Hindi: 1, Hinglish: 2 };

/** Picked once here, drives every LLM-generated response — chat, the
 * floating assistant, follow-up notifications — uniformly, regardless of
 * what language the customer types in (Customer.preferred_language is the
 * single source of truth on the backend).
 *
 * `variant="compact"` renders just the pill (no card/heading) for the top
 * nav bar, where it lives so it's visible on every page, not just Home. */
export default function LanguageSelector({ variant = "card" }: { variant?: "card" | "compact" }) {
  const { customer, setPreferredLanguage } = useCustomer();
  const [saving, setSaving] = useState<PreferredLanguage | null>(null);
  const [error, setError] = useState(false);

  const active = customer.preferred_language;

  async function handleSelect(value: PreferredLanguage) {
    if (value === active || saving) return;
    setSaving(value);
    setError(false);
    try {
      await setPreferredLanguage(value);
    } catch {
      setError(true);
    } finally {
      setSaving(null);
    }
  }

  const pill = (
    <div
      role="radiogroup"
      aria-label="Preferred reply language"
      className={`relative grid grid-cols-3 rounded-full bg-surface border border-border p-1 ${
        variant === "compact" ? "w-full" : ""
      }`}
    >
      <div
        className="absolute inset-y-1 w-1/3 rounded-full bg-brand-dark shadow-sm transition-transform duration-200 ease-out"
        style={{ transform: `translateX(${INDEX[active] * 100}%)` }}
        aria-hidden
      />
      {OPTIONS.map((option) => {
        const isActive = option.value === active;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            disabled={saving !== null}
            onClick={() => handleSelect(option.value)}
            title={option.hint}
            className={`tap-target relative z-10 rounded-full text-center font-medium transition-colors ${
              variant === "compact" ? "py-1 text-xs" : "py-2 text-sm"
            } ${isActive ? "text-white" : "text-ink-secondary hover:text-ink"}`}
          >
            {saving === option.value ? "…" : option.label}
          </button>
        );
      })}
    </div>
  );

  if (variant === "compact") {
    return (
      <div className="flex flex-col items-start w-full">
        {pill}
        {error && <p className="text-[10px] text-red-600 mt-1">Couldn&apos;t save. Try again.</p>}
      </div>
    );
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink">Reply language</h2>
        <span className="text-xs text-ink-secondary">{OPTIONS.find((o) => o.value === active)?.hint}</span>
      </div>
      {pill}
      {error && <p className="text-xs text-red-600 mt-2">Couldn&apos;t save your language preference. Please try again.</p>}
    </div>
  );
}
