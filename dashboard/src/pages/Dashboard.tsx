import { StatsCards } from "@/components/StatsCards";
import { HealthCharts } from "@/components/HealthCharts";
import { IncidentList } from "@/components/IncidentList";
import { IncidentDetail } from "@/components/IncidentDetail";
import { SubmitAnalysis } from "@/components/SubmitAnalysis";
import { useIncidents } from "@/hooks/use-incidents";

export default function Dashboard() {
  const { incidents, selectedIncident, selectedId, setSelectedId, submitEndpoint } = useIncidents();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Real-time API health monitoring & root cause analysis</p>
      </div>

      <StatsCards />
      <SubmitAnalysis onSubmit={submitEndpoint} />
      <HealthCharts />

      <div>
        <h2 className="text-lg font-bold text-foreground mb-3">Recent Incidents</h2>
        {incidents.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-muted-foreground">
            <p className="text-sm font-medium">No incidents detected yet</p>
            <p className="text-xs mt-1">Enable chaos mode or submit an endpoint above to generate incidents</p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
            <IncidentList incidents={incidents} selectedId={selectedId} onSelect={setSelectedId} />
            <div className="lg:sticky lg:top-4 lg:self-start">
              {selectedIncident ? (
                <IncidentDetail incident={selectedIncident} />
              ) : (
                <div className="flex items-center justify-center rounded-xl border border-dashed border-border p-12 text-sm text-muted-foreground">
                  Select an incident to view details
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
