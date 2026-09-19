"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Sparkles,
  Send,
  Bot,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  CornerDownLeft,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import { Card, PageHeader, Kpi, Badge, StatusBadge } from "@/components/ui";
import type { CommandResponse } from "@/lib/types";

const SUGGESTED_QUERIES = [
  "How much revenue is currently at risk?",
  "Show me all high-value failed payments",
  "Which cases have the highest recovery probability?",
  "Why did case #1 fail?",
  "Which recovery strategy performs best?",
  "Show me customers with high payment failure risk",
  "Recover the highest priority case",
];

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  response?: CommandResponse;
}

export default function CommandPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Welcome to RESURGE Autonomous Revenue Intelligence. You can query live revenue risk metrics, inspect AI decision reasoning, analyze strategy efficacy, or execute policy-gated recovery workflows in natural language.",
    },
  ]);

  async function handleSend(queryText?: string) {
    const textToSend = (queryText || input).trim();
    if (!textToSend || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: textToSend }]);
    setLoading(true);

    try {
      const res = await api.post<CommandResponse>("/command/query", { query: textToSend });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, response: res },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Command query failed: ${err.message || "Unknown error"}. Please check that backend services are active.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Command Center"
        subtitle="Natural language revenue intelligence, decision explainability & policy-governed action triggers"
      />

      {/* Suggested Quick Queries */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-muted flex items-center gap-1 font-medium">
          <Sparkles className="h-3 w-3 text-accent2" /> Suggested prompts:
        </span>
        {SUGGESTED_QUERIES.map((q, i) => (
          <button
            key={i}
            onClick={() => handleSend(q)}
            className="text-xs px-2.5 py-1 rounded-full bg-panel2 border border-border hover:border-accent2/50 text-white/80 hover:text-white transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Chat / Query Stream */}
      <Card className="min-h-[420px] max-h-[600px] overflow-y-auto flex flex-col justify-between space-y-4 p-4">
        <div className="space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 text-sm ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {m.role === "assistant" && (
                <div className="h-8 w-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center text-accent2 shrink-0">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div
                className={`p-3.5 rounded-xl max-w-2xl ${
                  m.role === "user"
                    ? "bg-accent text-white"
                    : "bg-panel2 border border-border text-white space-y-3"
                }`}
              >
                <div className="leading-relaxed">{m.text}</div>

                {/* Structured Rich Payload Render */}
                {m.response?.data && (
                  <div className="space-y-2 pt-1 border-t border-border/60">
                    {/* Revenue Overview Stats */}
                    {m.response.data.revenue_at_risk != null && (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                        <div className="p-2 rounded bg-panel border border-border/70">
                          <div className="text-[10px] uppercase text-muted">At Risk</div>
                          <div className="text-sm font-bold text-warn">{fmt(m.response.data.revenue_at_risk)}</div>
                        </div>
                        <div className="p-2 rounded bg-panel border border-border/70">
                          <div className="text-[10px] uppercase text-muted">Predicted Rec.</div>
                          <div className="text-sm font-bold text-accent2">{fmt(m.response.data.predicted_recoverable)}</div>
                        </div>
                        <div className="p-2 rounded bg-panel border border-border/70">
                          <div className="text-[10px] uppercase text-muted">Recovered</div>
                          <div className="text-sm font-bold text-ok">{fmt(m.response.data.revenue_recovered)}</div>
                        </div>
                        <div className="p-2 rounded bg-panel border border-border/70">
                          <div className="text-[10px] uppercase text-muted">Active Cases</div>
                          <div className="text-sm font-bold text-white">{m.response.data.active_cases}</div>
                        </div>
                      </div>
                    )}

                    {/* Case list output */}
                    {m.response.data.cases && Array.isArray(m.response.data.cases) && (
                      <div className="space-y-1.5 pt-2">
                        <div className="text-xs font-semibold text-muted uppercase">Matching Cases:</div>
                        {m.response.data.cases.map((c: any) => (
                          <div key={c.id} className="p-2 rounded bg-panel border border-border/70 flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <Link href={`/cases/${c.id}`} className="font-bold text-accent2 hover:underline">
                                #{c.id}
                              </Link>
                              <span className="text-white font-medium">{fmt(c.amount)}</span>
                              <span className="text-muted">· {c.failure_reason || "Declined"}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {c.recovery_probability != null && (
                                <span className="font-mono text-accent2">{pct(c.recovery_probability)}</span>
                              )}
                              <StatusBadge status={c.recovery_status || c.status} />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Strategies list output */}
                    {m.response.data.strategies && Array.isArray(m.response.data.strategies) && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2">
                        {m.response.data.strategies.map((s: any, i: number) => (
                          <div key={i} className="p-2 rounded bg-panel border border-border/70 text-xs">
                            <div className="font-bold text-accent2 capitalize">{s.strategy.replace(/_/g, " ")}</div>
                            <div className="text-ok font-bold mt-1">{fmt(s.recovered_amount)}</div>
                            <div className="text-muted text-[10px]">{s.recovered_cases} cases recovered</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Suggested Action Buttons */}
                    {m.response.suggested_actions && m.response.suggested_actions.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-2">
                        {m.response.suggested_actions.map((act, i) => (
                          act && (
                            <button
                              key={i}
                              onClick={() => {
                                if (act.action.startsWith("/")) {
                                  window.location.href = act.action;
                                } else {
                                  handleSend(act.action);
                                }
                              }}
                              className="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1 text-accent2 border-accent2/30"
                            >
                              <span>{act.label}</span>
                              <ArrowRight className="h-3 w-3" />
                            </button>
                          )
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-3 text-sm text-muted">
              <div className="h-8 w-8 rounded-lg bg-panel2 border border-border flex items-center justify-center text-accent2 shrink-0 animate-spin">
                <Cpu className="h-4 w-4" />
              </div>
              <span className="animate-pulse2 font-mono text-xs">Analyzing telemetry & executing policy checks…</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="pt-3 border-t border-border flex items-center gap-2"
        >
          <input
            className="input flex-1 text-sm bg-panel2 border-border/80 focus:border-accent2"
            placeholder="Ask a question or enter a recovery instruction (e.g. 'Why did case #1 fail?', 'Show highest probability cases')..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn-primary flex items-center gap-1.5 px-4" disabled={loading || !input.trim()}>
            <span>Ask</span>
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </Card>
    </div>
  );
}
