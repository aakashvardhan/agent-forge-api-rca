import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Activity, Search, Wrench, ChevronRight, CheckCircle2, ArrowRight, Gauge, Database, Settings2 } from "lucide-react";
import { usePolling } from "@/hooks/use-polling";
import { api, type AgentInfo, type PipelineTrace } from "@/lib/api-client";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useState } from "react";

const AGENT_ICONS: Record<string, typeof Bot> = {
  "Monitor Agent": Search,
  "Diagnostic Agent": Bot,
  "Remediation Agent": Wrench,
};

const AGENT_COLORS: Record<string, string> = {
  "Monitor Agent": "text-primary",
  "Diagnostic Agent": "text-accent",
  "Remediation Agent": "text-warning",
};

const AGENT_BG: Record<string, string> = {
  "Monitor Agent": "bg-primary/10",
  "Diagnostic Agent": "bg-accent/10",
  "Remediation Agent": "bg-warning/10",
};

function AgentCard({ agent, index }: { agent: AgentInfo; index: number }) {
  const Icon = AGENT_ICONS[agent.name] ?? Bot;
  const color = AGENT_COLORS[agent.name] ?? "text-primary";
  const bg = AGENT_BG[agent.name] ?? "bg-primary/10";

  const statLabel = agent.eventsProcessed != null
    ? "Events"
    : agent.diagnosesGenerated != null
    ? "Diagnoses"
    : "Actions";

  const statValue = agent.eventsProcessed
    ?? agent.diagnosesGenerated
    ?? agent.actionsExecuted
    ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card className="glass h-full">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", bg)}>
              <Icon className={cn("h-5 w-5", color)} />
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-semibold uppercase tracking-wider",
                agent.status === "active"
                  ? "bg-success/15 text-success border-success/30"
                  : "bg-muted text-muted-foreground border-border"
              )}
            >
              {agent.status === "active" && (
                <span className="relative mr-1.5 flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
                </span>
              )}
              {agent.status}
            </Badge>
          </div>

          <div>
            <p className="text-sm font-bold text-foreground">{agent.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{agent.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-secondary/50 p-2.5 text-center">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{statLabel}</p>
              <p className="text-lg font-bold font-mono text-foreground">{statValue}</p>
            </div>
            {agent.anomaliesDetected != null && (
              <div className="rounded-lg bg-secondary/50 p-2.5 text-center">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Anomalies</p>
                <p className="text-lg font-bold font-mono text-foreground">{agent.anomaliesDetected}</p>
              </div>
            )}
            {agent.actionBreakdown && (
              <div className="rounded-lg bg-secondary/50 p-2.5 text-center col-span-2">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Breakdown</p>
                <div className="flex items-center justify-center gap-3 text-xs font-mono">
                  <span className="text-destructive">{agent.actionBreakdown.REROUTE ?? 0} R</span>
                  <span className="text-warning">{agent.actionBreakdown.ALERT ?? 0} A</span>
                  <span className="text-success">{agent.actionBreakdown.WAIT ?? 0} W</span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function TraceItem({ trace, index }: { trace: PipelineTrace; index: number }) {
  const [expanded, setExpanded] = useState(index === 0);

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full rounded-xl border p-4 text-left transition-all duration-200",
          expanded
            ? "border-primary/30 bg-primary/5"
            : "border-border bg-card hover:border-primary/20"
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <span className="font-mono text-xs text-muted-foreground">{trace.id}</span>
            <span className="font-mono text-xs text-primary font-semibold">{trace.endpoint}</span>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono whitespace-nowrap ml-3">
            {new Date(trace.timestamp).toLocaleTimeString("en-US", { hour12: false })}
          </span>
        </div>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-4 space-y-3">
                {trace.steps.map((step, i) => {
                  const Icon = AGENT_ICONS[step.agent] ?? Bot;
                  const color = AGENT_COLORS[step.agent] ?? "text-primary";

                  return (
                    <div key={i} className="flex items-start gap-3">
                      <div className="flex flex-col items-center">
                        <div className={cn("flex h-7 w-7 items-center justify-center rounded-full", AGENT_BG[step.agent] ?? "bg-primary/10")}>
                          <CheckCircle2 className={cn("h-3.5 w-3.5", color)} />
                        </div>
                        {i < trace.steps.length - 1 && (
                          <div className="w-px flex-1 bg-border mt-1 min-h-[12px]" />
                        )}
                      </div>
                      <div className="pb-1 min-w-0 flex-1">
                        <p className="text-xs font-semibold text-foreground">{step.agent}</p>
                        <p className="text-[11px] text-muted-foreground">{step.action}</p>
                        <p className="text-[11px] flex items-center gap-1 mt-0.5">
                          <ChevronRight className={cn("h-3 w-3 shrink-0", color)} />
                          <span className={cn("truncate", color)}>{step.result}</span>
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </button>
    </motion.div>
  );
}

export default function AgentPipeline() {
  const { data, error } = usePolling({ fetcher: api.getAgentStatus, interval: 3000 });

  const agents = data?.agents ?? [];
  const pipeline = data?.pipeline;
  const traces = data?.recentTraces ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            Agent Pipeline
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time multi-agent RCA pipeline — Monitor → Diagnose → Remediate
          </p>
        </div>
        {data && (
          <Badge
            variant="outline"
            className={cn(
              "text-xs font-semibold",
              agents.some((a) => a.status === "active")
                ? "bg-success/15 text-success border-success/30"
                : "bg-muted text-muted-foreground"
            )}
          >
            <Activity className="h-3 w-3 mr-1.5" />
            {agents.some((a) => a.status === "active") ? "Pipeline Active" : "Pipeline Idle"}
          </Badge>
        )}
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive font-mono">
          {error}
        </div>
      )}

      {/* Agent Cards with flow arrows */}
      <div className="grid gap-4 md:grid-cols-3">
        {agents.map((agent, i) => (
          <div key={agent.name} className="relative">
            <AgentCard agent={agent} index={i} />
            {i < agents.length - 1 && (
              <div className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 h-8 w-8 items-center justify-center rounded-full bg-background border border-border">
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pipeline Config */}
      {pipeline && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card className="glass">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-muted-foreground" />
                Pipeline Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-secondary/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Threshold K</p>
                  <div className="flex items-center justify-center gap-1.5">
                    <Gauge className="h-4 w-4 text-primary" />
                    <p className="text-lg font-bold font-mono text-foreground">{pipeline.thresholdK}</p>
                  </div>
                </div>
                <div className="rounded-lg bg-secondary/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Pipeline Runs</p>
                  <div className="flex items-center justify-center gap-1.5">
                    <Activity className="h-4 w-4 text-accent" />
                    <p className="text-lg font-bold font-mono text-foreground">{pipeline.totalRuns}</p>
                  </div>
                </div>
                <div className="rounded-lg bg-secondary/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Cases Stored</p>
                  <div className="flex items-center justify-center gap-1.5">
                    <Database className="h-4 w-4 text-warning" />
                    <p className="text-lg font-bold font-mono text-foreground">{pipeline.casesStored}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Recent Traces */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
        <h2 className="text-lg font-bold text-foreground mb-3 flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          Recent Pipeline Traces
        </h2>
        {traces.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-muted-foreground">
            <Bot className="h-8 w-8 mb-3 opacity-40" />
            <p className="text-sm font-medium">No pipeline runs yet</p>
            <p className="text-xs mt-1">Enable chaos mode to trigger the agent pipeline</p>
          </div>
        ) : (
          <ScrollArea className="max-h-[500px]">
            <div className="space-y-2">
              {traces.map((trace, i) => (
                <TraceItem key={trace.id} trace={trace} index={i} />
              ))}
            </div>
          </ScrollArea>
        )}
      </motion.div>
    </div>
  );
}
