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

  async function startRazorpayRecovery() {
    if (!c?.payment_id) return;
    try {
      const order = await api.post<{ payment_id: number; razorpay_order_id: string; amount: number; currency: string; key_id: string; name: string; description: string }>(`/payments/${c.payment_id}/razorpay/order`, {});
      await loadRazorpayScript();
      const Razorpay = (window as any).Razorpay;
      if (!Razorpay) throw new Error("Razorpay Checkout could not be loaded");
      const rzp = new Razorpay({
        key: order.key_id,
        amount: Math.round(order.amount * 100),
        currency: order.currency,
        name: order.name,
        description: order.description,
        order_id: order.razorpay_order_id,
        handler: async (response: any) => {
          try {
            await api.post(`/payments/${c.payment_id}/razorpay/verify`, response);
            alert("Payment successful and verified by RecoverAI.");
            window.location.reload();
          } catch (err: any) {
            alert(`Payment verification failed: ${err.message || "Unknown error"}`);
          }
        },
      });
      rzp.on("payment.failed", (response: any) => alert(`Payment failed: ${response?.error?.description || "Payment failed"}`));
      rzp.open();
    } catch (err: any) {
      alert(`Unable to start Razorpay Checkout: ${err.message || "Unknown error"}`);
    }
  }

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
              {c.payment_id && c.recovery_status === "open" && (
                <div className="mt-3">
                  <button className="btn-primary" onClick={startRazorpayRecovery}>₹ Pay with Razorpay</button>
                </div>
              )}
              {c.policy_decision === "approval" && c.recovery_status !== "recovered" && (
  <div className="flex gap-2 mt-3">
    <button
      className="btn-primary"
      onClick={() => approve("success")}
    >
      Approve & Recover
    </button>

    <button
      className="btn-ghost"
      onClick={() => approve("failure")}
    >
      Approve & Fail
    </button>
  </div>
)}

{c.recovery_status === "recovered" && (
  <div className="mt-4 rounded-xl border border-green-500/50 bg-green-500/10 px-5 py-4">
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-green-400 text-black font-bold">
        ✓
      </div>

      <div>
        <div className="text-lg font-semibold text-green-400">
          Recovered
        </div>

        <div className="text-sm text-green-300">
          Recovery of ₹{Number(c.amount_recovered || 0).toLocaleString("en-IN")} completed successfully.
        </div>
      </div>
    </div>
  </div>
)}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function loadRazorpayScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).Razorpay) return resolve();
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Razorpay Checkout"));
    document.body.appendChild(script);
  });
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}
