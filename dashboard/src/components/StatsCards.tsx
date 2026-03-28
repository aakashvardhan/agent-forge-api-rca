import { Activity, AlertTriangle, CheckCircle2, Clock, Gauge, Monitor } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { usePolling } from "@/hooks/use-polling";
import { api } from "@/lib/api-client";
import { motion } from "framer-motion";

export function StatsCards() {
  const { data } = usePolling({ fetcher: api.getStats, interval: 5000 });

  const stats = [
    { label: "Total Incidents", value: data?.totalIncidents ?? 0, icon: AlertTriangle, color: "text-destructive" },
    { label: "Active Now", value: data?.activeIncidents ?? 0, icon: Activity, color: "text-warning" },
    { label: "Resolved Today", value: data?.resolvedToday ?? 0, icon: CheckCircle2, color: "text-success" },
    { label: "Avg MTTR", value: data?.mttr ?? "N/A", icon: Clock, color: "text-primary" },
    { label: "Avg Confidence", value: data?.avgConfidence ? `${data.avgConfidence}%` : "—", icon: Gauge, color: "text-accent" },
    { label: "APIs Monitored", value: data?.apisMonitored ?? 0, icon: Monitor, color: "text-primary" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
        >
          <Card className="glass">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <stat.icon className={`h-5 w-5 mb-2 ${stat.color}`} />
              <p className="text-xl font-bold text-foreground">{stat.value}</p>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mt-1">{stat.label}</p>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
