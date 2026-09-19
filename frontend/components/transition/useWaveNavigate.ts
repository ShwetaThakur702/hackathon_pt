"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { WAVE_TRANSITION_KEY, type WaveTransitionPayload } from "./wave-transition";

/**
 * Drives the two-halves-stitched-together wave transition: `navigate`
 * kicks off the "cover" animation on the page you're leaving; once it's
 * fully covered, the caller's WaveExitOverlay fires `handleCovered`,
 * which performs the real navigation invisibly underneath the solid
 * wave. The destination page's WaveEntranceOverlay picks up the payload
 * from sessionStorage and plays the "reveal" half.
 */
export function useWaveNavigate() {
  const router = useRouter();
  const [active, setActive] = useState(false);
  const pendingHref = useRef<string | null>(null);

  const navigate = useCallback((href: string, title: string, subtitle: string) => {
    if (pendingHref.current) return;
    const payload: WaveTransitionPayload = { title, subtitle };
    try {
      sessionStorage.setItem(WAVE_TRANSITION_KEY, JSON.stringify(payload));
    } catch {}
    pendingHref.current = href;
    setActive(true);
  }, []);

  const handleCovered = useCallback(() => {
    if (pendingHref.current) {
      router.push(pendingHref.current);
    }
  }, [router]);

  return { active, navigate, handleCovered };
}
