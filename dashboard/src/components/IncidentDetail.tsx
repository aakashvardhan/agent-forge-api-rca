import { AlertTriangle, Bot, CheckCircle2, ChevronRight, Clock, Gauge, Search, Wrench } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { StatusBadge, SeverityBadge } from "./StatusBadge";
import type { Incident } from "@/lib/types";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Props {
  incident: Incident;
}

export function IncidentDetail({ incident }: Props) {
  const rca = incident.rootCause;

  return (
    <motion.div
      key={incident.id}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="space-y-5"
    >
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-muted-foreground">{incident.id}</span>
          <StatusBadge status={incident.status} />
          <SeverityBadge severity={incident.severity} />
        </div>
        <h2 className="text-lg font-bold text-foreground leading-tight">
          <span className="font-mono text-primary mr-2">{incident.method}</span>
          {incident.endpoint}
        </h2>
        <p className="text-sm text-muted-foreground">{incident.summary}</p>
      </div>

      {/* Status: Pending / Analyzing */}
      {!rca && (
        <Card className="glass border-primary/20">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            {incident.status === "pending" && (
              <>
                <Clock className="h-10 w-10 text-warning mb-3 animate-pulse-slow" />
                <p className="text-sm font-semibold text-foreground">Queued for Analysis</p>
                <p className="text-xs text-muted-foreground mt-1">Waiting for agent pipeline...</p>
              </>
            )}
            {incident.status === "analyzing" && (
              <>
                <Bot className="h-10 w-10 text-primary mb-3 animate-pulse-slow" />
                <p className="text-sm font-semibold text-foreground">Agents Analyzing...</p>
                <p className="text-xs text-muted-foreground mt-1">Running diagnostic pipeline</p>
                <Progress value={45} className="mt-4 w-48 h-2" />
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Root Cause Analysis Results */}
      {rca && (
        <>
          {/* Confidence */}
          <Card className="glass border-accent/20 glow-accent">
            <CardContent className="flex items-center gap-4 py-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent/10">
                <Gauge className="h-6 w-6 text-accent" />
              </div>
              <div className="flex-1">
                <p className="text-xs text-muted-foreground font-medium">Analysis Confidence</p>
                <p className="text-2xl font-bold text-foreground">{rca.confidence}%</p>
              </div>
              <Progress value={rca.confidence} className="w-24 h-2" />
            </CardContent>
          </Card>

          {/* Anomalies */}
          <Card className="glass">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Search className="h-4 w-4 text-primary" />
                Anomalies Detected
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {rca.anomalies.map((anomaly, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-3">
                  <AlertTriangle className={cn("h-4 w-4 mt-0.5 shrink-0", anomaly.severity === "critical" ? "text-destructive" : anomaly.severity === "high" ? "text-warning" : "text-primary")} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-foreground">{anomaly.type}</span>
                      <SeverityBadge severity={anomaly.severity} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      <span className="font-medium">{anomaly.metric}:</span> Expected {anomaly.expected}, got{" "}
                      <span className="font-mono font-semibold text-destructive">{anomaly.actual}</span>
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Diagnosis */}
          <Card className="glass">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Bot className="h-4 w-4 text-primary" />
                Root Cause Diagnosis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-muted-foreground">{rca.diagnosis}</p>
            </CardContent>
          </Card>

          {/* Remediation */}
          <Card className="glass">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Wrench className="h-4 w-4 text-accent" />
                Remediation Steps
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2">
                {rca.remediationSteps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/10 text-[10px] font-bold text-accent">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground">{step}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          {/* Agent Trace */}
          <Card className="glass">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Bot className="h-4 w-4 text-primary" />
                Agent Execution Trace
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {rca.agentTrace.map((step, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                        <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                      </div>
                      {i < rca.agentTrace.length - 1 && <div className="w-px flex-1 bg-border mt-1 min-h-[16px]" />}
                    </div>
                    <div className="pb-2">
                      <p className="text-xs font-semibold text-foreground">{step.agent}</p>
                      <p className="text-xs text-muted-foreground">{step.action}</p>
                      <p className="text-xs text-primary flex items-center gap-1 mt-0.5">
                        <ChevronRight className="h-3 w-3" />
                        {step.result}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </motion.div>
  );
}
