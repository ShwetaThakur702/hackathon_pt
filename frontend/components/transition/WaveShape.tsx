"use client";

import { useEffect, useRef } from "react";
import { animate } from "framer-motion";
import {
  WAVE_BACK_POINTS,
  WAVE_DURATION,
  WAVE_EASE_IN,
  WAVE_EASE_OUT,
  WAVE_FRONT_POINTS,
  WAVE_ORIGIN_CX,
  WAVE_ORIGIN_CY,
  buildBlobPath,
} from "./wave-transition";

/**
 * Two layered wavy blobs, anchored bottom-left, that grow (or shrink)
 * toward that corner — `mode="in"` floods the screen, `mode="out"`
 * recedes back into the corner, `mode="hold"` keeps it fully covering
 * but lets it breathe with a slow pulse so it still reads as water
 * rather than a frozen slab.
 *
 * The growth is done by rebuilding the path's `d` attribute every frame
 * from raw points interpolated toward the anchor, rather than a CSS
 * `scale`/`transform-origin` — SVG's handling of percentage
 * transform-origins on nested elements is inconsistent across browsers
 * and was producing a static, wrongly-positioned colored patch instead
 * of a flowing wave. Recomputing the path is unambiguous everywhere.
 */
export default function WaveShape({
  mode,
  onComplete,
}: {
  mode: "in" | "out" | "hold";
  onComplete?: () => void;
}) {
  const frontRef = useRef<SVGPathElement>(null);
  const backRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    const setScale = (s: number) => {
      frontRef.current?.setAttribute("d", buildBlobPath(WAVE_FRONT_POINTS, WAVE_ORIGIN_CX, WAVE_ORIGIN_CY, s));
      backRef.current?.setAttribute("d", buildBlobPath(WAVE_BACK_POINTS, WAVE_ORIGIN_CX, WAVE_ORIGIN_CY, s));
    };

    let controls: { stop: () => void } | undefined;

    if (mode === "in") {
      setScale(0);
      controls = animate(0, 1, { duration: WAVE_DURATION, ease: WAVE_EASE_IN, onUpdate: setScale, onComplete });
    } else if (mode === "out") {
      setScale(1);
      controls = animate(1, 0, { duration: WAVE_DURATION * 0.9, ease: WAVE_EASE_OUT, onUpdate: setScale, onComplete });
    } else {
      setScale(1);
      controls = animate(1, [1.015, 1, 1.01, 1], {
        duration: 5,
        ease: "easeInOut",
        repeat: Infinity,
        onUpdate: setScale,
      });
    }

    return () => controls?.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
      <defs>
        <linearGradient id="nishchint-wave-gradient" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#002970" />
          <stop offset="60%" stopColor="#002970" />
          <stop offset="100%" stopColor="#00b9f1" />
        </linearGradient>
      </defs>
      <path ref={backRef} fill="#00b9f1" fillOpacity={0.35} />
      <path ref={frontRef} fill="url(#nishchint-wave-gradient)" />
    </svg>
  );
}
