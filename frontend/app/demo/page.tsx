"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FlaskConical,
  CheckCircle2,
  XCircle,
  Clock,
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
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import { useAsync, Card, PageHeader, Kpi, StatusBadge, Badge } from "@/components/ui";
import type { DemoResult } from "@/lib/types";

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

  async function runSimulation(scenarioKey: string) {
    setSelectedScenario(scenarioKey);
    setRunning(true);
    setResult(null);
    setCurrentStepIndex(0);

    // Animate the 7 stages sequentially for a realistic AI command center presentation
    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      setCurrentStepIndex(i);
      await new Promise((resolve) => setTimeout(resolve, 380));
    }

    try {
      const r = await api.post<DemoResult>("/demo/run", { scenario: scenarioKey });
      setResult(r);
      setCurrentStepIndex(PIPELINE_STEPS.length);
    } catch (err: any) {
      console.error("Simulation run error", err);
    } finally {
      setRunning(false);
    }
  }

  const activeScenario = SCENARIOS.find((s) => s.key === selectedScenario) || SCENARIOS[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live AI Recovery Simulation Lab"
        subtitle="Simulate real-world payment failures, policy rejections, and autonomous MCP recovery workflows"
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
              className="btn-primary text-sm px-5 py-2 flex items-center gap-2 shadow-lg shadow-accent/20"
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
            {!running && result && <span className="text-ok font-mono">✓ Workflow Complete</span>}
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

        {/* Simulation Output Summary */}
        {result && (
          <div className="mt-2 p-4 rounded-xl border border-ok/40 bg-panel2/90 space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-ok" />
                <span className="font-bold text-white text-sm">Simulation Execution Result</span>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/cases/${result.case_id}`} className="btn-ghost text-xs text-accent2 border-accent2/30 flex items-center gap-1">
                  <span>Inspect Case #{result.case_id}</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
                <StatusBadge status={result.recovery_status} />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs pt-1">
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
                <div className="text-[10px] uppercase text-muted">Recovery Status</div>
                <div className="text-sm font-bold text-white mt-0.5 capitalize">{result.recovery_status}</div>
              </div>
              <div className="p-2.5 rounded bg-panel border border-border/80">
                <div className="text-[10px] uppercase text-muted">Recovered Revenue</div>
                <div className="text-sm font-bold text-ok mt-0.5">{fmt(result.amount_recovered)}</div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Selectable Scenario Cards */}
      <div>
        <div className="text-sm font-semibold text-white mb-3">Select Scenario to Demonstrate:</div>
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
                    className="btn-ghost text-xs py-1 px-2 text-accent2 border-accent2/30 hover:bg-accent2/10"
                  >
                    Run
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
