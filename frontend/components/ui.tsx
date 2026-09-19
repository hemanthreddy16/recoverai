"use client";
import { ReactNode, useEffect, useState } from "react";
import {
  Search,
  Eye,
  Brain,
  Cpu,
  ShieldAlert,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export function Badge({ children, color = "muted" }: { children: ReactNode; color?: string }) {
  const colors: Record<string, string> = {
    muted: "bg-panel2 text-muted border border-border",
    ok: "bg-ok/15 text-ok border border-ok/30",
    warn: "bg-warn/15 text-warn border border-warn/30",
    danger: "bg-danger/15 text-danger border border-danger/30",
    accent: "bg-accent2/15 text-accent2 border border-accent2/30",
    blue: "bg-accent/15 text-accent border border-accent/30",
  };
  return <span className={`badge ${colors[color] || colors.muted}`}>{children}</span>;
}

export function statusColor(s: string | null | undefined): string {
  if (!s) return "muted";
  s = s.toLowerCase();
  if (s === "recovered" || s === "ok" || s === "auto" || s === "success" || s === "completed" || s === "active" || s === "connected") return "ok";
  if (s === "open" || s === "pending" || s === "running" || s === "approval" || s === "waiting_for_approval") return "warn";
  if (s === "failed" || s === "error" || s === "denied" || s === "stopped" || s === "blocked") return "danger";
  return "muted";
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  return <Badge color={statusColor(status)}>{status ? status.replace(/_/g, " ") : "—"}</Badge>;
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}

export function Card({
  title,
  subtitle,
  children,
  className = "",
  headerRight,
  action,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  className?: string;
  headerRight?: ReactNode;
  action?: ReactNode;
}) {
  const right = headerRight || action;
  return (
    <div className={`card ${className}`}>
      {(title || subtitle || right) && (
        <div className="flex items-start sm:items-center justify-between gap-2 text-sm font-semibold text-white/90 mb-3.5 pb-2 border-b border-border/50">
          <div>
            {title && <div>{title}</div>}
            {subtitle && <p className="text-xs text-muted font-normal mt-0.5">{subtitle}</p>}
          </div>
          {right && <div>{right}</div>}
        </div>
      )}
      {children}
    </div>
  );
}


export function Kpi({
  label,
  value,
  sub,
  color = "text-white",
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="kpi relative overflow-hidden group hover:border-accent2/30 transition-colors">
      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted">
        <span>{label}</span>
        {icon && <span className="text-muted/60 group-hover:text-accent2 transition-colors">{icon}</span>}
      </div>
      <div className={`text-2xl font-bold mt-1 tracking-tight ${color}`}>{value}</div>
      {sub && <div className="text-xs text-muted/80 mt-1">{sub}</div>}
    </div>
  );
}

export function LivePipelineVisualizer({
  activeStep = 0,
  stepDetails,
}: {
  activeStep?: number;
  stepDetails?: Record<string, { status: string; detail: string }>;
}) {
  const steps = [
    { key: "detect", name: "Detect", agent: "Detection Agent", icon: Eye },
    { key: "diagnose", name: "Diagnose", agent: "Diagnosis Agent", icon: Search },
    { key: "predict", name: "Predict", agent: "Prediction ML", icon: Brain },
    { key: "strategy", name: "Strategy", agent: "Strategy Agent", icon: Cpu },
    { key: "policy", name: "Policy", agent: "Policy Engine", icon: ShieldAlert },
    { key: "recover", name: "Recover", agent: "Recovery Agent", icon: Play },
    { key: "verify", name: "Verify", agent: "Verification", icon: CheckCircle2 },
  ];

  return (
    <div className="w-full py-2">
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {steps.map((s, idx) => {
          const Icon = s.icon;
          const isDone = idx < activeStep;
          const isCurrent = idx === activeStep;
          const info = stepDetails?.[s.key];

          let stateColor = "border-border bg-panel2 text-muted";
          if (isDone) stateColor = "border-ok/40 bg-ok/10 text-ok";
          if (isCurrent) stateColor = "border-accent2 bg-accent2/10 text-accent2 shadow-md shadow-accent2/10";

          return (
            <div
              key={s.key}
              className={`p-3 rounded-lg border flex flex-col justify-between transition-all duration-300 ${stateColor}`}
            >
              <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                <span className="text-[10px] font-bold opacity-75">0{idx + 1}</span>
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider">{s.name}</div>
                <div className="text-[10px] opacity-75 truncate">{s.agent}</div>
              </div>
              <div className="mt-2 text-[10px] pt-1 border-t border-current/10 truncate font-mono">
                {info ? info.detail : isDone ? "✓ Complete" : isCurrent ? "Active →" : "Idle"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function useAsync<T>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fn()
      .then((d) => active && setData(d))
      .catch((e) => active && setError(String(e.message || e)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refetch: () => fn().then(setData) };
}
