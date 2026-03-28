import { HealthCharts } from "@/components/HealthCharts";
import { StatsCards } from "@/components/StatsCards";

export default function Metrics() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Health Metrics</h1>
        <p className="text-sm text-muted-foreground mt-1">API performance and reliability over time</p>
      </div>
      <StatsCards />
      <HealthCharts />
    </div>
  );
}
