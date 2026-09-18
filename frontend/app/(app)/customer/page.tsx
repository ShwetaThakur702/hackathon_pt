import ChatPanel from "@/components/ChatPanel";

export default function CustomerPage() {
  return (
    <div className="page-shell">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-ink">Nishchint</h1>
        <p className="text-sm text-ink-secondary">Your autonomous payment &amp; service resolution assistant.</p>
      </div>
      <ChatPanel />
    </div>
  );
}
