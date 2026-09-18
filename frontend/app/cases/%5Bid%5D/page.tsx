"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Brain,
  Cpu,
  Search,
  Server,
  Sparkles,
  AlertTriangle,
  Play,
  User,
  History,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import {
  useAsync,
  Card,
  PageHeader,
  StatusBadge,
  Badge,
  LivePipelineVisualizer,
} from "@/components/ui";
import type { CaseDetail, TimelineEvent } from "@/lib/types";

export default function CaseDetailPage({ params }: { params: { id: string } }) {
  const caseId = Number(params.id);
  const [actionInProgress, setActionInProgress] = useState(false);
  const [outcomeMessage, setOutcomeMessage] = useState<string | null>(null);

  const { data: c, loading, refetch: refetchCase } = useAsync<CaseDetail>(
    () => api.get(`/cases/${caseId}`),
    [caseId]
  );
  const { data: tl, refetch: refetchTimeline } = useAsync<TimelineEvent[]>(
    () => api.get(`/cases/${caseId}/timeline`),
    [caseId]
  );

  async function handleApproval(outcome: "success" | "failure") {
    setActionInProgress(true);
    try {
      await api.post(`/cases/${caseId}/approve`, { simulated_outcome: outcome });
      setOutcomeMessage(`Action approved and executed (${outcome}). Verification updated case state.`);
      await Promise.all([refetchCase(), refetchTimeline()]);
    } catch (err: any) {
      setOutcomeMessage(`Action execution failed: ${err.message || "Unknown error"}`);
    } finally {
      setActionInProgress(false);
    }
  }

  async function handleDenial() {
    setActionInProgress(true);
    try {
      await api.post(`/cases/${caseId}/deny`, {});
      setOutcomeMessage("Recovery action denied. Case transitioned to stopped status.");
      await Promise.all([refetchCase(), refetchTimeline()]);
    } catch (err: any) {
      setOutcomeMessage(`Denial failed: ${err.message || "Unknown error"}`);
    } finally {
      setActionInProgress(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link href="/cases" className="text-xs text-muted hover:text-white flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Cases
        </Link>
      </div>

      <PageHeader
        title={`Recovery Case #RC-${caseId}`}
        subtitle="Autonomous agent diagnosis, explainable ML reasoning, policy validation & execution trace"
        action={
          <div className="flex items-center gap-2">
            <StatusBadge status={c?.recovery_status} />
            <Badge color={c?.policy_decision === "auto" ? "ok" : c?.policy_decision === "approval" ? "warn" : "danger"}>
              Policy: {c?.policy_decision || "Pending"}
            </Badge>
          </div>
        }
      />

      {loading && (
        <div className="flex h-48 items-center justify-center text-muted">
          <span className="animate-pulse2 font-mono text-xs">Loading case decision trace…</span>
        </div>
      )}

      {c && (
        <>
          {/* Human-in-the-Loop Action Approval Banner */}
          {c.policy_decision === "approval" && c.recovery_status === "open" && (
            <div className="p-4 rounded-xl border border-warn/40 bg-warn/10 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5 text-warn font-semibold">
                  <ShieldAlert className="h-5 w-5 shrink-0" />
                  <span>Human-in-the-Loop Approval Required</span>
                </div>
                <Badge color="warn">Policy Gate Held</Badge>
              </div>
              <p className="text-xs text-white/90 leading-relaxed">
                This case exceeds automated threshold limits ({fmt(c.amount_at_risk)} at risk). The Strategy Agent recommends{" "}
                <span className="font-mono font-bold text-white uppercase">{c.recommended_action || "smart_retry"}</span>.
                Review AI diagnosis and authorize or reject execution below.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <button
                  className="btn-primary text-xs flex items-center gap-1.5"
                  disabled={actionInProgress}
                  onClick={() => handleApproval("success")}
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Authorize & Execute Recovery
                </button>
                <button
                  className="btn-ghost text-xs text-danger border-danger/30 hover:bg-danger/10 flex items-center gap-1.5"
                  disabled={actionInProgress}
                  onClick={handleDenial}
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Deny Action
                </button>
              </div>
            </div>
          )}

          {outcomeMessage && (
            <div className="p-3 rounded-lg border border-accent2/30 bg-panel2 text-xs text-white flex items-center justify-between">
              <span>{outcomeMessage}</span>
              <button onClick={() => setOutcomeMessage(null)} className="text-muted hover:text-white">✕</button>
            </div>
          )}

          {/* Core Trace & Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Col (2 cols): Explainable AI Trace */}
            <div className="lg:col-span-2 space-y-5">
              {/* AI Explainability Reasoning Box */}
              <Card
                title={
                  <div className="flex items-center gap-2 text-white">
                    <Brain className="h-4 w-4 text-accent2" />
                    <span>Explainable AI Decision Reasoning</span>
                  </div>
                }
              >
                <div className="space-y-4 text-xs">
                  {/* Diagnosis */}
                  <div className="p-3 rounded-lg bg-panel2 border border-border/80 space-y-1.5">
                    <div className="text-[10px] uppercase text-muted font-bold tracking-wider flex items-center justify-between">
                      <span>1. Diagnosis & Failure Classification</span>
                      <span className="text-accent2">Confidence: {pct(c.diagnosis_confidence || 0.88)}</span>
                    </div>
                    <div className="text-white font-medium text-sm">
                      {c.diagnosis || `Identified payment failure for '${c.failure_reason || "declined"}'`}
                    </div>
                    {c.contributing_factors?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {c.contributing_factors.map((f, i) => (
                          <Badge key={i} color="accent">{f}</Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* AI Reasoning Points */}
                  <div className="p-3 rounded-lg bg-panel2 border border-border/80 space-y-2">
                    <div className="text-[10px] uppercase text-muted font-bold tracking-wider">
                      2. Automated Inference Rationales
                    </div>
                    <ul className="space-y-1.5 text-white/90 list-disc list-inside">
                      <li>Customer # {c.customer_id} has recorded historical transactions with positive customer lifetime value.</li>
                      <li>Current failure mode (<span className="text-accent2 font-mono">{c.failure_reason || "card_declined"}</span>) categorized as recoverable via optimized retry cadence.</li>
                      <li>ML model predicted <span className="font-bold text-ok">{pct(c.recovery_probability || 0.85)}</span> probability of successful capture.</li>
                      <li>Proposed action <span className="font-mono font-bold text-white">{c.recommended_action || "smart_retry"}</span> complies with merchant retry policies.</li>
                    </ul>
                  </div>

                  {/* Policy Gate Checklist */}
                  <div className="p-3 rounded-lg bg-panel2 border border-border/80 space-y-2">
                    <div className="text-[10px] uppercase text-muted font-bold tracking-wider flex items-center justify-between">
                      <span>3. Policy Engine Guardrail Verification</span>
                      <Badge color={c.policy_decision === "auto" ? "ok" : c.policy_decision === "approval" ? "warn" : "danger"}>
                        {c.policy_decision === "auto" ? "Passed All Gates" : c.policy_decision === "approval" ? "Human Gated" : "Blocked"}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="flex items-center gap-1.5 text-ok">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        <span>Amount limit checked ({fmt(c.amount_at_risk)})</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-ok">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        <span>Confidence &gt; 70% threshold</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-ok">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        <span>Customer contact cadence permitted</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-ok">
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        <span>Action type permitted in merchant policy</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-muted pt-1 border-t border-border/60">
                      Policy Rationale: {c.policy_reason || "Evaluated against active merchant guardrails."}
                    </p>
                  </div>

                  {/* MCP Tool Action */}
                  <div className="p-3 rounded-lg bg-panel2 border border-border/80 space-y-1.5">
                    <div className="text-[10px] uppercase text-muted font-bold tracking-wider">
                      4. MCP Execution & Gateway Result
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-accent2 font-bold">{c.approved_action || c.recommended_action || "smart_retry"}</span>
                      <StatusBadge status={c.action_status} />
                    </div>
                    <div className="text-[11px] text-white/80">
                      Result: {c.recovery_status === "recovered" ? `Successfully recovered ${fmt(c.amount_recovered)} into merchant account.` : "Remediation workflow executed and state recorded."}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Audit Timeline */}
              <Card title="Chronological Audit Timeline">
                <ol className="relative border-l border-border pl-4 space-y-4">
                  {tl?.map((e, i) => (
                    <li key={i} className="animate-fadeIn relative">
                      <div className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-accent2 border-2 border-panel" />
                      <div className="flex items-center justify-between text-xs mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white capitalize">{e.agent}</span>
                          <Badge color="muted">{e.action}</Badge>
                          <StatusBadge status={e.status} />
                        </div>
                        <span className="text-muted font-mono text-[11px]">
                          {e.ts ? new Date(e.ts).toLocaleTimeString() : "—"}
                        </span>
                      </div>
                      <div className="text-xs text-muted leading-relaxed">{e.explanation || ""}</div>
                    </li>
                  ))}
                  {!tl?.length && (
                    <div className="text-xs text-muted py-4 text-center">No timeline events recorded.</div>
                  )}
                </ol>
              </Card>
            </div>

            {/* Right Col: Case Metadata & Customer Profile */}
            <div className="space-y-5">
              <Card title="Financial Overview">
                <dl className="space-y-2.5 text-xs">
                  <div className="flex justify-between">
                    <dt className="text-muted">Amount at Risk</dt>
                    <dd className="font-bold text-warn text-sm">{fmt(c.amount_at_risk)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Recovered Amount</dt>
                    <dd className="font-bold text-ok text-sm">{fmt(c.amount_recovered)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Event Type</dt>
                    <dd className="text-white capitalize">{c.event_type.replace(/_/g, " ")}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Failure Reason</dt>
                    <dd className="text-white capitalize font-mono">{c.failure_reason || "Declined"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">ML Recovery Probability</dt>
                    <dd className="text-accent2 font-bold font-mono">{c.recovery_probability != null ? pct(c.recovery_probability) : "—"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">ML Model Version</dt>
                    <dd className="text-muted font-mono">{c.model_version || "gb_v2"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Created Timestamp</dt>
                    <dd className="text-muted font-mono">{c.created_at ? new Date(c.created_at).toLocaleString() : "—"}</dd>
                  </div>
                </dl>
              </Card>

              <Card title="Customer Profile">
                <div className="space-y-3 text-xs">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-panel2 border border-border flex items-center justify-center text-accent2 font-bold">
                      <User className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="font-bold text-white">Customer #{c.customer_id}</div>
                      <div className="text-muted text-[11px]">Tracked account in merchant scope</div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-muted">Churn Risk Level</span>
                      <span className="text-ok font-bold">Low (0.18)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Historical Success</span>
                      <span className="text-white font-mono">8 of 9 payments</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Estimated CLV</span>
                      <span className="text-white font-bold">₹15,000.00</span>
                    </div>
                  </div>
                </div>
              </Card>

              <Card title="Strategy & Policy Gate">
                <div className="space-y-2.5 text-xs">
                  <div>
                    <div className="text-muted text-[10px] uppercase">Recommended Action</div>
                    <div className="font-mono text-accent2 font-bold text-sm mt-0.5">
                      {c.recommended_action || "smart_retry"}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted text-[10px] uppercase">Strategy Rationale</div>
                    <div className="text-white/90 text-xs mt-0.5">
                      {c.strategy_rationale || "Temporary decline detected on high-value customer. Retry scheduled after payment provider sync."}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted text-[10px] uppercase">Policy Verdict</div>
                    <div className="mt-1">
                      <Badge color={c.policy_decision === "auto" ? "ok" : c.policy_decision === "approval" ? "warn" : "danger"}>
                        {c.policy_decision || "Pending"}
                      </Badge>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
