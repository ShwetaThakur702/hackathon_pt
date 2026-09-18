import type { Transaction } from "@/types";

export type DisplayStatus = "Completed" | "Needs attention" | "Resolved" | "Pending" | "Failed";

/** Derives a customer-friendly status label from the transaction's real
 * verified fields — never a separate, possibly-stale stored label. */
export function displayStatus(txn: Transaction): DisplayStatus {
  if (txn.status === "SUCCESS") return "Completed";
  if (txn.status === "FAILED") {
    if (txn.refund_status === "RECEIVED") return "Resolved";
    return "Needs attention";
  }
  if (txn.status === "PENDING") return "Pending";
  return "Failed";
}

export const STATUS_STYLES: Record<DisplayStatus, string> = {
  Completed: "bg-success-light text-success",
  "Needs attention": "bg-danger-light text-danger",
  Resolved: "bg-success-light text-success",
  Pending: "bg-warning-light text-warning",
  Failed: "bg-danger-light text-danger",
};
