export interface Case {
  id: number;
  customer_id: number;
  payment_id: number | null;
  amount_at_risk: number;
  risk_score: number;
  event_type: string;
  failure_reason: string | null;
  recovery_probability: number | null;
  recommended_action: string | null;
  approved_action: string | null;
  policy_decision: string | null;
  stage?: string;
  action_status: string;
  recovery_status: string;
  amount_recovered: number;
  retry_count?: number;
  max_attempts?: number;
  whatsapp_status?: string;
  customer_response?: string;
  payment_link_id?: string | null;
  payment_link_url?: string | null;
  verified_payment_id?: string | null;
  created_at: string | null;
}

export interface CaseDetail extends Case {
  diagnosis: string | null;
  diagnosis_confidence: number | null;
  contributing_factors: string[];
  strategy_rationale: string | null;
  policy_reason: string | null;
  model_version: string | null;
  resolved_at: string | null;
}

export interface PipelineRun {
  case_id: number;
  event_type: string;
  amount: number;
  diagnosis: string | null;
  strategy: string | null;
  policy: string | null;
  status: string;
  probability: number | null;
  created_at: string | null;
}

export interface Dashboard {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  active_cases: number;
  failed_payments: number;
  checkout_abandonments: number;
  subscription_failures: number;
  predicted_recoverable: number;
  high_risk_customers_count: number;
  recovery_trend: { date: string; cases: number; recovered: number }[];
  recent_pipeline_runs: PipelineRun[];
  high_risk_cases: Case[];
}

export interface ForecastPeriod {
  period: string;
  revenue_at_risk: number;
  predicted_recoverable: number;
  predicted_recovery_rate: number;
}

export interface Analytics {
  total_cases: number;
  recovered_cases: number;
  failed_cases: number;
  open_cases: number;
  stopped_cases: number;
  recovery_rate: number;
  total_revenue_recovered: number;
  revenue_at_risk: number;
  failed_recovery_amount: number;
  agent_success_rate: number;
  recovery_by_failure_type: Record<string, { at_risk: number; recovered: number; count: number }>;
  recovery_by_strategy: Record<string, { count: number; recovered: number; recovery_rate: number }>;
  recovery_by_segment: Record<string, { cases: number; at_risk: number; recovered: number }>;
  forecast_30d: Record<string, ForecastPeriod>;
}

export interface MLMetrics {
  model_type: string;
  version: string;
  dataset_size: number;
  threshold: number;
  train: any;
  validation: any;
  test: any;
}

export interface AgentRun {
  id: number;
  agent_name: string;
  case_id: number | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface AgentStats {
  name: string;
  title: string;
  status: string;
  current_task: string;
  last_action: string;
  execution_count: number;
  success_rate: number;
  avg_duration_ms: number;
  current_case_id: number | null;
  last_run_at: string | null;
}

export interface AgentDecision {
  id: number;
  agent_run_id: number;
  agent_name: string;
  decision_type: string;
  confidence: number | null;
  input_data: any;
  output_data: any;
  created_at: string | null;
}

export interface MCPTool {
  name: string;
  description: string;
  permission: string;
  requires_auth: boolean;
  sandbox_safe: boolean;
  execution_count: number;
  avg_duration_ms: number;
  success_rate: number;
}

export interface MCPServer {
  server_name: string;
  protocol: string;
  status: string;
  description: string;
  tools: MCPTool[];
}

export interface MCPCall {
  id: number;
  case_id: number | null;
  tool_name: string;
  arguments: any;
  result: any;
  status: string;
  duration_ms: number | null;
  error: string | null;
  caller: string | null;
  created_at: string | null;
}

export interface Policy {
  automatic_threshold: number;
  approval_threshold: number;
  retry_limit: number;
  max_recovery_attempts: number;
  high_value_threshold: number;
  allow_auto_retry: boolean;
  allow_auto_payment_link: boolean;
  allow_auto_notification: boolean;
  notification_channels: string[];
}

export interface TimelineEvent {
  ts: string | null;
  agent: string;
  action: string;
  explanation: string;
  status: string;
  detail: any;
}

export interface DemoResult {
  case_id: number;
  event_type: string;
  amount_at_risk: number;
  recovery_probability: number | null;
  recommended_action: string | null;
  policy_decision: string | null;
  approved_action: string | null;
  stage?: string;
  whatsapp_status?: string;
  customer_response?: string;
  payment_link_url?: string | null;
  verified_payment_id?: string | null;
  recovery_status: string;
  amount_recovered: number;
}

export interface CommandResponse {
  query: string;
  intent: string;
  answer: string;
  data: any;
  suggested_actions?: { label: string; action: string }[];
}

export interface AuditLog {
  id: number;
  actor: string;
  actor_id: number | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: string;
  ip_address: string | null;
  status: string;
  created_at: string | null;
}

export interface BillReminderLog {
  id: number;
  bill_id: number;
  stage?: string;
  channel: string;
  recipient_phone: string;
  message: string;
  status: string;
  delivery_status?: string;
  customer_response?: string;
  payment_status_after?: string;
  scheduled_for?: string | null;
  sent_at: string | null;
}

export interface BillReminderSettings {
  id: number;
  merchant_id: number;
  reminders_enabled: boolean;
  frequency: "smart" | "conservative" | "aggressive" | string;
  max_reminders: number;
  preferred_channel: "whatsapp" | "email" | "sms" | "multi" | string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  risk_multiplier_enabled: boolean;
  updated_at: string | null;
}

export interface ScheduledReminderAction {
  bill_id: number;
  bill_name: string;
  customer_name: string;
  customer_phone: string;
  amount: number;
  due_date: string;
  stage: string;
  channel: string;
  priority: "low" | "medium" | "high" | "urgent" | string;
  reason: string;
  scheduled_for: string;
  risk_score: number;
  risk_level: string;
}

export interface UpcomingActionsData {
  reminders_enabled: boolean;
  scheduled_count: number;
  sent_count: number;
  failed_count: number;
  recovered_count: number;
  recovered_amount: number;
  next_action_time: string | null;
  queue: ScheduledReminderAction[];
}

export interface ReminderTimelineStep {
  id: string;
  title: string;
  description: string;
  stage: string;
  timestamp: string;
  channel: string;
  status: "completed" | "active" | "pending" | "failed" | string;
  customer_response?: string | null;
  icon?: string | null;
}


export interface BillRiskHistory {
  id: number;
  bill_id: number;
  risk_score: number;
  risk_level: "Low" | "Medium" | "High" | string;
  risk_reason: string | null;
  factors: string[];
  evaluated_at: string | null;
}

export interface BillEmi {
  id: number;
  merchant_id: number;
  customer_id: number | null;
  name: string;
  category: string;
  amount: number;
  currency: string;
  due_date: string;
  recurrence: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  payment_link: string | null;
  notes: string | null;
  status: "Upcoming" | "Due Today" | "Overdue" | "Paid" | "Failed" | string;
  risk_score: number;
  risk_level: "Low" | "Medium" | "High" | string;
  risk_reason: string | null;
  risk_factors: string[];
  days_remaining: number;
  days_overdue: number;
  last_evaluated_at: string | null;
  paid_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  reminder_logs: BillReminderLog[];
  risk_history: BillRiskHistory[];
}

export interface RiskSummary {
  high_risk_count: number;
  high_risk_amount: number;
  medium_risk_count: number;
  medium_risk_amount: number;
  low_risk_count: number;
  low_risk_amount: number;
  total_amount_at_risk: number;
  average_risk_score: number;
  top_risk_reasons: { reason: string; count: number }[];
}

export interface BillEmiSummary {
  total_upcoming_count: number;
  total_amount_due: number;
  due_today_count: number;
  due_today_amount: number;
  due_7_days_count: number;
  due_7_days_amount: number;
  overdue_count: number;
  overdue_amount: number;
  high_risk_count: number;
  high_risk_amount: number;
  paid_count: number;
  paid_amount: number;
  risk_summary: RiskSummary;
  upcoming_vs_overdue: {
    upcoming_amount: number;
    upcoming_count: number;
    overdue_amount: number;
    overdue_count: number;
    paid_amount: number;
    paid_count: number;
  };
  category_breakdown: {
    category: string;
    count: number;
    amount: number;
    overdue_amount: number;
  }[];
  monthly_trend: {
    month: string;
    due_amount: number;
    paid_amount: number;
  }[];
}

export interface BillEmiInput {
  name: string;
  category: string;
  amount: number;
  currency?: string;
  due_date: string;
  recurrence: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  payment_link?: string;
  notes?: string;
  status?: string;
  risk_level?: string;
  risk_score?: number;
  risk_reason?: string;
}

export interface DemoResult {
  case_id: number;
  event_type: string;
  amount_at_risk: number;
  recovery_probability: number | null;
  recommended_action: string | null;
  policy_decision: string | null;
  approved_action: string | null;
  stage?: string;
  whatsapp_status?: string;
  customer_response?: string;
  payment_link_url?: string | null;
  verified_payment_id?: string | null;
  recovery_status: string;
  amount_recovered: number;
}


