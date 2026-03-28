import { cn } from "@/lib/utils";
import type { IncidentStatus, Severity } from "@/lib/types";

const statusConfig: Record<IncidentStatus, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-warning/15 text-warning border-warning/30" },
  analyzing: { label: "Analyzing", className: "bg-primary/15 text-primary border-primary/30 animate-pulse-slow" },
  completed: { label: "Completed", className: "bg-success/15 text-success border-success/30" },
  failed: { label: "Failed", className: "bg-destructive/15 text-destructive border-destructive/30" },
};

const severityConfig: Record<Severity, { label: string; className: string }> = {
  critical: { label: "Critical", className: "bg-destructive/15 text-destructive border-destructive/30" },
  high: { label: "High", className: "bg-warning/15 text-warning border-warning/30" },
  medium: { label: "Medium", className: "bg-primary/15 text-primary border-primary/30" },
  low: { label: "Low", className: "bg-muted text-muted-foreground border-border" },
};

export function StatusBadge({ status }: { status: IncidentStatus }) {
  const config = statusConfig[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider", config.className)}>
      {status === "analyzing" && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {config.label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const config = severityConfig[severity];
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider", config.className)}>
      {config.label}
    </span>
  );
}
