export interface ContextUsed {
  previous_case_found: boolean;
  related_transaction_found: boolean;
  semantic_memory_hits: number;
}

export interface ChatResponse {
  case_id: string | null;
  message: string;
  intent: string | null;
  status: string | null;
  actions: string[];
  context_used?: ContextUsed | null;
}

export interface Transaction {
  id: string;
  /** Customer-facing 12-digit UPI reference number, e.g. "809489842596" —
   * always display this (never the internal `id`) on any customer-facing
   * screen. */
  upi_ref_no: string;
  customer_id: string;
  amount: number;
  currency: string;
  type: "PERSON" | "MERCHANT";
  merchant_name: string | null;
  status: string;
  debited: boolean;
  merchant_credited: boolean | null;
  refund_status: string;
  transaction_date: string;
}

export interface PolicyResult {
  policy_id: string;
  rule_id: string | null;
  applicable: boolean;
  deadline: string | null;
  days_until_deadline: number | null;
  days_overdue: number | null;
  compensation_per_day: number | null;
  compensation: number | null;
  is_breached: boolean;
  recommended_action: string;
}

export interface TimelineEvent {
  event_type: string;
  actor: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface CaseMessage {
  case_id: string;
  sender: "CUSTOMER" | "ASSISTANT" | "HUMAN";
  message: string;
  timestamp: string;
}

export interface MemoryItem {
  text: string;
  source: string;
}

export interface MemorySection {
  cognee_configured: boolean;
  previous_interactions: MemoryItem[];
  related_incidents: MemoryItem[];
}

export interface CaseDetail {
  id: string;
  status: string;
  priority: string;
  intent: string | null;
  escalation_reason: string | null;
  deadline: string | null;
  created_at: string;
  customer: { id: string; name: string; preferred_language: string } | null;
  transaction: Transaction | null;
  policy_result: PolicyResult | null;
  messages: CaseMessage[];
  timeline: TimelineEvent[];
  followup: { id: string; status: string; scheduled_for: string; attempt_count: number } | null;
  dispute: { id: string; status: string; compensation_amount: number } | null;
  memory: MemorySection;
}

export interface CaseListItem {
  id: string;
  customer_id: string;
  transaction_id: string | null;
  intent: string | null;
  status: string;
  priority: string;
  escalation_reason: string | null;
  created_at: string;
  closed_at: string | null;
}

export interface NishchintInsight {
  has_issue: boolean;
  message: string | null;
}

export interface Bill {
  id: string;
  customer_id: string;
  category: string;
  provider_name: string;
  amount: number;
  status: string;
  provider_ack_status: string;
  due_date: string;
  paid_date: string | null;
  nishchint_insight: NishchintInsight;
}

export interface FastagAccount {
  id: string;
  customer_id: string;
  balance: number;
  last_recharge_amount: number | null;
  last_recharge_status: string;
  nishchint_insight: NishchintInsight;
}

export interface AutoPayMandate {
  id: string;
  customer_id: string;
  biller_name: string;
  amount: number;
  frequency: string;
  next_charge_date: string;
  status: string;
  nishchint_insight: NishchintInsight;
}

export interface Refund {
  id: string;
  customer_id: string;
  merchant_name: string;
  amount: number;
  original_transaction_id: string | null;
  merchant_status: string;
  customer_received: boolean;
  nishchint_insight: NishchintInsight;
}

export interface AttentionItem {
  type: "CASE" | "BILL" | "FASTAG" | "AUTOPAY" | "REFUND";
  id: string;
  title: string;
  subtitle: string | null;
  amount: number | null;
  cta_label: string;
  cta_href: string;
}

export interface AttentionResponse {
  has_attention: boolean;
  items: AttentionItem[];
}
