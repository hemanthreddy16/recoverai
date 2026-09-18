"use client";

import { useState } from "react";
import {
  ScrollText,
  Search,
  Filter,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUpDown,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAsync, Card, PageHeader, StatusBadge, Badge } from "@/components/ui";
import type { AuditLog } from "@/lib/types";

export default function AuditPage() {
  const [query, setQuery] = useState("");
  const [selectedAction, setSelectedAction] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data, loading, refetch } = useAsync<AuditLog[]>(
    () => api.get("/audit?limit=200"),
    []
  );

  const filteredLogs = (data || []).filter((log) => {
    if (selectedAction !== "all" && !log.action.toLowerCase().includes(selectedAction.toLowerCase())) {
      return false;
    }
    if (selectedStatus !== "all" && log.status.toLowerCase() !== selectedStatus.toLowerCase()) {
      return false;
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      return (
        log.actor.toLowerCase().includes(q) ||
        log.action.toLowerCase().includes(q) ||
        log.details.toLowerCase().includes(q) ||
        String(log.entity_id || "").includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Trail & System Ledger"
        subtitle="Immutable, cryptographically verifiable log of all agent runs, policy evaluations, and MCP tool invocations"
        action={
          <button onClick={() => refetch()} className="btn-ghost flex items-center gap-1.5 text-xs">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh Log
          </button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="sm:col-span-2 relative">
          <Search className="h-4 w-4 text-muted absolute left-3 top-2.5" />
          <input
            className="input pl-9 text-xs"
            placeholder="Search by actor, action, case ID, or payload detail..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div>
          <select
            className="input text-xs"
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
          >
            <option value="all">All Action Types</option>
            <option value="detect">Detect Actions</option>
            <option value="policy">Policy Evaluations</option>
            <option value="recovery">Recovery Invocations</option>
            <option value="approve">Human Approvals</option>
            <option value="verify">Verifications</option>
          </select>
        </div>

        <div>
          <select
            className="input text-xs"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="success">Success / OK</option>
            <option value="denied">Policy Denied</option>
            <option value="error">Failed / Error</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-muted border-b border-border bg-panel2/50 text-[11px] uppercase tracking-wider">
                <th className="th">Timestamp</th>
                <th className="th">Actor / Agent</th>
                <th className="th">Action</th>
                <th className="th">Entity</th>
                <th className="th">Status</th>
                <th className="th">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-xs">
              {filteredLogs.map((log) => {
                const isExpanded = expandedId === log.id;
                let parsedDetail: any = null;
                try {
                  parsedDetail = JSON.parse(log.details);
                } catch {
                  parsedDetail = log.details;
                }

                return (
                  <tr
                    key={log.id}
                    onClick={() => setExpandedId(isExpanded ? null : log.id)}
                    className="hover:bg-panel2/40 cursor-pointer transition-colors"
                  >
                    <td className="td text-muted font-mono whitespace-nowrap">
                      {log.created_at ? new Date(log.created_at).toLocaleTimeString() : "—"}
                    </td>
                    <td className="td font-semibold text-white">
                      <span className="capitalize">{log.actor.replace(/_/g, " ")}</span>
                    </td>
                    <td className="td font-mono text-accent2">
                      {log.action}
                    </td>
                    <td className="td text-muted">
                      {log.entity_type ? `${log.entity_type} #${log.entity_id ?? "—"}` : "—"}
                    </td>
                    <td className="td">
                      <StatusBadge status={log.status} />
                    </td>
                    <td className="td max-w-xs truncate text-muted">
                      {typeof parsedDetail === "object" ? JSON.stringify(parsedDetail) : String(parsedDetail)}
                    </td>
                  </tr>
                );
              })}
              {!loading && filteredLogs.length === 0 && (
                <tr>
                  <td className="td text-muted text-center py-8" colSpan={6}>
                    No audit records matching criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Expanded detail panel if selected */}
      {expandedId && (
        <Card
          title={`Audit Log Record #${expandedId}`}
          headerRight={
            <button
              onClick={() => setExpandedId(null)}
              className="text-xs text-muted hover:text-white"
            >
              Close ✕
            </button>
          }
        >
          {(() => {
            const log = data?.find((l) => l.id === expandedId);
            if (!log) return null;
            return (
              <div className="space-y-3 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <div className="text-muted text-[10px] uppercase">Actor</div>
                    <div className="font-bold text-white mt-0.5">{log.actor} (ID: {log.actor_id ?? "system"})</div>
                  </div>
                  <div>
                    <div className="text-muted text-[10px] uppercase">Action</div>
                    <div className="font-mono text-accent2 mt-0.5">{log.action}</div>
                  </div>
                  <div>
                    <div className="text-muted text-[10px] uppercase">Timestamp</div>
                    <div className="font-mono text-white mt-0.5">{log.created_at ? new Date(log.created_at).toLocaleString() : "—"}</div>
                  </div>
                  <div>
                    <div className="text-muted text-[10px] uppercase">Status</div>
                    <div className="mt-0.5"><StatusBadge status={log.status} /></div>
                  </div>
                </div>

                <div>
                  <div className="text-muted text-[10px] uppercase mb-1">Payload Details (JSON)</div>
                  <pre className="p-3 rounded bg-panel2 border border-border/80 text-accent2 font-mono overflow-x-auto text-[11px]">
                    {(() => {
                      try {
                        return JSON.stringify(JSON.parse(log.details), null, 2);
                      } catch {
                        return log.details;
                      }
                    })()}
                  </pre>
                </div>
              </div>
            );
          })()}
        </Card>
      )}
    </div>
  );
}
