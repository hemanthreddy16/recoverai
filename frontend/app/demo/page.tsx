"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  Play,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Brain,
  Cpu,
  Search,
  Eye,
  Zap,
  Sparkles,
  RefreshCw,
  Clock,
  AlertTriangle,
  CreditCard,
  MessageSquare,
  Check,
  Copy,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import { Card, PageHeader, StatusBadge, Badge } from "@/components/ui";
import type { Case, DemoResult } from "@/lib/types";

const SCENARIOS: {
  key: string;
  name: string;
  desc: string;
  tag: string;
  amount: number;
  expected: string;
}[] = [
  {
    key: "simple_payment_failure",
    name: "Card Declined (Standard)",
    desc: "Single-occurrence card decline on a ₹2,400 transaction with strong customer history.",
    tag: "Auto-Recoverable",
    amount: 2400,
    expected: "Notification Sent → Awaiting Payment",
  },
  {
    key: "recoverable_payment_failure",
    name: "Insufficient Funds (High Prob)",
    desc: "Temporary balance insufficiency with 88% recovery probability.",
    tag: "High Probability",
    amount: 1800,
    expected: "Payment Link Created → Awaiting Payment",
  },
  {
    key: "repeated_payment_failure",
    name: "Expired Card / Repeat Decline",
    desc: "Multiple repeated payment failures requiring alternate payment channel.",
    tag: "Multi-Retry",
    amount: 1500,
    expected: "Payment Link Sent",
  },
  {
    key: "high_value_payment",
    name: "High-Value Transaction (₹90k)",
    desc: "Large enterprise payment exceeding automatic threshold — triggers Human-in-the-Loop policy gate.",
    tag: "Human Approval",
    amount: 90000,
    expected: "Policy Hold → Human Gated",
  },
  {
    key: "checkout_abandonment",
    name: "Checkout Abandonment",
    desc: "Customer left checkout funnel before completing payment.",
    tag: "Cart Recovery",
    amount: 3200,
    expected: "Recovery Link Dispatched",
  },
  {
    key: "subscription_failure",
    name: "Subscription Hard Failure",
    desc: "Recurring subscription renewal failed — proactive churn intervention.",
    tag: "SaaS Churn",
    amount: 2200,
    expected: "Dunning Escalation",
  },
  {
    key: "failed_recovery",
    name: "Fraud Blocked (Non-Recoverable)",
    desc: "High-risk fraud score transaction — correctly blocked by policy engine.",
    tag: "Policy Blocked",
    amount: 12000,
    expected: "Blocked by Guardrails",
  },
  {
    key: "successful_recovery",
    name: "Network Error / Transient Glitch",
    desc: "Immediate transient network timeout — 94% instantaneous recovery.",
    tag: "Instant Capture",
    amount: 5400,
    expected: "Gateway Retry → Recaptured",
  },
];

const PIPELINE_STEPS = [
  { key: "detect", name: "Detection Agent", icon: Eye, action: "Payment failure event ingested and case created" },
  { key: "diagnose", name: "Diagnosis Agent", icon: Search, action: "Decline code parsed & transient risk classified" },
  { key: "predict", name: "Prediction Agent", icon: Brain, action: "ML model calculated recovery probability" },
  { key: "strategy", name: "Strategy Agent", icon: Cpu, action: "Optimal remediation strategy selected" },
  { key: "policy", name: "Policy Engine", icon: ShieldAlert, action: "Merchant policy & threshold rules validated" },
  { key: "recover", name: "Recovery Agent", icon: Play, action: "MCP tool executed action through gateway" },
  { key: "verify", name: "Verification Agent", icon: CheckCircle2, action: "Capture confirmed & revenue updated" },
];

export default function DemoPage() {
  const [selectedScenario, setSelectedScenario] = useState<string>("simple_payment_failure");
  const [running, setRunning] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(-1);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [recentCases, setRecentCases] = useState<Case[]>([]);
  const [loadingCases, setLoadingCases] = useState(false);
  const [paymentActionLoading, setPaymentActionLoading] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Fetch recent cases from backend
  async function fetchRecentCases() {
    setLoadingCases(true);
    try {
      const cases = await api.get<Case[]>("/cases?limit=10");
      setRecentCases(cases || []);
    } catch (err: any) {
      console.warn("Could not fetch recent cases", err);
    } finally {
      setLoadingCases(false);
    }
  }

  useEffect(() => {
    fetchRecentCases();
  }, []);

  async function runSimulation(scenarioKey: string) {
    setSelectedScenario(scenarioKey);
    setRunning(true);
    setErrorMsg(null);
    setActionSuccessMsg(null);
    setResult(null);
    setCurrentStepIndex(0);

    // Animate the 7 stages sequentially for a realistic AI command center presentation
    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      setCurrentStepIndex(i);
      await new Promise((resolve) => setTimeout(resolve, 340));
    }

    try {
      const r = await api.post<DemoResult>("/demo/run", { scenario: scenarioKey });
      setResult(r);
      setCurrentStepIndex(PIPELINE_STEPS.length);
      // Immediately refresh recent cases list
      await fetchRecentCases();
    } catch (err: any) {
      console.error("Simulation run error", err);
      setErrorMsg(err?.message || "Failed to execute scenario. Please check backend connection.");
    } finally {
      setRunning(false);
    }
  }

  async function handleSimulatePayment(caseId: number, outcome: "success" | "failure") {
    setPaymentActionLoading(true);
    setActionSuccessMsg(null);
    try {
      const updated = await api.post<any>(`/cases/${caseId}/simulate-customer-payment`, { outcome });
      setActionSuccessMsg(
        outcome === "success"
          ? `✓ Customer payment confirmed! Case #${caseId} transitioned to Payment Verified • RECOVERED (Amount: ${fmt(updated.amount_recovered || updated.amount_at_risk)})`
          : `Customer payment failed. Retry attempt registered in recovery state machine for Case #${caseId}.`
      );
      // Update the active result if matching
      if (result && result.case_id === caseId) {
        setResult({
          ...result,
          recovery_status: updated.recovery_status,
          stage: updated.stage,
          amount_recovered: updated.amount_recovered,
          verified_payment_id: updated.verified_payment_id,
        });
      }
      await fetchRecentCases();
    } catch (err: any) {
      setErrorMsg(`Payment simulation failed: ${err.message || "Unknown error"}`);
    } finally {
      setPaymentActionLoading(false);
    }
  }

  function copyToClipboard(text: string) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  }

  const activeScenario = SCENARIOS.find((s) => s.key === selectedScenario) || SCENARIOS[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live AI Recovery Simulation Lab"
        subtitle="Trigger real-world payment failures, watch the multi-agent pipeline execute, and inspect generated cases live"
      />

      {/* Main Runner Console */}
      <Card className="border-accent2/30 bg-gradient-to-b from-panel to-panel2">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-border/80">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-accent2 uppercase tracking-wider">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Target Scenario</span>
            </div>
            <h2 className="text-lg font-bold text-white mt-0.5">{activeScenario.name}</h2>
            <p className="text-xs text-muted mt-0.5 max-w-xl">{activeScenario.desc}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => runSimulation(activeScenario.key)}
              disabled={running}
              className="btn-primary text-sm px-5 py-2 flex items-center gap-2 shadow-lg shadow-accent/20 cursor-pointer"
            >
              {running ? (
                <>
                  <Zap className="h-4 w-4 animate-spin text-white" />
                  <span>Pipeline Executing…</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Start AI Recovery</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Step-by-Step Pipeline Animation */}
        <div className="py-4 space-y-3">
          <div className="text-xs font-semibold uppercase text-muted tracking-wider flex items-center justify-between">
            <span>Autonomous Pipeline Progression</span>
            {running && <span className="text-accent2 font-mono animate-pulse2">Processing Step 0{currentStepIndex + 1} / 07...</span>}
            {!running && result && <span className="text-ok font-mono">✓ Workflow Complete • Case #{result.case_id} Generated</span>}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            {PIPELINE_STEPS.map((s, idx) => {
              const Icon = s.icon;
              const isCompleted = currentStepIndex > idx || (result && !running);
              const isCurrent = currentStepIndex === idx && running;

              let style = "border-border/60 bg-panel2/60 text-muted";
              if (isCompleted) style = "border-ok/50 bg-ok/10 text-ok";
              if (isCurrent) style = "border-accent2 bg-accent2/20 text-accent2 shadow-md shadow-accent2/20 scale-[1.02]";

              return (
                <div key={s.key} className={`p-3 rounded-lg border flex flex-col justify-between transition-all duration-300 ${style}`}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-[10px] font-mono opacity-70">0{idx + 1}</span>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold">{s.name.split(" ")[0]}</div>
                    <div className="text-[10px] opacity-75 truncate">{s.name}</div>
                  </div>
                  <div className="mt-2 text-[10px] pt-1 border-t border-current/10 truncate font-mono">
                    {isCompleted ? "✓ Completed" : isCurrent ? "Active →" : "Idle"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Error Notification */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-xs flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Success Action Notification */}
        {actionSuccessMsg && (
          <div className="p-3 rounded-lg bg-ok/10 border border-ok/30 text-ok text-xs flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{actionSuccessMsg}</span>
          </div>
        )}

        {/* Simulation Output Summary */}
        {result && (
          <div className="mt-2 p-4 rounded-xl border border-ok/40 bg-panel2/90 space-y-4 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-ok" />
                <span className="font-bold text-white text-sm">Simulation Case Created & Processed</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent2/10 text-accent2 border border-accent2/30">
                  Case #{result.case_id}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/cases/${result.case_id}`}
                  className="btn-ghost text-xs text-accent2 border-accent2/30 flex items-center gap-1.5 px-3 py-1.5 hover:bg-accent2/10"
                >
                  <span>Inspect Case Timeline</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
                <StatusBadge status={result.recovery_status} />
              </div>
            </div>

            {/* Metric badges */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Amount at Risk</div>
                <div className="text-sm font-bold text-warn mt-0.5">{fmt(result.amount_at_risk)}</div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Recovery Prob.</div>
                <div className="text-sm font-bold text-accent2 mt-0.5">
                  {result.recovery_probability != null ? pct(result.recovery_probability) : "—"}
                </div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Strategy</div>
                <div className="text-sm font-bold text-white mt-0.5 font-mono capitalize">
                  {(result.approved_action || result.recommended_action || "smart_retry").replace(/_/g, " ")}
                </div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Policy Gate</div>
                <div className="text-sm font-bold mt-0.5">
                  <Badge color={result.policy_decision === "auto" ? "ok" : result.policy_decision === "approval" ? "warn" : "danger"}>
                    {result.policy_decision || "Auto"}
                  </Badge>
                </div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Recovery Stage</div>
                <div className="text-xs font-bold text-accent mt-0.5 font-mono capitalize">
                  {((result.stage || result.recovery_status) ?? "failed").replace(/_/g, " ")}
                </div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Recovered Revenue</div>
                <div className="text-sm font-bold text-ok mt-0.5">{fmt(result.amount_recovered)}</div>
              </div>
            </div>

            {/* Real-time State & Recovery Actions Bar */}
            <div className="p-3 rounded-lg bg-panel border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5 text-muted">
                  <MessageSquare className="h-3.5 w-3.5 text-accent2" />
                  <span>WhatsApp:</span>
                  <span className="font-semibold text-white capitalize">{(result.whatsapp_status || "not_dispatched").replace(/_/g, " ")}</span>
                </div>
                <div className="text-border">|</div>
                <div className="flex items-center gap-1.5 text-muted">
                  <Clock className="h-3.5 w-3.5 text-warn" />
                  <span>Customer:</span>
                  <span className="font-semibold text-white capitalize">{(result.customer_response || "pending").replace(/_/g, " ")}</span>
                </div>
                {result.payment_link_url && (
                  <>
                    <div className="text-border">|</div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-muted">Payment Link:</span>
                      <button
                        onClick={() => copyToClipboard(result.payment_link_url!)}
                        className="text-accent2 hover:underline flex items-center gap-1 cursor-pointer font-mono"
                      >
                        {copiedLink ? <Check className="h-3 w-3 text-ok" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedLink ? "Copied!" : "Copy Link"}</span>
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Action Buttons for Interactive Testing */}
              <div className="flex items-center gap-2">
                {result.recovery_status !== "recovered" && (
                  <button
                    onClick={() => handleSimulatePayment(result.case_id, "success")}
                    disabled={paymentActionLoading}
                    className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 bg-ok hover:bg-ok/90 text-white cursor-pointer"
                  >
                    <CreditCard className="h-3.5 w-3.5" />
                    <span>Simulate Payment ({fmt(result.amount_at_risk)})</span>
                  </button>
                )}
                <Link
                  href={`/cases/${result.case_id}`}
                  className="btn-ghost text-xs py-1.5 px-3 text-white border-border hover:bg-panel2 flex items-center gap-1"
                >
                  <span>View Case #{result.case_id}</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Selectable Scenario Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-semibold text-white">Select Scenario to Demonstrate:</div>
          <span className="text-xs text-muted">Click any scenario to load and test</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {SCENARIOS.map((s) => {
            const isSelected = selectedScenario === s.key;
            return (
              <div
                key={s.key}
                onClick={() => setSelectedScenario(s.key)}
                className={`p-3.5 rounded-xl border cursor-pointer flex flex-col justify-between transition-all ${
                  isSelected
                    ? "border-accent2 bg-panel2 ring-1 ring-accent2/50"
                    : "border-border bg-panel hover:bg-panel2/60"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-2">
                    <Badge color="accent">{s.tag}</Badge>
                    <span className="font-bold text-white font-mono">{fmt(s.amount)}</span>
                  </div>
                  <div className="font-bold text-white text-sm">{s.name}</div>
                  <p className="text-xs text-muted mt-1 leading-relaxed">{s.desc}</p>
                </div>

                <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                  <span className="text-muted font-mono text-[11px]">{s.expected}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      runSimulation(s.key);
                    }}
                    disabled={running}
                    className="btn-ghost text-xs py-1 px-2.5 text-accent2 border-accent2/30 hover:bg-accent2/10 cursor-pointer"
                  >
                    Run
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Generated Cases in Database */}
      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="font-bold text-white text-sm">Recent Recovery Cases (Live Database)</h3>
            <p className="text-xs text-muted">Cases generated and tracked across all simulation runs and live events</p>
          </div>
          <button
            onClick={fetchRecentCases}
            disabled={loadingCases}
            className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 text-muted hover:text-white"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingCases ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                <th className="th">Case ID</th>
                <th className="th">Event Type</th>
                <th className="th">Amount at Risk</th>
                <th className="th">Reason</th>
                <th className="th">Strategy</th>
                <th className="th">Stage / Status</th>
                <th className="th">Recovered</th>
                <th className="th text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-xs">
              {recentCases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-muted">
                    {loadingCases ? "Loading cases..." : "No cases in database yet. Run a scenario above to create one!"}
                  </td>
                </tr>
              ) : (
                recentCases.map((c) => (
                  <tr key={c.id} className="hover:bg-panel2/40 transition-colors">
                    <td className="td font-mono font-bold text-accent2">
                      <Link href={`/cases/${c.id}`} className="hover:underline">
                        #{c.id}
                      </Link>
                    </td>
                    <td className="td font-medium text-white capitalize">{c.event_type.replace(/_/g, " ")}</td>
                    <td className="td font-bold text-warn font-mono">{fmt(c.amount_at_risk)}</td>
                    <td className="td text-muted font-mono text-[11px]">{c.failure_reason || "—"}</td>
                    <td className="td text-muted font-mono text-[11px] capitalize">
                      {(c.approved_action || c.recommended_action || "—").replace(/_/g, " ")}
                    </td>
                    <td className="td">
                      <div className="flex items-center gap-1.5">
                        <StatusBadge status={c.recovery_status} />
                        {c.stage && (
                          <span className="text-[10px] font-mono text-muted">
                            ({c.stage.replace(/_/g, " ")})
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="td font-bold text-ok font-mono">
                      {c.amount_recovered > 0 ? fmt(c.amount_recovered) : "—"}
                    </td>
                    <td className="td text-right">
                      <div className="flex items-center justify-end gap-2">
                        {c.recovery_status !== "recovered" && (
                          <button
                            onClick={() => handleSimulatePayment(c.id, "success")}
                            disabled={paymentActionLoading}
                            className="text-[11px] text-ok hover:underline font-medium cursor-pointer"
                          >
                            Pay & Recover
                          </button>
                        )}
                        <Link
                          href={`/cases/${c.id}`}
                          className="text-[11px] text-accent2 hover:underline flex items-center gap-0.5"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
