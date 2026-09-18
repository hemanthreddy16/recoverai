"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync, Card, PageHeader, StatusBadge, Badge } from "@/components/ui";
import { fmt, pct } from "@/lib/api";
import type { CaseDetail, TimelineEvent } from "@/lib/types";

export default function CaseDetailPage({ params }: { params: { id: string } }) {
  const caseId = Number(params.id);
  const [approved, setApproved] = useState(false);
  const { data: c, loading } = useAsync<CaseDetail>(() => api.get(`/cases/${caseId}`), [caseId, approved]);
  const { data: tl } = useAsync<TimelineEvent[]>(() => api.get(`/cases/${caseId}/timeline`), [caseId, approved]);

  async function approve(outcome: string) {
    await api.post(`/cases/${caseId}/approve`, { simulated_outcome: outcome });
    setApproved((v) => !v);
  }

  return (
    <div>
      <PageHeader title={`Case #${caseId}`} subtitle="Full agent + policy + MCP audit trail" />
      {loading && <div className="text-muted">Loading…</div>}
      {c && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <Card title="Audit Timeline">
              <ol className="relative border-l border-border pl-4 space-y-4">
                {tl?.map((e, i) => (
                  <li key={i} className="animate-fadeIn">
                    <div className="absolute -left-[5px] h-2.5 w-2.5 rounded-full bg-accent2" />
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{e.agent}</span>
                      <Badge color="muted">{e.action}</Badge>
                      <StatusBadge status={e.status} />
                      <span className="ml-auto text-xs text-muted">{e.ts ? new Date(e.ts).toLocaleTimeString() : ""}</span>
                    </div>
                    <div className="text-sm text-muted mt-1">{e.explanation || ""}</div>
                  </li>
                ))}
                {!tl?.length && <div className="text-sm text-muted">No events.</div>}
              </ol>
            </Card>
          </div>

          <div className="space-y-4">
            <Card title="Case">
              <dl className="space-y-2 text-sm">
                <Row k="Amount at risk" v={fmt(c.amount_at_risk)} />
                <Row k="Customer" v={String(c.customer_id)} />
                <Row k="Payment" v={c.payment_id ? String(c.payment_id) : "—"} />
                <Row k="Event" v={c.event_type} />
                <Row k="Failure reason" v={c.failure_reason || "—"} />
                <Row k="Risk score" v={pct(c.risk_score)} />
                <Row k="Recovery prob." v={c.recovery_probability != null ? pct(c.recovery_probability) : "—"} />
                <Row k="Model" v={c.model_version || "—"} />
              </dl>
            </Card>

            <Card title="AI Diagnosis">
              <p className="text-sm">{c.diagnosis || "—"}</p>
              {c.contributing_factors?.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {c.contributing_factors.map((f, i) => <Badge key={i} color="accent">{f}</Badge>)}
                </div>
              )}
              <div className="text-xs text-muted mt-2">Confidence {pct(c.diagnosis_confidence || 0)}</div>
            </Card>

            <Card title="Strategy & Policy">
              <dl className="space-y-2 text-sm">
                <Row k="Recommended" v={c.recommended_action || "—"} />
                <Row k="Policy" v={c.policy_decision || "—"} />
                <Row k="Approved" v={c.approved_action || "—"} />
                <Row k="Action status" v={c.action_status} />
                <Row k="Recovery" v={c.recovery_status} />
                <Row k="Recovered" v={fmt(c.amount_recovered)} />
              </dl>
              <p className="text-xs text-muted mt-2">{c.policy_reason}</p>
              {c.policy_decision === "approval" && (
                <div className="flex gap-2 mt-3">
                  <button className="btn-primary" onClick={() => approve("success")}>Approve & Recover</button>
                  <button className="btn-ghost" onClick={() => approve("failure")}>Approve & Fail</button>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}
