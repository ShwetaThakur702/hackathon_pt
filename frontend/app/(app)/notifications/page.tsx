"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getNotifications } from "@/lib/api";
import { useCustomer } from "@/lib/customer-context";
import { BellIcon } from "@/components/shell/icons";

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
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 rounded-xl skeleton" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-8 flex flex-col items-center text-center gap-2 animate-pop-in">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-light text-brand-dark">
            <BellIcon className="w-5 h-5" />
          </span>
          <p className="text-sm font-medium text-ink">No notifications yet</p>
          <p className="text-xs text-ink-secondary max-w-xs">
            When Nishchint raises a dispute, resolves a case, or spots something worth telling you about, it shows up here.
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-border overflow-hidden stagger-list">
          {items.map((n) => (
            <div key={n.id} className="stagger-item flex items-start gap-3 px-5 py-4 transition-colors duration-150 hover:bg-surface">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-light text-brand-dark mt-0.5">
                <BellIcon className="w-4 h-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink">{n.message}</p>
                <p className="text-xs text-ink-secondary mt-1">
                  {new Date(n.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                  {n.case_id && (
                    <>
                      {" · "}
                      <Link href={`/cases/${n.case_id}`} className="text-brand-dark hover:underline transition-all">
                        {n.case_id}
                      </Link>
                    </>
                  )}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
