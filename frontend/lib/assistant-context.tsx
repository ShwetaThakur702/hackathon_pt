"use client";

import { createContext, useContext, useState } from "react";

interface PageContext {
  /** Short, human-readable description of what's currently on screen,
   * built by the page itself from real fetched data — e.g.
   * "this ₹2,400 Apollo Medicals payment". Never fabricated. */
  summary: string;
  /** A ready-to-send message the launcher can offer as a one-tap action. */
  suggestedMessage: string;
}

interface AssistantContextValue {
  pageContext: PageContext | null;
  setPageContext: (ctx: PageContext | null) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: React.ReactNode }) {
  const [pageContext, setPageContext] = useState<PageContext | null>(null);
  const [open, setOpen] = useState(false);
  return (
    <AssistantContext.Provider value={{ pageContext, setPageContext, open, setOpen }}>{children}</AssistantContext.Provider>
  );
}

export function useAssistant() {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used within AssistantProvider");
  return ctx;
}
