"use client";

import { AnimatePresence, motion } from "framer-motion";
import OverlayPortal from "./OverlayPortal";
import { WAVE_DURATION } from "./wave-transition";
import WaveShape from "./WaveShape";

/**
 * The half of the branded transition that plays on the page you're
 * LEAVING: a soft blur settles in, then the wave grows out of the
 * bottom-left corner and floods the screen. `onCovered` fires once it's
 * fully opaque — that's when the caller (useWaveNavigate) actually
 * performs the navigation, so it happens invisibly underneath.
 */
export default function WaveExitOverlay({ active, onCovered }: { active: boolean; onCovered: () => void }) {
  return (
    <OverlayPortal>
      <AnimatePresence>
        {active && (
          <div className="fixed inset-0 z-[200] pointer-events-none overflow-hidden" aria-hidden>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: WAVE_DURATION * 0.4 }}
              className="absolute inset-0 backdrop-blur-md bg-white/20"
            />
            <WaveShape mode="in" onComplete={onCovered} />
          </div>
        )}
      </AnimatePresence>
    </OverlayPortal>
  );
}
