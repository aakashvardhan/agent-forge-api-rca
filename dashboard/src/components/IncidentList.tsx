import { formatDistanceToNow } from "date-fns";
import { Clock, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge, SeverityBadge } from "./StatusBadge";
import type { Incident } from "@/lib/types";
import { motion } from "framer-motion";

interface Props {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function IncidentList({ incidents, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {incidents.map((incident, i) => (
        <motion.button
          key={incident.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(incident.id)}
          className={cn(
            "group w-full rounded-xl border p-4 text-left transition-all duration-200",
            selectedId === incident.id
              ? "border-primary/40 bg-primary/5 glow-primary"
              : "border-border bg-card hover:border-primary/20 hover:bg-card/80"
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
                <StatusBadge status={incident.status} />
                <SeverityBadge severity={incident.severity} />
              </div>
              <p className="truncate text-sm font-medium text-foreground">
                <span className="font-mono text-xs text-primary mr-1.5">{incident.method}</span>
                {incident.endpoint}
              </p>
              <p className="mt-1 truncate text-xs text-muted-foreground">{incident.summary}</p>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(new Date(incident.timestamp), { addSuffix: true })}
            </span>
            {incident.responseTime > 0 && (
              <span className="flex items-center gap-1">
                <Zap className="h-3 w-3" />
                {incident.responseTime}ms
              </span>
            )}
            {incident.statusCode > 0 && (
              <span className={cn("font-mono font-semibold", incident.statusCode >= 500 ? "text-destructive" : incident.statusCode >= 400 ? "text-warning" : "text-success")}>
                {incident.statusCode}
              </span>
            )}
          </div>
        </motion.button>
      ))}
    </div>
  );
}
