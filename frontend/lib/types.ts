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
  action_status: string;
  recovery_status: string;
  amount_recovered: number;
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
