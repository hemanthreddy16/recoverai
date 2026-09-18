"use client";

import { useState } from "react";
import {
  Server,
  Terminal,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  Zap,
  Code,
  RefreshCw,
} from "lucide-react";
import { api, fmt } from "@/lib/api";
import { useAsync, Card, PageHeader, Kpi, StatusBadge, Badge } from "@/components/ui";
import type { MCPCall, MCPServer } from "@/lib/types";

export default function McpPage() {
  const [selectedTool, setSelectedTool] = useState<string>("get_customer");
  const [toolArgs, setToolArgs] = useState<string>('{\n  "customer_id": 1\n}');
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const { data: registry, loading: loadingReg } = useAsync<{ servers: MCPServer[] }>(
    () => api.get("/mcp/registry"),
    []
  );
  const { data: calls, refetch: refetchCalls } = useAsync<MCPCall[]>(
    () => api.get("/mcp/calls?limit=100"),
    []
  );
  const { data: summary } = useAsync<{
    total_calls: number;
    ok: number;
    denied: number;
    error: number;
    success_rate: number;
    by_tool: Record<string, number>;
  }>(() => api.get("/mcp/summary"), []);

  async function handleTestTool() {
    setTestRunning(true);
    setTestResult(null);
    let parsedArgs = {};
    try {
      parsedArgs = JSON.parse(toolArgs);
    } catch {
      setTestResult({ status: "error", error: "Invalid JSON format in arguments" });
      setTestRunning(false);
      return;
    }

    try {
      const res = await api.post("/mcp/test-tool", {
        tool_name: selectedTool,
        arguments: parsedArgs,
      });
      setTestResult(res);
      refetchCalls();
    } catch (err: any) {
      setTestResult({ status: "error", error: err.message || "Failed to execute tool" });
    } finally {
      setTestRunning(false);
    }
  }

  function handleSelectToolPreset(toolName: string) {
    setSelectedTool(toolName);
    if (toolName === "get_customer" || toolName === "get_payment_history") {
      setToolArgs('{\n  "customer_id": 1\n}');
    } else if (toolName === "get_payment" || toolName === "retry_payment" || toolName === "verify_payment") {
      setToolArgs('{\n  "payment_id": 1\n}');
    } else if (toolName === "create_payment_link") {
      setToolArgs('{\n  "customer_id": 1,\n  "amount": 2500,\n  "reason": "Payment recovery"\n}');
    } else if (toolName === "send_email" || toolName === "send_whatsapp") {
      setToolArgs('{\n  "customer_id": 1,\n  "message": "Action required: Complete payment renewal"\n}');
    } else {
      setToolArgs("{}");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Context Protocol (MCP) Tool Registry"
        subtitle="Secure, authorized gateway connecting AI agents to payment providers, databases & notification channels"
        action={
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs text-ok font-mono px-3 py-1.5 rounded-full bg-ok/10 border border-ok/30">
              <span className="h-2 w-2 rounded-full bg-ok animate-pulse2" />
              3 Servers Connected
            </span>
          </div>
        }
      />

      {/* Top MCP Telemetry KPIs */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Kpi label="Total Tool Calls" value={String(summary.total_calls)} />
          <Kpi label="Successful Invocations" value={String(summary.ok)} color="text-ok" />
          <Kpi label="Policy Denials" value={String(summary.denied)} color="text-warn" />
          <Kpi
            label="Gateway Reliability"
            value={`${((summary.success_rate || 0) * 100).toFixed(1)}%`}
            color="text-accent2"
          />
        </div>
      )}

      {/* Connected MCP Servers & Tool Cards */}
      <div className="space-y-4">
        <div className="text-sm font-semibold text-white">Registered MCP Server Nodes:</div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {registry?.servers?.map((server) => (
            <Card key={server.server_name} className="flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between">
                  <div className="font-bold text-white text-base flex items-center gap-2">
                    <Server className="h-4 w-4 text-accent2" />
                    <span>{server.server_name}</span>
                  </div>
                  <Badge color="ok">Connected</Badge>
                </div>
                <div className="text-[11px] text-accent2 font-mono mt-1">{server.protocol}</div>
                <p className="text-xs text-muted mt-2 leading-relaxed">{server.description}</p>
              </div>

              <div className="space-y-2 pt-2 border-t border-border/70">
                <div className="text-[10px] uppercase text-muted font-bold tracking-wider">
                  Exposed Tools ({server.tools.length}):
                </div>
                <div className="space-y-1.5">
                  {server.tools.map((t) => (
                    <div
                      key={t.name}
                      onClick={() => handleSelectToolPreset(t.name)}
                      className="p-2 rounded bg-panel2 border border-border/70 hover:border-accent2/50 cursor-pointer flex items-center justify-between text-xs transition-colors"
                    >
                      <div>
                        <span className="font-mono text-accent2 font-bold">{t.name}</span>
                        <div className="text-[10px] text-muted truncate max-w-[200px]">{t.description}</div>
                      </div>
                      <span className="text-[10px] font-mono text-muted bg-panel px-1.5 py-0.5 rounded border border-border">
                        {t.avg_duration_ms}ms
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Interactive Sandbox Test Runner */}
      <Card
        title={
          <div className="flex items-center gap-2 text-white">
            <Terminal className="h-4 w-4 text-accent2" />
            <span>Interactive MCP Tool Sandbox Runner</span>
          </div>
        }
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-muted block mb-1">Target MCP Tool</label>
              <select
                className="input text-xs"
                value={selectedTool}
                onChange={(e) => handleSelectToolPreset(e.target.value)}
              >
                <option value="get_customer">Database MCP: get_customer</option>
                <option value="get_payment_history">Database MCP: get_payment_history</option>
                <option value="get_payment">Razorpay MCP: get_payment</option>
                <option value="retry_payment">Razorpay MCP: retry_payment</option>
                <option value="create_payment_link">Razorpay MCP: create_payment_link</option>
                <option value="verify_payment">Razorpay MCP: verify_payment</option>
                <option value="send_email">Notification MCP: send_email</option>
                <option value="send_whatsapp">Notification MCP: send_whatsapp</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted block mb-1">Arguments (JSON payload)</label>
              <textarea
                className="input font-mono text-xs h-32 text-accent2"
                value={toolArgs}
                onChange={(e) => setToolArgs(e.target.value)}
              />
            </div>

            <button
              onClick={handleTestTool}
              disabled={testRunning}
              className="btn-primary text-xs flex items-center gap-2"
            >
              {testRunning ? <Zap className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              <span>{testRunning ? "Executing in Sandbox…" : "Execute Tool via MCP Gateway"}</span>
            </button>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted block mb-1">Execution Response</label>
            <div className="p-3 rounded-lg bg-panel2 border border-border/80 min-h-[190px] font-mono text-xs overflow-auto">
              {testResult ? (
                <pre className="text-[11px] text-white/90">
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              ) : (
                <div className="text-muted flex flex-col items-center justify-center h-40 text-center text-xs">
                  <Code className="h-6 w-6 text-muted/40 mb-1" />
                  <span>Select a tool and click execute to verify sandbox output.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Tool Execution History Table */}
      <Card title="Live MCP Gateway Execution Ledger" className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                <th className="th">Timestamp</th>
                <th className="th">Tool Name</th>
                <th className="th">Arguments</th>
                <th className="th">Response Payload</th>
                <th className="th">Status</th>
                <th className="th">Latency</th>
                <th className="th">Caller</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-xs">
              {calls?.map((c) => (
                <tr key={c.id} className="hover:bg-panel2/40">
                  <td className="td text-muted font-mono whitespace-nowrap">
                    {c.created_at ? new Date(c.created_at).toLocaleTimeString() : "—"}
                  </td>
                  <td className="td font-mono font-bold text-accent2">{c.tool_name}</td>
                  <td className="td max-w-xs font-mono text-[11px] text-muted truncate">
                    {JSON.stringify(c.arguments)}
                  </td>
                  <td className="td max-w-xs font-mono text-[11px] text-white truncate">
                    {JSON.stringify(c.result)}
                  </td>
                  <td className="td">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="td font-mono text-accent2">{c.duration_ms ?? 24}ms</td>
                  <td className="td text-muted capitalize">{c.caller || "Agent"}</td>
                </tr>
              ))}
              {!calls?.length && (
                <tr>
                  <td className="td text-muted text-center py-6" colSpan={7}>
                    No tool calls recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
