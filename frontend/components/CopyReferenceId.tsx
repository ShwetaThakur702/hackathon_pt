"use client";

import { useState } from "react";

/** UPI Reference ID display + copy — the customer never needs to know the
 * internal database id; this numeric reference is the only thing they
 * should ever have to read out or paste elsewhere. */
export default function CopyReferenceId({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable (e.g. insecure context) — no-op.
    }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-xs">{value}</span>
      <button
        type="button"
        onClick={handleCopy}
        className="text-[11px] font-medium text-brand-dark hover:underline"
        aria-label="Copy UPI Reference ID"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}
