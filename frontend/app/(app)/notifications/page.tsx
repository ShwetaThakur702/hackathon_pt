"use client";

import { useEffect, useState } from "react";
import { getNotifications } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";

interface NotificationItem {
  id: number;
  case_id: string | null;
  message: string;
  channel: string;
  created_at: string;
}

export default function NotificationsPage() {
  const { customerId } = useCustomer();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getNotifications(customerId).then(setItems).catch(console.error).finally(() => setLoading(false));
  }, [customerId]);

  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Notifications</h1>
        <p className="text-sm text-ink-secondary mt-1">Updates Nishchint has sent you, generated from real case events.</p>
      </div>

      {loading ? (
        <div className="h-32 rounded-xl bg-surface animate-pulse" />
      ) : items.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-secondary">No notifications yet.</div>
      ) : (
        <div className="card divide-y divide-border overflow-hidden">
          {items.map((n) => (
            <div key={n.id} className="px-5 py-4">
              <p className="text-sm text-ink">{n.message}</p>
              <p className="text-xs text-ink-secondary mt-1">
                {new Date(n.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                {n.case_id && ` · ${n.case_id}`}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
