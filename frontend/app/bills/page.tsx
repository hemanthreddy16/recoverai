"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  Area,
  AreaChart,
  Pie,
  PieChart,
  Cell,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Receipt,
  Plus,
  Search,
  Filter,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Send,
  MessageSquare,
  Eye,
  Edit3,
  Trash2,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Zap,
  Building2,
  Wifi,
  Smartphone,
  Landmark,
  CreditCard,
  FileText,
  HelpCircle,
  X,
  Phone,
  User,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Brain,
  Layers,
  Activity,
  Info,
  ChevronRight,
  History,
  Bell,
  Sliders,
  Moon,
  Mail,
  CheckCheck,
  Timer,
  Forward,
  Check,
} from "lucide-react";
import { api, fmt, pct } from "@/lib/api";
import {
  useAsync,
  Card,
  PageHeader,
  Kpi,
  Badge,
} from "@/components/ui";
import type {
  BillEmi,
  BillEmiSummary,
  BillEmiInput,
  BillReminderSettings,
  UpcomingActionsData,
  ScheduledReminderAction,
  ReminderTimelineStep,
} from "@/lib/types";

const CATEGORIES = [

  "Electricity",
  "Internet",
  "Mobile",
  "Rent",
  "EMI",
  "Insurance",
  "Subscription",
  "Other",
];

const RECURRENCES = ["One-time", "Weekly", "Monthly", "Quarterly", "Yearly"];

const STATUSES = ["Upcoming", "Due Today", "Overdue", "Paid", "Failed"];

const RISKS = ["Low", "Medium", "High"];

const CATEGORY_COLORS: Record<string, string> = {
  Electricity: "#f59e0b",
  Internet: "#3b82f6",
  Mobile: "#06b6d4",
  Rent: "#ec4899",
  EMI: "#ef4444",
  Insurance: "#8b5cf6",
  Subscription: "#10b981",
  Other: "#64748b",
};

function getCategoryIcon(cat: string) {
  switch (cat?.toLowerCase()) {
    case "electricity":
      return <Zap className="h-4 w-4 text-amber-400" />;
    case "internet":
      return <Wifi className="h-4 w-4 text-blue-400" />;
    case "mobile":
      return <Smartphone className="h-4 w-4 text-cyan-400" />;
    case "rent":
      return <Building2 className="h-4 w-4 text-pink-400" />;
    case "emi":
      return <Landmark className="h-4 w-4 text-rose-400" />;
    case "insurance":
      return <ShieldCheck className="h-4 w-4 text-purple-400" />;
    case "subscription":
      return <CreditCard className="h-4 w-4 text-emerald-400" />;
    default:
      return <Receipt className="h-4 w-4 text-muted" />;
  }
}

function getStatusBadge(status: string) {
  switch (status?.toLowerCase()) {
    case "paid":
      return <Badge color="ok">Paid</Badge>;
    case "upcoming":
      return <Badge color="blue">Upcoming</Badge>;
    case "due today":
      return <Badge color="warn">Due Today</Badge>;
    case "overdue":
      return <Badge color="danger">Overdue</Badge>;
    case "failed":
      return <Badge color="danger">Failed</Badge>;
    default:
      return <Badge color="muted">{status || "—"}</Badge>;
  }
}

function getRiskLevelBadge(level: string, score?: number) {
  const norm = (level || "Low").toLowerCase();
  const scoreDisplay = score !== undefined && score !== null ? `${score}/100` : "";

  if (norm === "high") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-danger/15 text-danger border border-danger/30">
        <span className="h-1.5 w-1.5 rounded-full bg-danger animate-pulse2" />
        High {scoreDisplay && <span className="font-mono font-bold">({scoreDisplay})</span>}
      </span>
    );
  }
  if (norm === "medium") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-warn/15 text-warn border border-warn/30">
        <span className="h-1.5 w-1.5 rounded-full bg-warn" />
        Medium {scoreDisplay && <span className="font-mono font-bold">({scoreDisplay})</span>}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-ok/15 text-ok border border-ok/30">
      <span className="h-1.5 w-1.5 rounded-full bg-ok" />
      Low {scoreDisplay && <span className="font-mono font-bold">({scoreDisplay})</span>}
    </span>
  );
}

function getPriorityBadge(priority: string) {
  switch (priority?.toLowerCase()) {
    case "urgent":
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-danger/20 text-danger border border-danger/40 uppercase">Urgent</span>;
    case "high":
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase">High</span>;
    case "medium":
      return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase">Medium</span>;
    default:
      return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/20 text-blue-300 border border-blue-500/40 uppercase">Low</span>;
  }
}

function getStageBadge(stage: string) {
  const s = (stage || "").toLowerCase();
  if (s === "recovery") return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-danger/20 text-danger border border-danger/40">Recovery Alert</span>;
  if (s === "overdue") return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">Overdue Stage</span>;
  if (s === "due_today") return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-warn/20 text-warn border border-warn/40">Due Today</span>;
  if (s === "1-day") return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-400/20 text-amber-300 border border-amber-400/40">1-Day Advance</span>;
  if (s === "3-day") return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-400/20 text-blue-300 border border-blue-400/40">3-Day Notice</span>;
  if (s === "7-day") return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-400/20 text-purple-300 border border-purple-400/40">7-Day Smart</span>;
  return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-panel2 text-muted border border-border">{stage || "Reminder"}</span>;
}

export default function BillsPage() {

  // Filters state
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [dateRangeFilter, setDateRangeFilter] = useState("all");

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [editingBill, setEditingBill] = useState<BillEmi | null>(null);
  const [detailBill, setDetailBill] = useState<BillEmi | null>(null);
  const [whatsAppBill, setWhatsAppBill] = useState<BillEmi | null>(null);
  const [deleteConfirmBill, setDeleteConfirmBill] = useState<BillEmi | null>(null);

  // Timeline & Upcoming State
  const [billTimeline, setBillTimeline] = useState<ReminderTimelineStep[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);

  // Form states
  const [formData, setFormData] = useState<BillEmiInput>({
    name: "",
    category: "Electricity",
    amount: 1000,
    currency: "INR",
    due_date: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 16),
    recurrence: "Monthly",
    customer_name: "",
    customer_phone: "",
    customer_email: "",
    payment_link: "",
    notes: "",
    status: "Upcoming",
    risk_level: "Low",
  });
  const [customWaMsg, setCustomWaMsg] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [notificationToast, setNotificationToast] = useState<string | null>(null);

  // Fetch summary & bills list
  const { data: summary, loading: summaryLoading, refetch: refetchSummary } = useAsync<BillEmiSummary>(
    () => api.get("/bills/summary"),
    []
  );

  // Fetch upcoming actions & reminder settings
  const { data: upcomingActions, loading: actionsLoading, refetch: refetchUpcomingActions } = useAsync<UpcomingActionsData>(
    () => api.get("/bills/reminders/upcoming-actions"),
    []
  );

  const { data: reminderSettings, loading: settingsLoading, refetch: refetchSettings } = useAsync<BillReminderSettings>(
    () => api.get("/bills/reminders/settings"),
    []
  );

  const [settingsForm, setSettingsForm] = useState<Partial<BillReminderSettings>>({});

  const queryParams = new URLSearchParams();
  if (categoryFilter !== "all") queryParams.set("category", categoryFilter);
  if (statusFilter !== "all") queryParams.set("status", statusFilter);
  if (riskFilter !== "all") queryParams.set("risk_level", riskFilter);
  if (dateRangeFilter !== "all") queryParams.set("date_range", dateRangeFilter);
  if (search.trim()) queryParams.set("search", search.trim());

  const { data: bills, loading: billsLoading, refetch: refetchBills } = useAsync<BillEmi[]>(
    () => api.get(`/bills?${queryParams.toString()}`),
    [categoryFilter, statusFilter, riskFilter, dateRangeFilter, search]
  );

  function showToast(msg: string) {
    setNotificationToast(msg);
    setTimeout(() => setNotificationToast(null), 4500);
  }

  async function openDetailModal(bill: BillEmi) {
    setDetailBill(bill);
    setTimelineLoading(true);
    try {
      const timeline = await api.get<ReminderTimelineStep[]>(`/bills/${bill.id}/timeline`);
      setBillTimeline(timeline || []);
    } catch {
      setBillTimeline([]);
    } finally {
      setTimelineLoading(false);
    }
  }

  function openSettingsModal() {
    if (reminderSettings) {
      setSettingsForm({
        reminders_enabled: reminderSettings.reminders_enabled,
        frequency: reminderSettings.frequency,
        max_reminders: reminderSettings.max_reminders,
        preferred_channel: reminderSettings.preferred_channel,
        quiet_hours_enabled: reminderSettings.quiet_hours_enabled,
        quiet_hours_start: reminderSettings.quiet_hours_start || "22:00",
        quiet_hours_end: reminderSettings.quiet_hours_end || "08:00",
        risk_multiplier_enabled: reminderSettings.risk_multiplier_enabled,
      });
    }
    setIsSettingsOpen(true);
  }

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    setActionLoading(true);
    try {
      await api.put("/bills/reminders/settings", settingsForm);
      showToast("Smart Payment Reminder configuration saved successfully.");
      setIsSettingsOpen(false);
      await Promise.all([refetchSettings(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Failed to save reminder settings: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDispatchSmartQueue() {
    setIsDispatching(true);
    try {
      const res = await api.post<{ dispatched_count: number; message: string }>("/bills/reminders/evaluate-and-dispatch", {});
      showToast(res.message || `Dispatched ${res.dispatched_count} reminders across active gateways.`);
      await Promise.all([refetchUpcomingActions(), refetchBills(), refetchSummary()]);
    } catch (err: any) {
      alert(`Dispatch error: ${err.message || "Unknown error"}`);
    } finally {
      setIsDispatching(false);
    }
  }


  async function handleCreateOrUpdate(e: React.FormEvent) {
    e.preventDefault();
    setActionLoading(true);
    try {
      if (editingBill) {
        await api.patch(`/bills/${editingBill.id}`, formData);
        showToast(`Successfully updated '${formData.name}' with AI risk re-evaluation`);
      } else {
        await api.post("/bills", formData);
        showToast(`Successfully added '${formData.name}' with AI risk score calculation`);
      }
      setIsCreateOpen(false);
      setEditingBill(null);
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Error saving bill: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRecalculateSingle(billId: number) {
    setActionLoading(true);
    try {
      const updated = await api.post<BillEmi>(`/bills/${billId}/recalculate-risk`, {});
      showToast(`Recalculated AI risk for '${updated.name}': ${updated.risk_score}/100 (${updated.risk_level})`);
      if (detailBill?.id === billId) {
        setDetailBill(updated);
        const timeline = await api.get<ReminderTimelineStep[]>(`/bills/${billId}/timeline`);
        setBillTimeline(timeline || []);
      }
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Failed to recalculate risk: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleBatchRecalculate() {
    setActionLoading(true);
    try {
      const res = await api.post<{ status: string; recalculated_count: number }>("/bills/recalculate-all-risk", {});
      showToast(`AI engine updated risk scores for all ${res.recalculated_count} recurring obligations.`);
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Batch risk recalculation failed: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleMarkPaid(bill: BillEmi) {
    setActionLoading(true);
    try {
      await api.post(`/bills/${bill.id}/mark-paid`, {});
      showToast(`Marked '${bill.name}' as Paid. Risk score reduced to minimal.`);
      if (detailBill?.id === bill.id) {
        const updated = await api.get<BillEmi>(`/bills/${bill.id}`);
        setDetailBill(updated);
        const timeline = await api.get<ReminderTimelineStep[]>(`/bills/${bill.id}/timeline`);
        setBillTimeline(timeline || []);
      }
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Failed to mark bill as paid: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDelete(bill: BillEmi) {
    setActionLoading(true);
    try {
      await api.delete(`/bills/${bill.id}`);
      showToast(`Deleted obligation '${bill.name}'`);
      setDeleteConfirmBill(null);
      if (detailBill?.id === bill.id) setDetailBill(null);
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Failed to delete: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSendWhatsApp(bill: BillEmi) {
    setActionLoading(true);
    try {
      const res = await api.post<{
        status: string;
        message: string;
        whatsapp_direct_url: string;
        rendered_message: string;
      }>(`/bills/${bill.id}/send-whatsapp`, {
        custom_message: customWaMsg.trim() || undefined,
        include_payment_link: true,
      });

      showToast(`WhatsApp reminder dispatched & logged to communication audit.`);
      
      if (res.whatsapp_direct_url) {
        window.open(res.whatsapp_direct_url, "_blank");
      }

      setWhatsAppBill(null);
      setCustomWaMsg("");
      if (detailBill?.id === bill.id) {
        const updated = await api.get<BillEmi>(`/bills/${bill.id}`);
        setDetailBill(updated);
        const timeline = await api.get<ReminderTimelineStep[]>(`/bills/${bill.id}/timeline`);
        setBillTimeline(timeline || []);
      }
      await Promise.all([refetchBills(), refetchSummary(), refetchUpcomingActions()]);
    } catch (err: any) {
      alert(`Failed to send WhatsApp reminder: ${err.message || "Unknown error"}`);
    } finally {
      setActionLoading(false);
    }
  }

  function openCreateModal() {

    setEditingBill(null);
    setFormData({
      name: "",
      category: "Electricity",
      amount: 5000,
      currency: "INR",
      due_date: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 16),
      recurrence: "Monthly",
      customer_name: "",
      customer_phone: "",
      customer_email: "",
      payment_link: "",
      notes: "",
      status: "Upcoming",
      risk_level: "Low",
    });
    setIsCreateOpen(true);
  }

  function openEditModal(b: BillEmi) {
    setEditingBill(b);
    setFormData({
      name: b.name,
      category: b.category,
      amount: b.amount,
      currency: b.currency,
      due_date: b.due_date ? new Date(b.due_date).toISOString().slice(0, 16) : "",
      recurrence: b.recurrence,
      customer_name: b.customer_name,
      customer_phone: b.customer_phone,
      customer_email: b.customer_email || "",
      payment_link: b.payment_link || "",
      notes: b.notes || "",
      status: b.status,
      risk_level: b.risk_level,
    });
    setIsCreateOpen(true);
  }

  function openWhatsAppModal(b: BillEmi) {
    setWhatsAppBill(b);
    const dueStr = new Date(b.due_date).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    const link = b.payment_link || `https://pay.resurge.dev/bill/${b.id}`;
    setCustomWaMsg(
      `Hello ${b.customer_name}, this is a reminder from Resurge regarding your ${b.category} payment '${b.name}' of ${fmt(b.amount)} due on ${dueStr}. Please complete your payment securely at: ${link}`
    );
  }

  // Chart data formatting
  const upcomingVsOverdueData = summary?.upcoming_vs_overdue
    ? [
        {
          name: "Upcoming Due",
          Amount: summary.upcoming_vs_overdue.upcoming_amount,
          Count: summary.upcoming_vs_overdue.upcoming_count,
        },
        {
          name: "Overdue",
          Amount: summary.upcoming_vs_overdue.overdue_amount,
          Count: summary.upcoming_vs_overdue.overdue_count,
        },
        {
          name: "Paid Settled",
          Amount: summary.upcoming_vs_overdue.paid_amount,
          Count: summary.upcoming_vs_overdue.paid_count,
        },
      ]
    : [];

  const categoryPieData = summary?.category_breakdown?.map((c) => ({
    name: c.category,
    value: c.amount,
    count: c.count,
    color: CATEGORY_COLORS[c.category] || "#64748b",
  })) || [];

  const monthlyTrendData = summary?.monthly_trend || [];

  // Top high risk bills for dedicated section
  const atRiskBills = (bills || [])
    .filter((b) => b.status !== "Paid" && (b.risk_score >= 31 || b.risk_level === "High" || b.risk_level === "Medium"))
    .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  return (
    <div className="space-y-6">
      {/* Notification Toast */}
      {notificationToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-panel2 border border-accent2/50 text-white px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 animate-fadeIn">
          <CheckCircle2 className="h-5 w-5 text-accent2" />
          <span className="text-sm font-medium">{notificationToast}</span>
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title="Bills & EMIs Obligation Center"
        subtitle="Manage recurring utility bills, leases, EMIs, insurance premiums & autonomous payment recoveries"
        action={
          <div className="flex items-center gap-2.5">
            <button
              onClick={openSettingsModal}
              className="btn-ghost text-xs flex items-center gap-1.5 text-accent border-accent/30 hover:bg-accent/10"
              title="Configure Smart Reminder Engine & Quiet Hours"
            >
              <Sliders className="h-3.5 w-3.5 text-accent" />
              Reminder Engine Config
            </button>
            <button
              onClick={handleBatchRecalculate}
              disabled={actionLoading}
              className="btn-ghost text-xs flex items-center gap-1.5 text-accent2 border-accent2/30 hover:bg-accent2/10"
              title="Run AI Risk Model across all obligations"
            >
              <Brain className="h-3.5 w-3.5 text-accent2" />
              Run AI Risk Engine
            </button>
            <button
              onClick={() => {
                refetchBills();
                refetchSummary();
                refetchUpcomingActions();
              }}
              className="btn-ghost text-xs flex items-center gap-1.5"
              title="Refresh Telemetry"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Sync
            </button>
            <button
              onClick={openCreateModal}
              className="btn-primary text-xs flex items-center gap-1.5 shadow-md shadow-accent/20"
            >
              <Plus className="h-4 w-4" />
              Add Bill / EMI
            </button>
          </div>
        }
      />

      {/* Top 6 KPI Cards */}
      {summaryLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="kpi animate-pulse bg-panel2/60 h-24" />
          ))}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <Kpi
            label="Total Upcoming"
            value={String(summary.total_upcoming_count)}
            sub="Active recurring bills"
            color="text-white"
            icon={<Receipt className="h-4 w-4" />}
          />
          <Kpi
            label="Total Amount Due"
            value={fmt(summary.total_amount_due)}
            sub="Upcoming obligations"
            color="text-accent2"
            icon={<CreditCard className="h-4 w-4" />}
          />
          <Kpi
            label="Due Today"
            value={String(summary.due_today_count)}
            sub={fmt(summary.due_today_amount)}
            color={summary.due_today_count > 0 ? "text-warn" : "text-white"}
            icon={<Clock className="h-4 w-4" />}
          />
          <Kpi
            label="Due in 7 Days"
            value={String(summary.due_7_days_count)}
            sub={fmt(summary.due_7_days_amount)}
            color="text-ok"
            icon={<Calendar className="h-4 w-4" />}
          />
          <Kpi
            label="Overdue Payments"
            value={String(summary.overdue_count)}
            sub={fmt(summary.overdue_amount)}
            color={summary.overdue_count > 0 ? "text-danger" : "text-white"}
            icon={<AlertTriangle className="h-4 w-4" />}
          />
          <Kpi
            label="High-Risk (AI 71-100)"
            value={String(summary.risk_summary?.high_risk_count ?? summary.high_risk_count)}
            sub={fmt(summary.risk_summary?.high_risk_amount ?? summary.high_risk_amount)}
            color="text-danger"
            icon={<ShieldAlert className="h-4 w-4 text-danger" />}
          />
        </div>
      )}

      {/* SMART PAYMENT REMINDER ENGINE & UPCOMING ACTIONS HERO CARD */}
      <Card
        title="Smart Payment Reminder Engine · Scheduled Actions Queue"
        subtitle="Autonomous timing logic factoring due dates, AI risk velocity, anti-spam limits & quiet hours"
        action={
          <div className="flex items-center gap-2.5">
            {reminderSettings && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-panel2 border border-border">
                <span className={`h-2 w-2 rounded-full ${reminderSettings.reminders_enabled ? "bg-ok" : "bg-muted"}`} />
                {reminderSettings.reminders_enabled ? "Engine Active" : "Paused"} ·{" "}
                <span className="capitalize text-accent2">{reminderSettings.frequency} Mode</span>
              </span>
            )}
            <button
              onClick={handleDispatchSmartQueue}
              disabled={isDispatching || !upcomingActions?.scheduled_count}
              className="btn bg-accent/20 text-accent border border-accent/40 hover:bg-accent/30 text-xs flex items-center gap-1.5 disabled:opacity-50"
            >
              <Send className={`h-3.5 w-3.5 ${isDispatching ? "animate-spin" : ""}`} />
              {isDispatching ? "Dispatching..." : "Dispatch Smart Queue"}
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Reminder Telemetry Counters */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-panel2/80 border border-border">
              <div className="text-[11px] text-muted uppercase font-semibold flex items-center gap-1.5">
                <Timer className="h-3.5 w-3.5 text-accent2" /> Scheduled in Queue
              </div>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {upcomingActions?.scheduled_count ?? 0}
              </div>
              <div className="text-[10px] text-muted mt-0.5">Pending dispatch criteria</div>
            </div>

            <div className="p-3 rounded-lg bg-panel2/80 border border-border">
              <div className="text-[11px] text-muted uppercase font-semibold flex items-center gap-1.5">
                <CheckCheck className="h-3.5 w-3.5 text-blue-400" /> Reminders Dispatched
              </div>
              <div className="text-xl font-bold font-mono text-blue-400 mt-1">
                {upcomingActions?.sent_count ?? 0}
              </div>
              <div className="text-[10px] text-muted mt-0.5">Across WhatsApp, Email, SMS</div>
            </div>

            <div className="p-3 rounded-lg bg-panel2/80 border border-border">
              <div className="text-[11px] text-muted uppercase font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-ok" /> Recovered via Reminders
              </div>
              <div className="text-xl font-bold font-mono text-ok mt-1">
                {upcomingActions?.recovered_count ?? 0}{" "}
                <span className="text-xs font-normal text-muted">({fmt(upcomingActions?.recovered_amount || 0)})</span>
              </div>
              <div className="text-[10px] text-muted mt-0.5">Obligations settled after nudge</div>
            </div>

            <div className="p-3 rounded-lg bg-panel2/80 border border-border">
              <div className="text-[11px] text-muted uppercase font-semibold flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-purple-400" /> Next Window Trigger
              </div>
              <div className="text-xs font-bold text-white mt-2 truncate font-mono">
                {upcomingActions?.next_action_time
                  ? new Date(upcomingActions.next_action_time).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "All current queues clear"}
              </div>
              <div className="text-[10px] text-muted mt-0.5">Quiet hours: 22:00 – 08:00</div>
            </div>
          </div>

          {/* Action Queue List */}
          {upcomingActions && upcomingActions.queue && upcomingActions.queue.length > 0 ? (
            <div className="overflow-x-auto border border-border rounded-lg bg-panel2/40">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-panel2/80 text-muted uppercase text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Obligation</th>
                    <th className="py-2.5 px-3">Customer Contact</th>
                    <th className="py-2.5 px-3">Target Stage</th>
                    <th className="py-2.5 px-3">Channel</th>
                    <th className="py-2.5 px-3">AI Risk</th>
                    <th className="py-2.5 px-3">Scheduled For</th>
                    <th className="py-2.5 px-3">Smart Trigger Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {upcomingActions.queue.map((item, idx) => (
                    <tr key={idx} className="hover:bg-panel2/60 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-white">
                        <div>{item.bill_name}</div>
                        <div className="text-[10px] font-mono text-accent2">{fmt(item.amount)}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="text-white">{item.customer_name}</div>
                        <div className="text-[10px] text-muted font-mono">{item.customer_phone}</div>
                      </td>
                      <td className="py-2.5 px-3">{getStageBadge(item.stage)}</td>
                      <td className="py-2.5 px-3">
                        <span className="capitalize text-xs font-mono font-semibold px-2 py-0.5 rounded bg-panel border border-border text-white">
                          {item.channel}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{getRiskLevelBadge(item.risk_level, item.risk_score)}</td>
                      <td className="py-2.5 px-3 font-mono text-muted text-[11px]">
                        {new Date(item.scheduled_for).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-muted text-[11px]">
                        <div className="flex items-center gap-1.5">
                          {getPriorityBadge(item.priority)}
                          <span className="truncate max-w-xs text-white/80">{item.reason}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-6 border border-dashed border-border rounded-lg bg-panel2/20 text-muted text-xs">
              <CheckCircle2 className="h-6 w-6 text-ok mx-auto mb-1.5 opacity-80" />
              All reminder stages up to date. No pending automated actions required right now.
            </div>
          )}
        </div>
      </Card>


      {/* DEDICATED PAYMENT RISK INTELLIGENCE SECTION */}
      <div className="rounded-xl border border-border bg-panel p-5 space-y-4">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center text-accent2 shadow-sm">
              <Brain className="h-4 w-4" />
            </div>
            <div>
              <div className="text-base font-bold text-white flex items-center gap-2">
                AI Payment Risk Prediction Intelligence
                <span className="text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded bg-accent2/20 text-accent2 border border-accent2/30">
                  Calibrated (0–100)
                </span>
              </div>
              <div className="text-xs text-muted">
                Probabilistic failure estimation evaluating past customer declines, late payment velocity, amount scale & deadlines
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleBatchRecalculate}
              disabled={actionLoading}
              className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 hover:border-accent2/50"
            >
              <Sparkles className="h-3.5 w-3.5 text-accent2" />
              Recalculate Scores
            </button>
          </div>
        </div>

        {/* AI Disclaimer Notice */}
        <div className="p-3 rounded-lg bg-panel2/70 border border-border/80 flex items-start gap-2.5 text-xs text-muted">
          <Info className="h-4 w-4 text-accent2 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="text-white/90">AI Risk Model Notice:</strong> Risk scores and levels (
            <span className="text-ok font-semibold">Low: 0–30</span>,{" "}
            <span className="text-warn font-semibold">Medium: 31–70</span>,{" "}
            <span className="text-danger font-semibold">High: 71–100</span>
            ) are probabilistic AI-generated estimates based on customer failure telemetry and upcoming schedules.
            Predictions are indicative and non-guaranteed.
          </div>
        </div>

        {/* 4-Column Risk Summary Cards */}
        {summary?.risk_summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {/* Total Amount at Risk */}
            <div className="p-4 rounded-xl bg-panel2 border border-danger/30 relative overflow-hidden group hover:border-danger/50 transition-colors">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted">
                <span>Total Amount at Risk</span>
                <ShieldAlert className="h-4 w-4 text-danger" />
              </div>
              <div className="text-2xl font-bold mt-1 text-danger font-mono">
                {fmt(summary.risk_summary.total_amount_at_risk)}
              </div>
              <div className="text-xs text-muted mt-1">High + Medium risk obligations</div>
            </div>

            {/* High-Risk Payments */}
            <div className="p-4 rounded-xl bg-panel2 border border-border relative overflow-hidden group hover:border-danger/30 transition-colors">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted">
                <span>High-Risk (71–100)</span>
                <span className="badge bg-danger/15 text-danger border border-danger/30 font-bold">
                  {summary.risk_summary.high_risk_count} bills
                </span>
              </div>
              <div className="text-2xl font-bold mt-1 text-white font-mono">
                {fmt(summary.risk_summary.high_risk_amount)}
              </div>
              <div className="text-xs text-danger font-medium mt-1">Immediate intervention recommended</div>
            </div>

            {/* Medium-Risk Payments */}
            <div className="p-4 rounded-xl bg-panel2 border border-border relative overflow-hidden group hover:border-warn/30 transition-colors">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted">
                <span>Medium-Risk (31–70)</span>
                <span className="badge bg-warn/15 text-warn border border-warn/30 font-bold">
                  {summary.risk_summary.medium_risk_count} bills
                </span>
              </div>
              <div className="text-2xl font-bold mt-1 text-white font-mono">
                {fmt(summary.risk_summary.medium_risk_amount)}
              </div>
              <div className="text-xs text-warn font-medium mt-1">Requires pre-due reminder</div>
            </div>

            {/* Low-Risk Payments */}
            <div className="p-4 rounded-xl bg-panel2 border border-border relative overflow-hidden group hover:border-ok/30 transition-colors">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted">
                <span>Low-Risk (0–30)</span>
                <span className="badge bg-ok/15 text-ok border border-ok/30 font-bold">
                  {summary.risk_summary.low_risk_count} bills
                </span>
              </div>
              <div className="text-2xl font-bold mt-1 text-ok font-mono">
                {fmt(summary.risk_summary.low_risk_amount)}
              </div>
              <div className="text-xs text-muted mt-1">Healthy settlement probability</div>
            </div>
          </div>
        )}

        {/* Top At-Risk Priority Obligations Carousel / Cards */}
        {atRiskBills.length > 0 && (
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-warn" />
                Priority At-Risk Obligations Ranked by AI Risk Score
              </span>
              <span className="text-muted font-normal text-[11px]">
                Showing {Math.min(3, atRiskBills.length)} highest risk obligations
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {atRiskBills.slice(0, 3).map((b) => (
                <div
                  key={b.id}
                  className="p-3.5 rounded-xl border border-border/90 bg-panel2/60 hover:border-accent2/40 transition-all flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white truncate hover:text-accent2 cursor-pointer" onClick={() => setDetailBill(b)}>
                        {b.name}
                      </span>
                      {getRiskLevelBadge(b.risk_level, b.risk_score)}
                    </div>
                    <div className="text-sm font-bold text-accent2 font-mono mt-1">
                      {fmt(b.amount)} <span className="text-[11px] text-muted font-normal">· {b.category}</span>
                    </div>

                    {/* Main Reason Tag */}
                    <div className="mt-2 p-2 rounded bg-panel border border-border/70 text-[11px] text-white/90 flex items-start gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-accent2 shrink-0 mt-0.5" />
                      <span className="leading-tight">
                        <strong className="text-accent2">Risk Driver: </strong>
                        {b.risk_reason || "Approaching deadline with high liability"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-border/50 text-[11px]">
                    <span className="text-muted">
                      {b.days_overdue > 0 ? (
                        <span className="text-danger font-semibold">{b.days_overdue}d overdue</span>
                      ) : b.days_remaining === 0 ? (
                        <span className="text-warn font-semibold">Due today</span>
                      ) : (
                        <span>Due in {b.days_remaining}d</span>
                      )}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => openWhatsAppModal(b)}
                        className="btn-ghost py-1 px-2 text-[10px] text-ok border-ok/30 hover:bg-ok/10 flex items-center gap-1"
                      >
                        <MessageSquare className="h-3 w-3" /> WhatsApp
                      </button>
                      <button
                        onClick={() => setDetailBill(b)}
                        className="btn-ghost py-1 px-2 text-[10px] text-accent2 hover:bg-accent2/10"
                      >
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Analytical Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart 1: Upcoming vs Overdue */}
        <Card title="Upcoming vs Overdue Obligations">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={upcomingVsOverdueData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <CartesianGrid stroke="#1e2733" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="#8a97a8" fontSize={11} />
                <YAxis stroke="#8a97a8" fontSize={11} tickFormatter={(v) => fmt(v)} />
                <Tooltip
                  contentStyle={{
                    background: "#0f141d",
                    border: "1px solid #1e2733",
                    borderRadius: "8px",
                  }}
                  formatter={(v: any) => [fmt(Number(v)), "Amount"]}
                />
                <Bar dataKey="Amount" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                  {upcomingVsOverdueData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={index === 0 ? "#3b82f6" : index === 1 ? "#ef4444" : "#22c55e"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Chart 2: Payments by Category */}
        <Card title="Payments by Category Breakdown">
          <div className="h-56 flex flex-col sm:flex-row items-center justify-between">
            <div className="h-full w-full sm:w-1/2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={38}
                    outerRadius={68}
                    paddingAngle={3}
                  >
                    {categoryPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#0f141d",
                      border: "1px solid #1e2733",
                      borderRadius: "8px",
                    }}
                    formatter={(v: any) => [fmt(Number(v)), "Total Amount"]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full sm:w-1/2 max-h-48 overflow-y-auto space-y-1.5 text-xs pr-1">
              {categoryPieData.map((cat) => (
                <div key={cat.name} className="flex items-center justify-between p-1.5 rounded bg-panel2/50">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                    <span className="text-white/90 truncate">{cat.name}</span>
                  </div>
                  <span className="font-mono text-muted shrink-0">{fmt(cat.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Chart 3: Monthly Payment Projection */}
        <Card title="Monthly Payment Trajectory">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthlyTrendData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="dueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="paidGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1e2733" strokeDasharray="3 3" />
                <XAxis dataKey="month" stroke="#8a97a8" fontSize={11} />
                <YAxis stroke="#8a97a8" fontSize={11} tickFormatter={(v) => fmt(v)} />
                <Tooltip
                  contentStyle={{
                    background: "#0f141d",
                    border: "1px solid #1e2733",
                    borderRadius: "8px",
                  }}
                  formatter={(v: any, name: string) => [fmt(Number(v)), name]}
                />
                <Area
                  type="monotone"
                  dataKey="due_amount"
                  stroke="#3b82f6"
                  fill="url(#dueGrad)"
                  strokeWidth={2}
                  name="Due Amount"
                />
                <Area
                  type="monotone"
                  dataKey="paid_amount"
                  stroke="#22c55e"
                  fill="url(#paidGrad)"
                  strokeWidth={2}
                  name="Paid Settled"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="space-y-3 bg-panel p-4 rounded-xl border border-border">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[260px]">
            <Search className="h-3.5 w-3.5 text-muted absolute left-3 top-3" />
            <input
              className="input pl-8 text-xs py-2"
              placeholder="Search by bill name, customer, phone number, risk reason..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Quick Date Range Filter Buttons */}
          <div className="flex flex-wrap gap-1.5 items-center">
            {[
              { id: "all", label: "All Dates" },
              { id: "today", label: "Due Today" },
              { id: "7days", label: "Next 7 Days" },
              { id: "month", label: "This Month" },
              { id: "overdue", label: "Overdue Only" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setDateRangeFilter(f.id)}
                className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition-colors ${
                  dateRangeFilter === f.id
                    ? "bg-accent text-white border border-accent"
                    : "bg-panel2 text-muted hover:text-white border border-border"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Secondary Category & Status Pills */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pt-2 border-t border-border/50 text-xs">
          {/* Category Selector */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            <span className="text-muted text-[11px] uppercase font-semibold mr-1">Category:</span>
            <button
              onClick={() => setCategoryFilter("all")}
              className={`px-2 py-1 rounded text-xs transition-colors shrink-0 ${
                categoryFilter === "all" ? "bg-accent2/20 text-accent2 font-bold border border-accent2/40" : "text-muted hover:text-white"
              }`}
            >
              All
            </button>
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCategoryFilter(c)}
                className={`px-2 py-1 rounded text-xs transition-colors shrink-0 ${
                  categoryFilter === c ? "bg-accent2/20 text-accent2 font-bold border border-accent2/40" : "text-muted hover:text-white"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Status & Risk Filters */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-1">
              <span className="text-muted text-[11px] uppercase font-semibold">Status:</span>
              <select
                className="bg-panel2 border border-border text-white text-xs rounded px-2 py-1 outline-none focus:border-accent"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Statuses</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1">
              <span className="text-muted text-[11px] uppercase font-semibold">Risk:</span>
              <select
                className="bg-panel2 border border-border text-white text-xs rounded px-2 py-1 outline-none focus:border-accent"
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
              >
                <option value="all">All Risk</option>
                {RISKS.map((r) => (
                  <option key={r} value={r}>
                    {r} Risk
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Bills & EMIs Table Card with AI Risk Column */}
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-muted border-b border-border bg-panel2/60 text-[11px] uppercase tracking-wider">
                <th className="th">Obligation Name</th>
                <th className="th">Category</th>
                <th className="th">Amount</th>
                <th className="th">Due Date</th>
                <th className="th">Days Timeline</th>
                <th className="th">Status</th>
                <th className="th">AI Payment Risk & Reason</th>
                <th className="th">Customer / Recipient</th>
                <th className="th text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-xs">
              {bills?.map((b) => (
                <tr key={b.id} className="hover:bg-panel2/40 transition-colors">
                  {/* Name */}
                  <td className="td font-medium text-white">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-panel2 border border-border">
                        {getCategoryIcon(b.category)}
                      </div>
                      <div>
                        <button
                          onClick={() => setDetailBill(b)}
                          className="font-bold text-white hover:text-accent2 transition-colors text-left"
                        >
                          {b.name}
                        </button>
                        <div className="text-[11px] text-muted">{b.recurrence} obligation</div>
                      </div>
                    </div>
                  </td>

                  {/* Category */}
                  <td className="td">
                    <span className="badge bg-panel2 text-white/90 border border-border font-medium">
                      {b.category}
                    </span>
                  </td>

                  {/* Amount */}
                  <td className="td font-bold text-white font-mono text-sm">{fmt(b.amount)}</td>

                  {/* Due Date */}
                  <td className="td">
                    <div className="text-white/90 font-medium">
                      {new Date(b.due_date).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </div>
                    <div className="text-[10px] text-muted">
                      {new Date(b.due_date).toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </td>

                  {/* Days Timeline (Calculated) */}
                  <td className="td">
                    {b.status === "Paid" ? (
                      <span className="text-[11px] text-ok font-medium flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Settled
                      </span>
                    ) : b.days_overdue > 0 ? (
                      <span className="badge bg-danger/15 text-danger border border-danger/30 font-bold">
                        {b.days_overdue} {b.days_overdue === 1 ? "day" : "days"} overdue
                      </span>
                    ) : b.days_remaining === 0 ? (
                      <span className="badge bg-warn/15 text-warn border border-warn/30 font-bold animate-pulse2">
                        Due Today
                      </span>
                    ) : (
                      <span className="text-muted font-mono">
                        In <strong className="text-white">{b.days_remaining}</strong> {b.days_remaining === 1 ? "day" : "days"}
                      </span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="td">{getStatusBadge(b.status)}</td>

                  {/* AI Risk Score & Reason Column */}
                  <td className="td max-w-[260px]">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {getRiskLevelBadge(b.risk_level, b.risk_score)}
                      </div>
                      <div className="text-[11px] text-white/80 truncate flex items-center gap-1 font-medium" title={b.risk_reason || "Standard obligation"}>
                        <Sparkles className="h-2.5 w-2.5 text-accent2 shrink-0" />
                        <span className="truncate">{b.risk_reason || "Normal payment cycle"}</span>
                      </div>
                    </div>
                  </td>

                  {/* Customer / Phone */}
                  <td className="td">
                    <div className="text-white font-medium truncate max-w-[130px]">{b.customer_name}</div>
                    <div className="text-[11px] text-muted font-mono flex items-center gap-1">
                      <Phone className="h-2.5 w-2.5" />
                      {b.customer_phone}
                    </div>
                  </td>

                  {/* Actions */}
                  <td className="td text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* WhatsApp Button */}
                      <button
                        onClick={() => openWhatsAppModal(b)}
                        className="btn-ghost py-1 px-2 text-[11px] text-ok border-ok/30 hover:bg-ok/10 flex items-center gap-1"
                        title="Send WhatsApp Reminder"
                      >
                        <MessageSquare className="h-3 w-3 text-ok" />
                        <span className="hidden sm:inline">WhatsApp</span>
                      </button>

                      {/* Mark Paid Button */}
                      {b.status !== "Paid" && (
                        <button
                          onClick={() => handleMarkPaid(b)}
                          className="btn-ghost py-1 px-2 text-[11px] text-accent2 border-accent2/30 hover:bg-accent2/10 flex items-center gap-1"
                          title="Mark as Paid"
                        >
                          <CheckCircle2 className="h-3 w-3" />
                          <span className="hidden sm:inline">Paid</span>
                        </button>
                      )}

                      {/* View Details */}
                      <button
                        onClick={() => setDetailBill(b)}
                        className="btn-ghost p-1.5 text-muted hover:text-white"
                        title="View Complete Details"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>

                      {/* Edit */}
                      <button
                        onClick={() => openEditModal(b)}
                        className="btn-ghost p-1.5 text-muted hover:text-white"
                        title="Edit Obligation"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() => setDeleteConfirmBill(b)}
                        className="btn-ghost p-1.5 text-muted hover:text-danger hover:border-danger/30"
                        title="Delete Obligation"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}

              {billsLoading && (
                <tr>
                  <td className="td text-muted text-center py-10" colSpan={9}>
                    <span className="animate-pulse2 font-mono text-xs">Loading recurring obligations…</span>
                  </td>
                </tr>
              )}

              {!billsLoading && bills?.length === 0 && (
                <tr>
                  <td className="td text-muted text-center py-12" colSpan={9}>
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Receipt className="h-8 w-8 text-muted/50" />
                      <div className="text-sm font-medium text-white/80">No Bills or EMIs found</div>
                      <div className="text-xs text-muted">
                        No obligations match your active filters, or you haven't added one yet.
                      </div>
                      <button onClick={openCreateModal} className="btn-primary text-xs mt-2 flex items-center gap-1">
                        <Plus className="h-3.5 w-3.5" /> Add New Obligation
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* CREATE / EDIT BILL MODAL */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-panel border border-border rounded-xl w-full max-w-xl p-6 shadow-2xl space-y-4 animate-fadeIn my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Receipt className="h-5 w-5 text-accent2" />
                {editingBill ? "Edit Bill / EMI Obligation" : "Add New Bill / EMI Obligation"}
              </h2>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-muted hover:text-white p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateOrUpdate} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* Payment Name */}
                <div className="sm:col-span-2">
                  <label className="block text-muted mb-1 font-medium">Payment / Obligation Name *</label>
                  <input
                    required
                    className="input text-xs py-2"
                    placeholder="e.g. Tata Power Commercial Electricity, Office Lease, HDFC EMI"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                {/* Category */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Category *</label>
                  <select
                    className="input text-xs py-2"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Amount (INR ₹) *</label>
                  <input
                    type="number"
                    min="1"
                    step="any"
                    required
                    className="input text-xs py-2 font-mono"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                {/* Due Date */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Due Date & Time *</label>
                  <input
                    type="datetime-local"
                    required
                    className="input text-xs py-2 font-mono"
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  />
                </div>

                {/* Recurrence */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Recurrence Schedule *</label>
                  <select
                    className="input text-xs py-2"
                    value={formData.recurrence}
                    onChange={(e) => setFormData({ ...formData, recurrence: e.target.value })}
                  >
                    {RECURRENCES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Customer Name */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Customer / Payee Name *</label>
                  <input
                    required
                    className="input text-xs py-2"
                    placeholder="e.g. Rajesh Sharma"
                    value={formData.customer_name}
                    onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                  />
                </div>

                {/* Customer Phone */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Phone Number (WhatsApp) *</label>
                  <input
                    required
                    className="input text-xs py-2 font-mono"
                    placeholder="e.g. 9876543210"
                    value={formData.customer_phone}
                    onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                  />
                </div>

                {/* Customer Email */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Email Address (Optional)</label>
                  <input
                    type="email"
                    className="input text-xs py-2"
                    placeholder="e.g. rajesh@example.com"
                    value={formData.customer_email || ""}
                    onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
                  />
                </div>

                {/* Status */}
                <div>
                  <label className="block text-muted mb-1 font-medium">Status</label>
                  <select
                    className="input text-xs py-2"
                    value={formData.status || "Upcoming"}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Payment Link */}
                <div className="sm:col-span-2">
                  <label className="block text-muted mb-1 font-medium">Payment Link / Gateway URL (Optional)</label>
                  <input
                    type="url"
                    className="input text-xs py-2"
                    placeholder="https://pay.example.com/invoice-link"
                    value={formData.payment_link || ""}
                    onChange={(e) => setFormData({ ...formData, payment_link: e.target.value })}
                  />
                </div>

                {/* Notes */}
                <div className="sm:col-span-2">
                  <label className="block text-muted mb-1 font-medium">Internal Notes & Context</label>
                  <textarea
                    rows={2}
                    className="input text-xs py-2"
                    placeholder="Account number, meter ID, loan account reference or recovery notes..."
                    value={formData.notes || ""}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="btn-ghost text-xs px-4"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="btn-primary text-xs px-5 flex items-center gap-1.5"
                >
                  {actionLoading ? "Saving…" : editingBill ? "Save Changes" : "Create Obligation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SMART REMINDER ENGINE SETTINGS MODAL */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-panel border border-border rounded-xl w-full max-w-lg p-6 shadow-2xl space-y-4 animate-fadeIn my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Sliders className="h-5 w-5 text-accent" />
                Smart Payment Reminder Engine Configuration
              </h2>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="text-muted hover:text-white p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-4 text-xs">
              {/* Master Engine Toggle */}
              <div className="p-3 rounded-lg bg-panel2 border border-border flex items-center justify-between">
                <div>
                  <div className="font-semibold text-white">Enable Automated Payment Reminders</div>
                  <div className="text-[11px] text-muted">Orchestrate risk-aware pre-due and recovery notices</div>
                </div>
                <input
                  type="checkbox"
                  checked={settingsForm.reminders_enabled ?? true}
                  onChange={(e) => setSettingsForm({ ...settingsForm, reminders_enabled: e.target.checked })}
                  className="h-4 w-4 rounded accent-accent"
                />
              </div>

              {/* Reminder Strategy / Frequency */}
              <div>
                <label className="block text-muted mb-1 font-medium">Reminder Cadence & Policy Strategy</label>
                <select
                  className="input text-xs py-2"
                  value={settingsForm.frequency || "smart"}
                  onChange={(e) => setSettingsForm({ ...settingsForm, frequency: e.target.value })}
                >
                  <option value="smart">Smart (AI Risk-Adaptive · Proactive 7-day for High Risk)</option>
                  <option value="conservative">Conservative (Minimal alerts · 3-day & Due Today only)</option>
                  <option value="aggressive">Aggressive (High frequency · 7-day, 3-day, 1-day, Due Date & Daily Overdue)</option>
                </select>
              </div>

              {/* Preferred Gateway Channel */}
              <div>
                <label className="block text-muted mb-1 font-medium">Preferred Communication Channel</label>
                <select
                  className="input text-xs py-2"
                  value={settingsForm.preferred_channel || "whatsapp"}
                  onChange={(e) => setSettingsForm({ ...settingsForm, preferred_channel: e.target.value })}
                >
                  <option value="whatsapp">WhatsApp Business API (Highest Engagement)</option>
                  <option value="email">Email Invoicing Gateway</option>
                  <option value="sms">SMS Text Alert</option>
                  <option value="multi">Multi-Channel Fallback (WhatsApp → Email)</option>
                </select>
              </div>

              {/* Max Reminders Limit */}
              <div>
                <label className="block text-muted mb-1 font-medium">
                  Maximum Reminders Per Obligation Cycle:{" "}
                  <span className="text-white font-mono font-bold">{settingsForm.max_reminders ?? 4}</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="8"
                  value={settingsForm.max_reminders ?? 4}
                  onChange={(e) => setSettingsForm({ ...settingsForm, max_reminders: parseInt(e.target.value) || 4 })}
                  className="w-full accent-accent"
                />
                <span className="text-[10px] text-muted">Anti-spam ceiling: prevents sending more than this limit.</span>
              </div>

              {/* AI Risk Multiplier Toggle */}
              <div className="p-3 rounded-lg bg-panel2 border border-border flex items-center justify-between">
                <div>
                  <div className="font-semibold text-white">AI Risk Proactive Multiplier</div>
                  <div className="text-[11px] text-muted">Advance reminder timelines for high-risk accounts (7-day trigger)</div>
                </div>
                <input
                  type="checkbox"
                  checked={settingsForm.risk_multiplier_enabled ?? true}
                  onChange={(e) => setSettingsForm({ ...settingsForm, risk_multiplier_enabled: e.target.checked })}
                  className="h-4 w-4 rounded accent-accent"
                />
              </div>

              {/* Quiet Hours Window */}
              <div className="p-3.5 rounded-lg bg-panel2 border border-border space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-white flex items-center gap-1.5">
                    <Moon className="h-4 w-4 text-purple-400" />
                    Quiet Hours Compliance
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsForm.quiet_hours_enabled ?? true}
                    onChange={(e) => setSettingsForm({ ...settingsForm, quiet_hours_enabled: e.target.checked })}
                    className="h-4 w-4 rounded accent-accent"
                  />
                </div>
                <p className="text-[11px] text-muted">
                  Suppresses non-emergency dispatches during late evening/early morning. Scheduled reminders are automatically deferred to the active morning window.
                </p>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-muted mb-1 text-[11px]">Quiet Window Start (HH:MM)</label>
                    <input
                      type="text"
                      placeholder="22:00"
                      className="input text-xs py-1.5 font-mono"
                      value={settingsForm.quiet_hours_start || "22:00"}
                      onChange={(e) => setSettingsForm({ ...settingsForm, quiet_hours_start: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-muted mb-1 text-[11px]">Quiet Window End (HH:MM)</label>
                    <input
                      type="text"
                      placeholder="08:00"
                      className="input text-xs py-1.5 font-mono"
                      value={settingsForm.quiet_hours_end || "08:00"}
                      onChange={(e) => setSettingsForm({ ...settingsForm, quiet_hours_end: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="btn-ghost text-xs px-4"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="btn-primary text-xs px-5 flex items-center gap-1.5"
                >
                  {actionLoading ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PAYMENT DETAIL MODAL WITH VISUAL REMINDER TIMELINE */}
      {detailBill && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-panel border border-border rounded-xl w-full max-w-2xl p-6 shadow-2xl space-y-5 animate-fadeIn my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-panel2 border border-border">
                  {getCategoryIcon(detailBill.category)}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">{detailBill.name}</h2>
                  <div className="text-xs text-muted flex items-center gap-2">
                    <span>{detailBill.category}</span>
                    <span>·</span>
                    <span>{detailBill.recurrence}</span>
                    <span>·</span>
                    <span className="font-mono">ID #{detailBill.id}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setDetailBill(null)}
                className="text-muted hover:text-white p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Quick Badges & Amount Banner */}
            <div className="p-4 rounded-xl bg-panel2 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs text-muted uppercase tracking-wider font-semibold">Total Obligation Amount</div>
                <div className="text-2xl font-bold text-white font-mono mt-0.5">{fmt(detailBill.amount)}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {getStatusBadge(detailBill.status)}
                {getRiskLevelBadge(detailBill.risk_level, detailBill.risk_score)}
                {detailBill.days_overdue > 0 ? (
                  <Badge color="danger">{detailBill.days_overdue} Days Overdue</Badge>
                ) : (
                  <Badge color="blue">{detailBill.days_remaining} Days Remaining</Badge>
                )}
              </div>
            </div>

            {/* VISUAL REMINDER & RECOVERY LIFECYCLE TIMELINE */}
            <div className="p-4 rounded-xl bg-panel2/70 border border-border space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Forward className="h-4 w-4 text-accent2" />
                  Smart Reminder & Recovery Lifecycle Timeline
                </div>
                {timelineLoading && (
                  <span className="text-[11px] text-muted flex items-center gap-1">
                    <RefreshCw className="h-3 w-3 animate-spin text-accent2" /> Syncing timeline...
                  </span>
                )}
              </div>

              <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border/80">
                {billTimeline.map((step, idx) => {
                  const isCompleted = step.status === "completed";
                  const isActive = step.status === "active";
                  return (
                    <div key={idx} className="relative group text-xs">
                      {/* Step Indicator Dot */}
                      <span
                        className={`absolute -left-6 top-1 h-4 w-4 rounded-full border flex items-center justify-center ${
                          isCompleted
                            ? "bg-ok border-ok/80 text-black"
                            : isActive
                            ? "bg-danger border-danger animate-pulse2 text-white"
                            : "bg-panel border-muted/50 text-muted"
                        }`}
                      >
                        {isCompleted ? <Check className="h-2.5 w-2.5 stroke-[3]" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
                      </span>

                      <div className="p-2.5 rounded-lg bg-panel border border-border/80 space-y-1">
                        <div className="flex items-center justify-between">
                          <div className="font-semibold text-white flex items-center gap-2">
                            <span>{step.title}</span>
                            {getStageBadge(step.stage)}
                          </div>
                          <span className="text-[10px] text-muted font-mono">
                            {new Date(step.timestamp).toLocaleDateString("en-IN", {
                              day: "numeric",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="text-muted text-[11px]">{step.description}</div>
                        {step.customer_response && step.customer_response !== "pending" && (
                          <div className="text-[10px] text-ok flex items-center gap-1 font-medium pt-0.5">
                            <CheckCheck className="h-3 w-3" /> Customer Action: {step.customer_response.replace("_", " ").toUpperCase()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {!timelineLoading && billTimeline.length === 0 && (
                  <div className="text-muted text-xs py-2">No timeline entries recorded yet.</div>
                )}
              </div>
            </div>

            {/* AI Risk Score Analysis Card */}
            <div className="p-4 rounded-xl bg-panel2/60 border border-accent2/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-white flex items-center gap-2 uppercase tracking-wider">
                  <Brain className="h-4 w-4 text-accent2" />
                  AI Payment Risk Diagnostic
                </div>
                <button
                  onClick={() => handleRecalculateSingle(detailBill.id)}
                  disabled={actionLoading}

                  className="text-xs text-accent2 hover:underline flex items-center gap-1 font-mono"
                >
                  <RefreshCw className="h-3 w-3" /> Re-evaluate Score
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div className="p-2.5 rounded-lg bg-panel border border-border text-xs">
                  <div className="text-muted text-[10px] uppercase font-semibold">AI Risk Score</div>
                  <div className="text-xl font-bold text-white font-mono mt-0.5">
                    {detailBill.risk_score ?? 15} <span className="text-xs text-muted font-normal">/ 100</span>
                  </div>
                  <div className="text-[10px] text-muted capitalize mt-0.5">Level: {detailBill.risk_level}</div>
                </div>

                <div className="sm:col-span-2 p-2.5 rounded-lg bg-panel border border-border text-xs space-y-1">
                  <div className="text-muted text-[10px] uppercase font-semibold">Primary Risk Reason</div>
                  <div className="text-white font-semibold text-xs flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-accent2 shrink-0" />
                    {detailBill.risk_reason || "Normal payment cycle with standard parameters"}
                  </div>
                </div>
              </div>

              {/* Contributing Factors Checklist */}
              {detailBill.risk_factors && detailBill.risk_factors.length > 0 && (
                <div className="pt-2 border-t border-border/50 text-xs">
                  <div className="text-[11px] font-semibold text-muted mb-1.5">Contributing AI Risk Factors:</div>
                  <div className="space-y-1">
                    {detailBill.risk_factors.map((factor, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-white/90 text-[11px]">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent2 shrink-0" />
                        <span>{factor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Detailed Grid Info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-3 p-3.5 rounded-lg bg-panel2/40 border border-border/70">
                <div className="font-bold text-white uppercase tracking-wider text-[11px] pb-1 border-b border-border/50">
                  Obligation Schedule
                </div>
                <div>
                  <span className="text-muted">Due Date: </span>
                  <strong className="text-white">
                    {new Date(detailBill.due_date).toLocaleDateString("en-IN", {
                      weekday: "short",
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </strong>
                </div>
                <div>
                  <span className="text-muted">Recurrence: </span>
                  <strong className="text-white">{detailBill.recurrence}</strong>
                </div>
                {detailBill.paid_at && (
                  <div>
                    <span className="text-muted">Settled / Paid At: </span>
                    <strong className="text-ok">
                      {new Date(detailBill.paid_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </strong>
                  </div>
                )}
                {detailBill.payment_link && (
                  <div>
                    <span className="text-muted block mb-1">Direct Payment URL:</span>
                    <a
                      href={detailBill.payment_link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent2 hover:underline inline-flex items-center gap-1 font-mono break-all"
                    >
                      {detailBill.payment_link} <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>

              <div className="space-y-3 p-3.5 rounded-lg bg-panel2/40 border border-border/70">
                <div className="font-bold text-white uppercase tracking-wider text-[11px] pb-1 border-b border-border/50">
                  Recipient & Contact
                </div>
                <div>
                  <span className="text-muted">Payee / Customer: </span>
                  <strong className="text-white">{detailBill.customer_name}</strong>
                </div>
                <div>
                  <span className="text-muted">Phone (WhatsApp): </span>
                  <strong className="text-white font-mono">{detailBill.customer_phone}</strong>
                </div>
                {detailBill.customer_email && (
                  <div>
                    <span className="text-muted">Email: </span>
                    <strong className="text-white">{detailBill.customer_email}</strong>
                  </div>
                )}
                {detailBill.notes && (
                  <div>
                    <span className="text-muted block mb-1">Notes:</span>
                    <p className="text-white/90 bg-panel p-2 rounded border border-border/50 text-[11px]">
                      {detailBill.notes}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Risk History Timeline & Dispatched Reminders */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Risk Evolution History */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <History className="h-3.5 w-3.5 text-accent2" />
                  Risk Progression Timeline
                </div>
                <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1 text-xs">
                  {detailBill.risk_history?.map((rh) => (
                    <div key={rh.id} className="p-2 rounded bg-panel2 border border-border/70 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-white">Score: {rh.risk_score}/100</span>
                        <span className="text-[10px] text-muted">
                          {rh.evaluated_at ? new Date(rh.evaluated_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" }) : ""}
                        </span>
                      </div>
                      <div className="text-muted text-[10px] truncate">{rh.risk_reason || "Assessment"}</div>
                    </div>
                  ))}
                  {!detailBill.risk_history?.length && (
                    <div className="text-center py-4 text-muted text-[11px] bg-panel2/30 rounded border border-border/40">
                      Initial risk evaluation logged.
                    </div>
                  )}
                </div>
              </div>

              {/* Dispatched WhatsApp Reminders */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <MessageSquare className="h-3.5 w-3.5 text-ok" />
                  Communication Ledger
                </div>
                <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1 text-xs">
                  {detailBill.reminder_logs?.map((log) => (
                    <div key={log.id} className="p-2 rounded bg-panel2 border border-border/70 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="badge bg-ok/15 text-ok border border-ok/30 text-[9px]">WhatsApp</span>
                        <span className="text-[10px] text-muted">
                          {log.sent_at ? new Date(log.sent_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" }) : ""}
                        </span>
                      </div>
                      <div className="text-white/80 text-[10px] truncate font-mono mt-0.5">{log.message}</div>
                    </div>
                  ))}
                  {!detailBill.reminder_logs?.length && (
                    <div className="text-center py-4 text-muted text-[11px] bg-panel2/30 rounded border border-border/40">
                      No WhatsApp reminders dispatched yet.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 pt-3 border-t border-border">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setDetailBill(null);
                    openWhatsAppModal(detailBill);
                  }}
                  className="btn bg-ok/20 text-ok border border-ok/40 hover:bg-ok/30 text-xs flex items-center gap-1.5"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  Dispatch WhatsApp Reminder
                </button>
                {detailBill.status !== "Paid" && (
                  <button
                    onClick={() => handleMarkPaid(detailBill)}
                    className="btn-primary text-xs flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Mark Settled (Paid)
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const b = detailBill;
                    setDetailBill(null);
                    openEditModal(b);
                  }}
                  className="btn-ghost text-xs flex items-center gap-1"
                >
                  <Edit3 className="h-3.5 w-3.5" /> Edit
                </button>
                <button
                  onClick={() => {
                    const b = detailBill;
                    setDetailBill(null);
                    setDeleteConfirmBill(b);
                  }}
                  className="btn-ghost text-xs text-danger hover:bg-danger/10 border-danger/30 flex items-center gap-1"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* WHATSAPP REMINDER DISPATCH MODAL */}
      {whatsAppBill && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel border border-border rounded-xl w-full max-w-lg p-6 shadow-2xl space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-ok" />
                Dispatch WhatsApp Payment Reminder
              </h2>
              <button
                onClick={() => setWhatsAppBill(null)}
                className="text-muted hover:text-white p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-panel2 border border-border flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">{whatsAppBill.name}</div>
                  <div className="text-muted">
                    Recipient: <strong className="text-white">{whatsAppBill.customer_name}</strong> (
                    <span className="font-mono">{whatsAppBill.customer_phone}</span>)
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-accent2 font-mono text-sm">{fmt(whatsAppBill.amount)}</div>
                  <div className="text-[10px] text-muted">
                    Due: {new Date(whatsAppBill.due_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-muted mb-1 font-medium">Personalized WhatsApp Message Template</label>
                <textarea
                  rows={4}
                  className="input text-xs py-2 font-mono"
                  value={customWaMsg}
                  onChange={(e) => setCustomWaMsg(e.target.value)}
                />
                <span className="text-[10px] text-muted mt-1 block">
                  Clicking send will record an audit trail in the Recovery Ledger and open WhatsApp directly.
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
              <button
                type="button"
                onClick={() => setWhatsAppBill(null)}
                className="btn-ghost text-xs px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleSendWhatsApp(whatsAppBill)}
                className="btn bg-ok text-black font-bold hover:bg-ok/90 text-xs px-5 flex items-center gap-1.5"
              >
                <Send className="h-3.5 w-3.5" />
                {actionLoading ? "Dispatching…" : "Dispatch WhatsApp Reminder"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteConfirmBill && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel border border-border rounded-xl w-full max-w-md p-6 shadow-2xl space-y-4 animate-fadeIn">
            <div className="flex items-center gap-3 text-danger">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-bold text-white">Delete Obligation</h3>
            </div>
            <p className="text-xs text-muted leading-relaxed">
              Are you sure you want to delete <strong className="text-white">'{deleteConfirmBill.name}'</strong> of{" "}
              <strong className="text-accent2">{fmt(deleteConfirmBill.amount)}</strong>? This will permanently remove
              this obligation and its reminder logs.
            </p>
            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
              <button
                onClick={() => setDeleteConfirmBill(null)}
                className="btn-ghost text-xs px-4"
              >
                Cancel
              </button>
              <button
                disabled={actionLoading}
                onClick={() => handleDelete(deleteConfirmBill)}
                className="btn bg-danger text-white hover:bg-danger/90 text-xs px-4"
              >
                {actionLoading ? "Deleting…" : "Yes, Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
