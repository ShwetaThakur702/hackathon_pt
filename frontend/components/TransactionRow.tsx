import Link from "next/link";
import type { Transaction } from "@/types";
import { displayStatus, STATUS_STYLES } from "@/lib/transaction-status";

export default function TransactionRow({ txn }: { txn: Transaction }) {
  const status = displayStatus(txn);
  return (
    <Link href={`/transactions/${txn.id}`} className="flex items-center justify-between px-5 py-3.5 hover:bg-surface">
      <div className="min-w-0">
        <div className="text-sm font-medium text-ink truncate">{txn.merchant_name || "P2P transfer"}</div>
        <div className="text-xs text-ink-secondary">
          {new Date(txn.transaction_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} · {txn.type === "MERCHANT" ? "UPI" : "P2P"}
        </div>
      </div>
      <div className="text-right shrink-0 ml-3">
        <div className="amount">₹{txn.amount.toLocaleString("en-IN")}</div>
        <span className={`badge mt-1 ${STATUS_STYLES[status]}`}>{status}</span>
      </div>
    </Link>
  );
}
