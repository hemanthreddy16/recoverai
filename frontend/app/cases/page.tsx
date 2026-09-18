"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FolderKanban,
  Search,
  Filter,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import { useAsync, Card, PageHeader, StatusBadge, Badge } from "@/components/ui";
import type { Case } from "@/lib/types";

export default function CasesPage() {
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState<string>("");

  const { data, loading } = useAsync<Case[]>(() => api.get("/cases?limit=200"), []);

  const filteredCases = (data || []).filter((c) => {
    // Status filter
    if (filter === "high_risk" && (c.amount_at_risk < 10000 && c.risk_score < 0.6)) return false;
    if (filter === "recoverable" && (c.recovery_probability == null || c.recovery_probability < 0.6)) return false;
    if (filter === "approval" && c.policy_decision !== "approval") return false;
    if (filter === "recovered" && c.recovery_status !== "recovered") return false;
    if (filter === "failed" && c.recovery_status !== "failed") return false;
    if (filter === "blocked" && (c.policy_decision !== "denied" && c.recovery_status !== "stopped")) return false;

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        String(c.id).includes(q) ||
        String(c.customer_id).includes(q) ||
        (c.failure_reason && c.failure_reason.toLowerCase().includes(q)) ||
        (c.recommended_action && c.recommended_action.toLowerCase().includes(q)) ||
        c.event_type.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Revenue Recovery Cases"
        subtitle="Track every at-risk event through diagnosis, ML probability, policy checks, and MCP execution"
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5 items-center">
          {[
            { id: "all", label: "All Cases" },
            { id: "high_risk", label: "High Risk (₹10k+)" },
            { id: "recoverable", label: "Highly Recoverable" },
            { id: "approval", label: "Pending Approval" },
            { id: "recovered", label: "Recovered" },
            { id: "failed", label: "Failed" },
            { id: "blocked", label: "Blocked" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                filter === f.id
                  ? "bg-accent text-white border border-accent"
                  : "bg-panel2 text-muted hover:text-white border border-border"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="h-3.5 w-3.5 text-muted absolute left-3 top-3" />
          <input
            className="input pl-8 text-xs py-1.5"
            placeholder="Search cases, customers, reasons..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Cases Table */}
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                <th className="th">Case ID</th>
                <th className="th">Customer</th>
                <th className="th">Amount at Risk</th>
                <th className="th">Event Type</th>
                <th className="th">Failure Reason</th>
                <th className="th">Recovery Prob.</th>
                <th className="th">Selected Strategy</th>
                <th className="th">Policy Gate</th>
                <th className="th">Recovery Status</th>
                <th className="th text-right">Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-xs">
              {filteredCases.map((c) => (
                <tr key={c.id} className="hover:bg-panel2/40 transition-colors">
                  <td className="td font-mono">
                    <Link
                      href={`/cases/${c.id}`}
                      className="text-accent2 font-bold hover:underline"
                    >
                      #{c.id}
                    </Link>
                  </td>
                  <td className="td text-white font-medium">Customer #{c.customer_id}</td>
                  <td className="td font-bold text-white">{fmt(c.amount_at_risk)}</td>
                  <td className="td text-muted capitalize">{c.event_type.replace(/_/g, " ")}</td>
                  <td className="td text-muted capitalize">{c.failure_reason || "Declined"}</td>
                  <td className="td">
                    {c.recovery_probability != null ? (
                      <span className="font-mono text-accent2 font-bold">
                        {pct(c.recovery_probability)}
                      </span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="td font-mono text-white/90">
                    {c.approved_action || c.recommended_action || "—"}
                  </td>
                  <td className="td">
                    <Badge
                      color={
                        c.policy_decision === "auto"
                          ? "ok"
                          : c.policy_decision === "approval"
                          ? "warn"
                          : "danger"
                      }
                    >
                      {c.policy_decision || "Pending"}
                    </Badge>
                  </td>
                  <td className="td">
                    <StatusBadge status={c.recovery_status} />
                  </td>
                  <td className="td text-right">
                    <Link
                      href={`/cases/${c.id}`}
                      className="btn-ghost text-[11px] py-1 px-2.5 inline-flex items-center gap-1 text-accent2 hover:bg-accent2/10"
                    >
                      Explain <ArrowRight className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              ))}
              {!loading && filteredCases.length === 0 && (
                <tr>
                  <td className="td text-muted text-center py-10" colSpan={10}>
                    No cases match the selected filter.
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
