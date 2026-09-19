/** The "Nishchint" brand wordmark, split two-tone: first 5 letters
 * ("Nishc") in deep blue, last 4 ("hint") in light blue — used everywhere
 * the brand name itself is rendered, so the split stays consistent. */
export default function Wordmark({ className }: { className?: string }) {
  return (
    <span className={className}>
      <span className="text-brand-dark">Nishc</span>
      <span className="text-brand">hint</span>
    </span>
  );
}
