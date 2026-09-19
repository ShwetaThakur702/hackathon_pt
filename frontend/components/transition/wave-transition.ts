export const WAVE_TRANSITION_KEY = "nishchint:wave-transition";

export interface WaveTransitionPayload {
  title: string;
  subtitle: string;
}

/** Asymmetric, water-like easing rather than a generic easeInOut: the
 * cover surges in fast and settles gently (like a wave rushing up a
 * shore), the reveal starts slow and pulls away with gathering speed
 * (like undertow). */
export const WAVE_EASE_IN = [0.16, 1, 0.3, 1] as const;
export const WAVE_EASE_OUT = [0.7, 0, 0.84, 0] as const;
export const WAVE_EASE = "easeInOut";
export const WAVE_DURATION = 1.05;

/**
 * The wave grows out of / recedes back into a fixed point near the
 * bottom-left corner ("waves that start from the bottom-left and go
 * up"), rather than sweeping in as a flat full-width band. It's a
 * static, hand-shaped "wavy blob" silhouette — not a perfect circle
 * (reads as a plain iris wipe, not a wave) and not per-frame path
 * morphing between unrelated shapes (reads as jumpy).
 *
 * The growth itself is done by interpolating every point of the blob
 * toward the anchor (not via a CSS `scale`/`transform-origin`): SVG's
 * handling of percentage transform-origins on nested <g> elements is
 * inconsistent across browsers (some resolve it against the element's
 * own painted bounding box rather than the viewBox), which showed up as
 * a static, wrongly-positioned colored patch instead of a flowing wave.
 * Interpolating the raw coordinates is unambiguous everywhere.
 */
export const WAVE_ORIGIN_CX = 6;
export const WAVE_ORIGIN_CY = 96;

// Both point sets trace a closed, five-lobed blob centered on the origin
// above; their minimum radius (~163 / ~178) comfortably clears the
// farthest viewport corner (~134 units away) at full size, so there's
// never a gap once fully grown.
export const WAVE_FRONT_POINTS: [number, number][] = [
  [185.77, 96], [180.11, 159.37], [133.67, 203.13], [89.81, 241.16], [38.28, 279.08],
  [-25.01, 271.88], [-75.42, 237.03], [-128.54, 208.89], [-169.67, 159.94], [-164.23, 96],
  [-148.78, 39.66], [-134.45, -21.85], [-85.19, -61.95], [-22.49, -65.6], [35.76, -72.8],
  [99.58, -66.08], [139.58, -16.09], [159.23, 40.23],
];
export const WAVE_BACK_POINTS: [number, number][] = [
  [208.34, 96], [182.19, 160.13], [142.76, 210.75], [104.24, 266.16], [40.6, 292.2],
  [-25.31, 273.57], [-86.07, 255.47], [-148.53, 225.67], [-174.22, 161.6], [-171.66, 96],
  [-174.89, 30.16], [-148.34, -33.51], [-85.76, -62.93], [-25.39, -82.03], [40.68, -100.65],
  [103.93, -73.62], [142.57, -18.59], [182.86, 31.63],
];

/**
 * Builds a smooth closed path (Catmull-Rom through the given points,
 * converted to cubic beziers) after shrinking every point toward
 * (originX, originY) by `scale` (0 = collapsed to a single point at the
 * origin, 1 = full size). This is what actually animates: callers tween
 * `scale` from 0 to 1 (or back) and rebuild the `d` string each frame.
 */
export function buildBlobPath(
  points: readonly [number, number][],
  originX: number,
  originY: number,
  scale: number
): string {
  const pts = points.map(([x, y]) => [originX + (x - originX) * scale, originY + (y - originY) * scale] as const);
  const n = pts.length;
  const seg: string[] = [`M${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`];
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n];
    const p1 = pts[i];
    const p2 = pts[(i + 1) % n];
    const p3 = pts[(i + 2) % n];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    seg.push(`C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`);
  }
  seg.push("Z");
  return seg.join(" ");
}
