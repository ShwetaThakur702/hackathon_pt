"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

/**
 * Renders children directly under <body>. A `position: fixed` element is
 * only fixed to the viewport if none of its ancestors has a transform,
 * filter or perspective — and page containers here animate in with a
 * translateY, which was trapping the full-screen wave inside the page's
 * content box. Body has none of that, so portaling there makes
 * `fixed inset-0` mean the whole viewport, always.
 */
export default function OverlayPortal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return createPortal(children, document.body);
}
