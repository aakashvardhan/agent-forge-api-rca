import { SubmitAnalysis } from "@/components/SubmitAnalysis";
import { IncidentDetail } from "@/components/IncidentDetail";
import { useIncidents } from "@/hooks/use-incidents";
import { Card, CardContent } from "@/components/ui/card";
import { Cpu, Search, Wrench } from "lucide-react";

export default function Analyze() {
  const { selectedIncident, submitEndpoint } = useIncidents();

  const handleSubmit = (url: string, method: string) => {
    submitEndpoint(url, method);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">New Analysis</h1>
        <p className="text-sm text-muted-foreground mt-1">Submit an API endpoint for root cause analysis</p>
      </div>

      <SubmitAnalysis onSubmit={handleSubmit} />

      {/* Pipeline info */}
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { icon: Search, label: "Monitor Agent", desc: "Detects anomalies in real-time metrics" },
          { icon: Cpu, label: "Diagnostic Agent", desc: "Correlates signals to find root cause" },
          { icon: Wrench, label: "Remediation Agent", desc: "Generates actionable fix recommendations" },
        ].map((agent) => (
          <Card key={agent.label} className="glass">
            <CardContent className="flex items-start gap-3 p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <agent.icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{agent.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{agent.desc}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Show latest result */}
      {selectedIncident && (
        <div>
          <h2 className="text-lg font-bold text-foreground mb-3">Latest Result</h2>
          <IncidentDetail incident={selectedIncident} />
        </div>
      )}
    </div>
  );
}
