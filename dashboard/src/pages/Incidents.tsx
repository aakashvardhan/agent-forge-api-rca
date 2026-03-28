import { IncidentList } from "@/components/IncidentList";
import { IncidentDetail } from "@/components/IncidentDetail";
import { useIncidents } from "@/hooks/use-incidents";

export default function Incidents() {
  const { incidents, selectedIncident, selectedId, setSelectedId } = useIncidents();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Incidents</h1>
        <p className="text-sm text-muted-foreground mt-1">All API incidents and root cause analyses</p>
      </div>
      {incidents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-muted-foreground">
          <p className="text-sm font-medium">No incidents detected yet</p>
          <p className="text-xs mt-1">Incidents will appear as anomalies are detected by the backend</p>
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
  );
}
