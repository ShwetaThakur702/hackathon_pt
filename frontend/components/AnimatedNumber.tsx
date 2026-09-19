"use client";

import { useEffect } from "react";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";

/** Counts smoothly from its previous value to the new one instead of
 * snapping — used for the compensation figure, which is the single most
 * important number in the demo (it visibly grows as the clock advances:
 * ₹100 → ₹200 → ₹300). Backend still computes the value; this only
 * animates its presentation. */
export default function AnimatedNumber({
  value,
  prefix = "",
  className,
}: {
  value: number;
  prefix?: string;
  className?: string;
}) {
  const motionValue = useMotionValue(value);
  const rounded = useTransform(motionValue, (latest) => `${prefix}${Math.round(latest).toLocaleString("en-IN")}`);

  useEffect(() => {
    const controls = animate(motionValue, value, { duration: 0.7, ease: [0.16, 1, 0.3, 1] });
    return controls.stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <motion.span className={className}>{rounded}</motion.span>;
}
