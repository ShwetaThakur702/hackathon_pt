"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import OverlayPortal from "./OverlayPortal";
import { WAVE_DURATION, WAVE_EASE, WAVE_TRANSITION_KEY, type WaveTransitionPayload } from "./wave-transition";
import WaveShape from "./WaveShape";

const HOLD_MS = 1000;
const RECEDE_MS = WAVE_DURATION * 900;

function readPendingTransition(): WaveTransitionPayload | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(WAVE_TRANSITION_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(WAVE_TRANSITION_KEY);
    return JSON.parse(raw) as WaveTransitionPayload;
  } catch {
    return null;
  }
}

/**
 * The half of the branded transition that plays on the page you're
 * ARRIVING at. Mounts already fully covered — the same wave, grown out
 * of the bottom-left corner and held there — matching exactly where
 * WaveExitOverlay left off on the page you came from, so there's never a
 * flash of unstyled content. Holds the welcome text for a beat, then the
 * wave recedes back into that corner to reveal the real page. A no-op if
 * the page wasn't reached via useWaveNavigate (e.g. a raw URL visit or
 * refresh) — nothing in sessionStorage, nothing renders.
 */
export default function WaveEntranceOverlay() {
  const [payload] = useState<WaveTransitionPayload | null>(readPendingTransition);
  const [phase, setPhase] = useState<"hold" | "receding" | "done">("hold");

  useEffect(() => {
    if (!payload) return;
    const t1 = setTimeout(() => setPhase("receding"), HOLD_MS);
    const t2 = setTimeout(() => setPhase("done"), HOLD_MS + RECEDE_MS);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [payload]);

  if (!payload || phase === "done") return null;
  const receding = phase === "receding";

  return (
    <OverlayPortal>
      <div className="fixed inset-0 z-[200] pointer-events-none overflow-hidden" aria-hidden>
        <motion.div
          animate={{ opacity: receding ? 0 : 1 }}
          transition={{ duration: RECEDE_MS / 1000, ease: WAVE_EASE }}
          className="absolute inset-0 backdrop-blur-md bg-white/10"
        />
        <WaveShape mode={receding ? "out" : "hold"} />
        <div className="absolute inset-0 flex items-center justify-center">
          <AnimatePresence>
            {!receding && (
              <motion.div
                initial={{ opacity: 0, y: 14, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.4, ease: WAVE_EASE }}
                className="text-center text-white px-6 max-w-sm"
              >
                <h1 className="text-2xl sm:text-3xl font-bold mb-2">{payload.title}</h1>
                <p className="text-sm text-white/80">{payload.subtitle}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </OverlayPortal>
  );
}
