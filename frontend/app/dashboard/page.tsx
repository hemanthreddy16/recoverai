"use client";

import Link from "next/link";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Brain,
  CheckCircle2,
  Cpu,
  Eye,
  FolderKanban,
  Play,
  ScrollText,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import {
  useAsync,
  Kpi,
  Card,
  PageHeader,
  StatusBadge,
  Badge,
  LivePipelineVisualizer,
} from "@/components/ui";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { data, loading, refetch } = useAsync<Dashboard>(() => api.get("/dashboard"), []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Autonomous Recovery Command Center"
        subtitle="Real-time multi-agent revenue protection, ML probability prediction & MCP remediation"
        action={
          <div className="flex items-center gap-2.5">
            <Link href="/command" className="btn-ghost flex items-center gap-1.5 text-xs text-accent2 border-accent2/30 hover:bg-accent2/10">
              <Sparkles className="h-3.5 w-3.5" />
              AI Command
            </Link>
            <Link href="/demo" className="btn-primary flex items-center gap-1.5 text-xs">
              <Play className="h-3.5 w-3.5" />
              Run Simulation
            </Link>
          </div>
        }
      />

      {loading && (
        <div className="flex h-48 items-center justify-center text-muted">
          <span className="animate-pulse2 font-mono text-xs">Synchronizing live revenue telemetry…</span>
        </div>
      )}

      {data && (
        <>
          {/* Primary Top KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
            <Kpi
              label="Revenue at Risk"
              value={fmt(data.revenue_at_risk)}
              color="text-warn"
              sub={`${data.active_cases} active cases`}
              icon={<AlertTriangle className="h-4 w-4" />}
            />
            <Kpi
              label="Predicted Recoverable"
              value={fmt(data.predicted_recoverable)}
              color="text-accent2"
              sub="ML Model (78% AUC)"
              icon={<Brain className="h-4 w-4" />}
            />
            <Kpi
              label="Revenue Recovered"
              value={fmt(data.revenue_recovered)}
              color="text-ok"
              sub="Captured through MCP"
              icon={<CheckCircle2 className="h-4 w-4" />}
            />
            <Kpi
              label="Recovery Rate"
              value={pct(data.recovery_rate)}
              color="text-ok"
              sub="Autonomous + gated"
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <Kpi
              label="Failed Payments"
              value={String(data.failed_payments)}
              color="text-danger"
              sub="Gateway rejects"
              icon={<AlertTriangle className="h-4 w-4" />}
            />
            <Kpi
              label="High-Risk Customers"
              value={String(data.high_risk_customers_count)}
              color="text-warn"
              sub="Repeat failures"
              icon={<ShieldAlert className="h-4 w-4" />}
            />
          </div>

          {/* Live Recovery Pipeline Banner */}
          <Card
            title={
              <div className="flex items-center gap-2 text-white font-semibold">
                <Zap className="h-4 w-4 text-accent2" />
                <span>Autonomous Recovery Pipeline Flow</span>
                <span className="text-xs text-muted font-normal">· Multi-Agent Sequential Engine</span>
              </div>
            }
            headerRight={
              <span className="flex items-center gap-1.5 text-xs text-ok font-mono">
                <span className="h-2 w-2 rounded-full bg-ok animate-pulse2" />
                8 Agents Operational
              </span>
            }
          >
            <LivePipelineVisualizer activeStep={3} />
          </Card>

          {/* Quick Actions Panel */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Link href="/cases" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <FolderKanban className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">All Cases</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
            <Link href="/command" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">AI Command</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
            <Link href="/agents" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">Agent Control</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
            <Link href="/mcp" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">MCP Tools</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
            <Link href="/demo" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <Play className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">Demo Lab</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
            <Link href="/audit" className="p-3 rounded-lg border border-border bg-panel hover:bg-panel2/80 transition-all flex items-center justify-between group">
              <div className="flex items-center gap-2">
                <ScrollText className="h-4 w-4 text-accent2" />
                <span className="text-xs font-medium text-white">Audit Log</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted group-hover:text-accent2 group-hover:translate-x-0.5 transition-all" />
            </Link>
          </div>

          {/* Main Visual Data Row: 14-Day Trend + Live Pipeline Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card title="Recovery Trend · 14-Day Trajectory" className="lg:col-span-2">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.recovery_trend}>
                    <defs>
                      <linearGradient id="recGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1e2733" strokeDasharray="3 3" />
                    <XAxis dataKey="date" stroke="#8a97a8" fontSize={11} />
                    <YAxis
                      stroke="#8a97a8"
                      fontSize={11}
                      tickFormatter={(v) => fmt(v)}
                      width={65}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0f141d",
                        border: "1px solid #1e2733",
                        borderRadius: "8px",
                      }}
                      formatter={(v: any) => [fmt(Number(v)), "Recovered"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="recovered"
                      stroke="#22d3ee"
                      fill="url(#recGrad)"
                      strokeWidth={2}
                      name="Recovered"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Live Agent Pipeline Stream">
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {data.recent_pipeline_runs?.map((run, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-md border border-border/70 bg-panel2/60 text-xs space-y-1 hover:border-accent2/40 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <Link
                        href={`/cases/${run.case_id}`}
                        className="font-bold text-accent2 hover:underline"
                      >
                        Case #{run.case_id}
                      </Link>
                      <StatusBadge status={run.status} />
                    </div>
                    <div className="text-white/80 font-medium">
                      {fmt(run.amount)} · {run.event_type.replace(/_/g, " ")}
                    </div>
                    <div className="text-muted text-[11px] truncate">
                      Strategy: <span className="text-white/90">{run.strategy || "Smart Retry"}</span> (Policy: {run.policy || "auto"})
                    </div>
                  </div>
                ))}
                {!data.recent_pipeline_runs?.length && (
                  <div className="text-sm text-muted py-6 text-center">
                    No active runs. Trigger one in the{" "}
                    <Link href="/demo" className="text-accent2 hover:underline">
                      Demo Center
                    </Link>
                    .
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* High-Risk At-Risk Cases Table */}
          <Card
            title="High-Priority At-Risk Cases"
            headerRight={
              <Link href="/cases" className="text-xs text-accent2 hover:underline flex items-center gap-1">
                View all cases <ArrowRight className="h-3 w-3" />
              </Link>
            }
            className="p-0"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                    <th className="th">Case ID</th>
                    <th className="th">Customer</th>
                    <th className="th">Amount at Risk</th>
                    <th className="th">Failure Reason</th>
                    <th className="th">Recovery Prob.</th>
                    <th className="th">Policy Status</th>
                    <th className="th">Status</th>
                    <th className="th text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {data.high_risk_cases?.map((c) => (
                    <tr key={c.id} className="hover:bg-panel2/40 text-xs">
                      <td className="td font-mono">
                        <Link href={`/cases/${c.id}`} className="text-accent2 font-bold hover:underline">
                          #{c.id}
                        </Link>
                      </td>
                      <td className="td text-white font-medium">Customer #{c.customer_id}</td>
                      <td className="td font-bold text-white">{fmt(c.amount_at_risk)}</td>
                      <td className="td text-muted capitalize">{c.failure_reason || "Declined"}</td>
                      <td className="td">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-accent2">
                            {c.recovery_probability != null ? pct(c.recovery_probability) : "—"}
                          </span>
                        </div>
                      </td>
                      <td className="td">
                        <Badge color={c.policy_decision === "auto" ? "ok" : c.policy_decision === "approval" ? "warn" : "danger"}>
                          {c.policy_decision || "Pending"}
                        </Badge>
                      </td>
                      <td className="td">
                        <StatusBadge status={c.recovery_status} />
                      </td>
                      <td className="td text-right">
                        <Link href={`/cases/${c.id}`} className="btn-ghost text-[11px] py-1 px-2">
                          Inspect Trace
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {!data.high_risk_cases?.length && (
                    <tr>
                      <td className="td text-muted text-center py-6" colSpan={8}>
                        No high-risk cases detected. Platform state healthy.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
