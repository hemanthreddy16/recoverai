"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync, Card, PageHeader, Kpi } from "@/components/ui";
import type { Policy } from "@/lib/types";

export default function SettingsPage() {
  const { data, loading, error } = useAsync<Policy>(() => api.get("/settings/policy"), []);
  const [form, setForm] = useState<Policy | null>(null);
  const [saved, setSaved] = useState(false);

  if (data && !form) setForm(data);
  const p = form;

  async function save() {
    if (!p) return;
    await api.patch("/settings/policy", p);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Merchant policy — the guardrails every recovery action must pass" />
      {loading && <div className="text-muted">Loading…</div>}
      {error && <div className="text-danger">Failed to load policy.</div>}
      {p && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <Kpi label="Auto Threshold" value={p.automatic_threshold.toFixed(2)} sub="prob ≥ → automatic" />
            <Kpi label="Approval Threshold" value={p.approval_threshold.toFixed(2)} />
            <Kpi label="Retry Limit" value={String(p.retry_limit)} />
            <Kpi label="High-Value" value={`₹${p.high_value_threshold}`} sub="≥ → human approval" />
          </div>
          <Card className="space-y-4 max-w-3xl">
            <Field label="Automatic threshold (0–1)">
              <input type="number" step="0.01" className="input" value={p.automatic_threshold}
                onChange={(e) => setForm({ ...p, automatic_threshold: Number(e.target.value) })} />
            </Field>
            <Field label="Approval threshold (0–1)">
              <input type="number" step="0.01" className="input" value={p.approval_threshold}
                onChange={(e) => setForm({ ...p, approval_threshold: Number(e.target.value) })} />
            </Field>
            <Field label="Retry limit">
              <input type="number" className="input" value={p.retry_limit}
                onChange={(e) => setForm({ ...p, retry_limit: Number(e.target.value) })} />
            </Field>
            <Field label="Max recovery attempts">
              <input type="number" className="input" value={p.max_recovery_attempts}
                onChange={(e) => setForm({ ...p, max_recovery_attempts: Number(e.target.value) })} />
            </Field>
            <Field label="High-value threshold (₹)">
              <input type="number" className="input" value={p.high_value_threshold}
                onChange={(e) => setForm({ ...p, high_value_threshold: Number(e.target.value) })} />
            </Field>
            <Toggle label="Allow auto retry" v={p.allow_auto_retry} on={(v) => setForm({ ...p, allow_auto_retry: v })} />
            <Toggle label="Allow auto payment link" v={p.allow_auto_payment_link} on={(v) => setForm({ ...p, allow_auto_payment_link: v })} />
            <Toggle label="Allow auto notification" v={p.allow_auto_notification} on={(v) => setForm({ ...p, allow_auto_notification: v })} />
            <div className="flex items-center gap-3 pt-2">
              <button className="btn-primary" onClick={save}>Save policy</button>
              {saved && <span className="text-ok text-sm">Saved ✓</span>}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 items-center gap-3">
      <label className="text-sm text-muted col-span-1">{label}</label>
      <div className="col-span-2">{children}</div>
    </div>
  );
}

function Toggle({ label, v, on }: { label: string; v: boolean; on: (v: boolean) => void }) {
  return (
    <div className="grid grid-cols-3 items-center gap-3">
      <label className="text-sm text-muted col-span-1">{label}</label>
      <button
        className={`col-span-2 btn-ghost w-16 ${v ? "text-ok border-ok/40" : "text-muted"}`}
        onClick={() => on(!v)}
      >
        {v ? "ON" : "OFF"}
      </button>
    </div>
  );
}
