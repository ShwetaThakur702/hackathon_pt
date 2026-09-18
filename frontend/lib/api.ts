import type {
  AttentionResponse,
  AutoPayMandate,
  Bill,
  CaseDetail,
  CaseListItem,
  ChatResponse,
  FastagAccount,
  MemorySection,
  Refund,
  Transaction,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function sendChatMessage(customerId: string, message: string, caseId?: string | null) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId, message, case_id: caseId ?? null }),
  });
}

export function getCase(caseId: string) {
  return request<CaseDetail>(`/api/cases/${caseId}`);
}

/** Separate from getCase() on purpose: this hits Cognee Cloud and can take
 * several seconds. Fetch it after the case itself has rendered, not before. */
export function getCaseMemory(caseId: string) {
  return request<MemorySection>(`/api/cases/${caseId}/memory`);
}

export function listCases(params?: { status?: string; priority?: string; customerId?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.priority) qs.set("priority", params.priority);
  if (params?.customerId) qs.set("customer_id", params.customerId);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<CaseListItem[]>(`/api/cases${suffix}`);
}

export function overrideCase(caseId: string, action: "APPROVE" | "OVERRIDE", newStatus?: string, note?: string) {
  return request<CaseDetail>(`/api/cases/${caseId}/override`, {
    method: "POST",
    body: JSON.stringify({ action, new_status: newStatus, note, operator: "ops-dashboard" }),
  });
}

export type PreferredLanguage = "English" | "Hindi" | "Hinglish";

export function getCustomer(customerId: string) {
  return request<{ id: string; name: string; phone: string; preferred_language: PreferredLanguage }>(
    `/api/customers/${customerId}`
  );
}

/** Single source of truth for response language (spec: picked once on the
 * landing page, must stay uniform across every LLM-generated response). */
export function updateCustomerLanguage(customerId: string, language: PreferredLanguage) {
  return request<{ id: string; preferred_language: PreferredLanguage }>(`/api/customers/${customerId}/language`, {
    method: "PUT",
    body: JSON.stringify({ preferred_language: language }),
  });
}

export function getCustomerContext(customerId: string) {
  return request<{
    customer: { id: string; name: string; preferred_language: string } | null;
    recent_transactions: unknown[];
    open_cases: { id: string; status: string }[];
    recent_messages: unknown[];
  }>(`/api/customers/${customerId}/context`);
}

export function advanceTime(days: number, hours = 0) {
  return request<{ current_time: string; followups_executed: unknown[] }>("/api/simulate/advance-time", {
    method: "POST",
    body: JSON.stringify({ days, hours }),
  });
}

export function advanceToDeadline() {
  return request<{ current_time: string; followups_executed: unknown[] }>("/api/simulate/advance-to-deadline", {
    method: "POST",
  });
}

export function resetDemo() {
  return request<{ status: string; current_time: string }>("/api/simulate/reset", { method: "POST" });
}

export function getCurrentTime() {
  return request<{ current_time: string }>("/api/simulate/current-time");
}

export function getCustomerTransactions(customerId: string) {
  return request<Transaction[]>(`/api/customers/${customerId}/transactions`);
}

export function getTransaction(transactionId: string) {
  return request<Transaction>(`/api/transactions/${transactionId}`);
}

export function getAttention(customerId: string) {
  return request<AttentionResponse>(`/api/nishchint/attention?customer_id=${customerId}`);
}

export function getBills(customerId: string) {
  return request<Bill[]>(`/api/customers/${customerId}/bills`);
}

export function investigateBill(billId: string) {
  return request<{ case_id: string; created: boolean; bill: Bill }>(`/api/bills/${billId}/investigate`, { method: "POST" });
}

export function getFastagAccount(customerId: string) {
  return request<FastagAccount>(`/api/customers/${customerId}/fastag`);
}

export function investigateFastag(accountId: string) {
  return request<{ case_id: string; created: boolean; account: FastagAccount }>(`/api/fastag/${accountId}/investigate`, {
    method: "POST",
  });
}

export function getAutoPayMandates(customerId: string) {
  return request<AutoPayMandate[]>(`/api/customers/${customerId}/autopay`);
}

export function reviewMandate(mandateId: string) {
  return request<{ mandate: AutoPayMandate; insight: { has_issue: boolean; message: string | null } }>(
    `/api/autopay/${mandateId}/review`,
    { method: "POST" }
  );
}

export function cancelMandate(mandateId: string) {
  return request<AutoPayMandate>(`/api/autopay/${mandateId}/cancel`, { method: "POST" });
}

export function getRefunds(customerId: string) {
  return request<Refund[]>(`/api/customers/${customerId}/refunds`);
}

export function getNotifications(customerId: string) {
  return request<{ id: number; case_id: string | null; message: string; channel: string; created_at: string }[]>(
    `/api/customers/${customerId}/notifications`
  );
}

export function investigateRefund(refundId: string) {
  return request<{ case_id: string; created: boolean; refund: Refund }>(`/api/refunds/${refundId}/investigate`, {
    method: "POST",
  });
}

export interface TranscribeResult {
  text: string;
  language: string;
  language_probability: number;
}

export async function transcribeAudio(blob: Blob): Promise<TranscribeResult> {
  const form = new FormData();
  form.append("file", blob, "clip.webm");
  // Deliberately not using request(): FormData needs the browser to set its
  // own multipart Content-Type boundary, not our shared JSON default.
  const res = await fetch(`${API_BASE}/api/voice/transcribe`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<TranscribeResult>;
}
