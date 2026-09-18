"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Bot,
  Eye,
  Search,
  Brain,
  Cpu,
  ShieldAlert,
  Play,
  CheckCircle2,
  LineChart,
  Clock,
  Sparkles,
  Activity,
  Zap,
} from "lucide-react";
import { api, pct } from "@/lib/api";
import { useAsync, Card, PageHeader, StatusBadge, Badge } from "@/components/ui";
import type { AgentDecision, AgentRun, AgentStats } from "@/lib/types";

const AGENT_ICONS: Record<string, any> = {
  detection: Eye,
  diagnosis: Search,
  prediction: Brain,
  strategy: Cpu,
  policy: ShieldAlert,
  recovery: Play,
  verification: CheckCircle2,
  analytics: LineChart,
};

export default function AgentsControlCenterPage() {
  const [tab, setTab] = useState<"control" | "decisions" | "runs">("control");

  const { data: stats, loading: loadingStats } = useAsync<AgentStats[]>(
    () => api.get("/agents/stats"),
    []
  );
  const { data: runs, loading: loadingRuns } = useAsync<AgentRun[]>(
    () => api.get("/agents/activity?limit=60"),
    []
  );
  const { data: decisions, loading: loadingDecisions } = useAsync<AgentDecision[]>(
    () => api.get("/agents/decisions?limit=60"),
    []
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Multi-Agent AI Control Center"
        subtitle="Orchestration telemetry, active tasks, latency, and explainable decision stream"
        action={
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs text-ok font-mono px-3 py-1.5 rounded-full bg-ok/10 border border-ok/30">
              <span className="h-2 w-2 rounded-full bg-ok animate-pulse2" />
              Autonomous Engine Online
            </span>
          </div>
        }
      />

      {/* Tabs */}
      <div className="flex rounded-lg overflow-hidden border border-border bg-panel2 max-w-md">
        <button
          onClick={() => setTab("control")}
          className={`flex-1 py-2 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 ${
            tab === "control" ? "bg-accent text-white" : "text-muted hover:text-white"
          }`}
        >
          <Bot className="h-3.5 w-3.5" />
          Agent Cards (8)
        </button>
        <button
          onClick={() => setTab("decisions")}
          className={`flex-1 py-2 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 ${
            tab === "decisions" ? "bg-accent text-white" : "text-muted hover:text-white"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          Decision Stream
        </button>
        <button
          onClick={() => setTab("runs")}
          className={`flex-1 py-2 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 ${
            tab === "runs" ? "bg-accent text-white" : "text-muted hover:text-white"
          }`}
        >
          <Activity className="h-3.5 w-3.5" />
          Live Run Logs
        </button>
      </div>

      {/* 1. AGENT CONTROL CARDS TAB */}
      {tab === "control" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats?.map((agent) => {
            const Icon = AGENT_ICONS[agent.name] || Bot;
            return (
              <Card
                key={agent.name}
                className="flex flex-col justify-between hover:border-accent2/40 transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent2 group-hover:scale-105 transition-transform">
                      <Icon className="h-4 w-4" />
                    </div>
                    <StatusBadge status={agent.status} />
                  </div>

                  <div className="font-bold text-white text-sm">{agent.title}</div>
                  <div className="text-xs text-muted mt-1 leading-relaxed line-clamp-2">
                    {agent.current_task}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/60 space-y-2 text-xs">
                  <div className="p-2 rounded bg-panel2 border border-border/70">
                    <div className="text-[10px] uppercase text-muted font-mono">Last Action</div>
                    <div className="text-white font-medium text-[11px] truncate mt-0.5">
                      {agent.last_action}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center pt-1">
                    <div>
                      <div className="text-[10px] text-muted uppercase">Runs</div>
                      <div className="font-mono font-bold text-white">{agent.execution_count}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted uppercase">Success</div>
                      <div className="font-mono font-bold text-ok">{pct(agent.success_rate)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted uppercase">Avg Latency</div>
                      <div className="font-mono font-bold text-accent2">{agent.avg_duration_ms}ms</div>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* 2. DECISION STREAM TAB */}
      {tab === "decisions" && (
        <Card title="Explainable AI Decision Trace" className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                  <th className="th">Timestamp</th>
                  <th className="th">Agent</th>
                  <th className="th">Decision Type</th>
                  <th className="th">Confidence</th>
                  <th className="th">Input Context</th>
                  <th className="th">Output Reasoning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-xs">
                {decisions?.map((d) => (
                  <tr key={d.id} className="hover:bg-panel2/40">
                    <td className="td text-muted font-mono whitespace-nowrap">
                      {d.created_at ? new Date(d.created_at).toLocaleTimeString() : "—"}
                    </td>
                    <td className="td font-bold text-white capitalize">{d.agent_name}</td>
                    <td className="td font-mono text-accent2">{d.decision_type}</td>
                    <td className="td font-mono text-ok">
                      {d.confidence != null ? pct(d.confidence) : "—"}
                    </td>
                    <td className="td max-w-xs truncate text-muted font-mono text-[11px]">
                      {JSON.stringify(d.input_data)}
                    </td>
                    <td className="td max-w-xs truncate text-white font-medium text-[11px]">
                      {JSON.stringify(d.output_data)}
                    </td>
                  </tr>
                ))}
                {!decisions?.length && (
                  <tr>
                    <td className="td text-muted text-center py-6" colSpan={6}>
                      No agent decisions recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 3. LIVE RUN LOGS TAB */}
      {tab === "runs" && (
        <Card title="Recent Agent Execution Logs" className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                  <th className="th">Run ID</th>
                  <th className="th">Agent</th>
                  <th className="th">Linked Case</th>
                  <th className="th">Status</th>
                  <th className="th">Started</th>
                  <th className="th">Finished</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-xs">
                {runs?.map((r) => (
                  <tr key={r.id} className="hover:bg-panel2/40">
                    <td className="td font-mono text-muted">#{r.id}</td>
                    <td className="td font-bold text-white capitalize">{r.agent_name}</td>
                    <td className="td">
                      {r.case_id ? (
                        <Link href={`/cases/${r.case_id}`} className="text-accent2 hover:underline font-mono">
                          Case #{r.case_id}
                        </Link>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="td">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="td text-muted font-mono">
                      {r.started_at ? new Date(r.started_at).toLocaleTimeString() : "—"}
                    </td>
                    <td className="td text-muted font-mono">
                      {r.finished_at ? new Date(r.finished_at).toLocaleTimeString() : "—"}
                    </td>
                  </tr>
                ))}
                {!runs?.length && (
                  <tr>
                    <td className="td text-muted text-center py-6" colSpan={6}>
                      No recent agent runs found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
