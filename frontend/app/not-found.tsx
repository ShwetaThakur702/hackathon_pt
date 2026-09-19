import Link from "next/link";
import Wordmark from "@/components/shell/Wordmark";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface px-4 text-center">
      <Link href="/nishchint" className="flex items-center gap-2 mb-8">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-dark text-white font-bold">N</span>
        <Wordmark className="font-bold text-xl tracking-tight" />
      </Link>

      <div className="card p-10 max-w-md">
        <div className="text-6xl font-bold text-brand-light mb-2">404</div>
        <h1 className="text-lg font-semibold text-ink mb-2">This page went missing</h1>
        <p className="text-sm text-ink-secondary mb-6">
          Unlike your payments, Nishchint isn&apos;t tracking this one down — the page you&apos;re looking for
          doesn&apos;t exist or may have moved.
        </p>
        <Link href="/nishchint" className="btn-primary btn-md">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
