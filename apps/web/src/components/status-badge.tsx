const PALETTE: Record<string, string> = {
  // generic positive / live
  LIVE: "border-emerald-200 bg-emerald-50 text-emerald-700",
  ACTIVE: "border-emerald-200 bg-emerald-50 text-emerald-700",
  AVAILABLE: "border-emerald-200 bg-emerald-50 text-emerald-700",
  COMPLETED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  PASSED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  APPROVED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  DISPATCHED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  APPLIED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  SUCCESS: "border-emerald-200 bg-emerald-50 text-emerald-700",
  RESOLVED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  // demo / mock
  MOCK: "border-violet-200 bg-violet-50 text-violet-700",
  MODIFIED: "border-violet-200 bg-violet-50 text-violet-700",
  // neutral / not configured
  NOT_CONFIGURED: "border-slate-200 bg-slate-100 text-slate-600",
  UNVERIFIED: "border-slate-300 bg-slate-100 text-slate-700",
  DISABLED: "border-slate-200 bg-slate-100 text-slate-600",
  DEPRECATED: "border-slate-200 bg-slate-100 text-slate-600",
  DRAFT: "border-slate-200 bg-slate-100 text-slate-600",
  PENDING: "border-amber-200 bg-amber-50 text-amber-700",
  READY: "border-amber-200 bg-amber-50 text-amber-700",
  // in progress
  PLANNING: "border-blue-200 bg-blue-50 text-blue-700",
  ASSEMBLING: "border-blue-200 bg-blue-50 text-blue-700",
  RUNNING: "border-blue-200 bg-blue-50 text-blue-700",
  ASSIGNED: "border-blue-200 bg-blue-50 text-blue-700",
  VERIFYING: "border-blue-200 bg-blue-50 text-blue-700",
  IN_PROGRESS: "border-blue-200 bg-blue-50 text-blue-700",
  OPEN: "border-blue-200 bg-blue-50 text-blue-700",
  NO_AGENT_AVAILABLE: "border-amber-200 bg-amber-50 text-amber-700",
  // needs attention / blocked
  WAITING_APPROVAL: "border-amber-200 bg-amber-50 text-amber-700",
  PARTIAL: "border-amber-200 bg-amber-50 text-amber-700",
  // negative / failed
  FAILED: "border-rose-200 bg-rose-50 text-rose-700",
  CANCELLED: "border-rose-200 bg-rose-50 text-rose-700",
  REJECTED: "border-rose-200 bg-rose-50 text-rose-700",
  FAILURE: "border-rose-200 bg-rose-50 text-rose-700",
};

const DEFAULT_STYLE = "border-slate-200 bg-slate-100 text-slate-600";

export function StatusBadge({ status, className = "" }: { status: string; className?: string }) {
  const style = PALETTE[status] ?? DEFAULT_STYLE;
  return (
    <span className={`inline-flex rounded border px-2 py-1 text-xs font-semibold ${style} ${className}`}>
      {status}
    </span>
  );
}
