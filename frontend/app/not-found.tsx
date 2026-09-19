import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface px-4 text-center">
      <Link href="/" className="flex items-center gap-2 mb-8">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-dark text-white font-bold">N</span>
        <span className="font-bold text-xl text-brand-dark tracking-tight">Nishchint</span>
      </Link>

      <div className="card p-10 max-w-md">
        <div className="text-6xl font-bold text-brand-light mb-2">404</div>
        <h1 className="text-lg font-semibold text-ink mb-2">This page went missing</h1>
        <p className="text-sm text-ink-secondary mb-6">
          Unlike your payments, Nishchint isn&apos;t tracking this one down — the page you&apos;re looking for
          doesn&apos;t exist or may have moved.
        </p>
        <Link href="/" className="btn-primary btn-md">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
