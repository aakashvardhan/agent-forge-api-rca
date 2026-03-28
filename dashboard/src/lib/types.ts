export type IncidentStatus = "pending" | "analyzing" | "completed" | "failed";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Incident {
  id: string;
  endpoint: string;
  method: string;
  status: IncidentStatus;
  severity: Severity;
  timestamp: string;
  responseTime: number;
  statusCode: number;
  errorRate: number;
  summary: string;
  rootCause?: RootCauseAnalysis;
}

export interface RootCauseAnalysis {
  anomalies: Anomaly[];
  diagnosis: string;
  remediationSteps: string[];
  confidence: number;
  analyzedAt: string;
  agentTrace: AgentStep[];
}

export interface Anomaly {
  type: string;
  metric: string;
  expected: string;
  actual: string;
  severity: Severity;
}

export interface AgentStep {
  agent: string;
  action: string;
  result: string;
  timestamp: string;
}

export interface HealthMetric {
  time: string;
  latency: number;
  errorRate: number;
  throughput: number;
  uptime: number;
}

export interface OverviewStats {
  totalIncidents: number;
  activeIncidents: number;
  resolvedToday: number;
  mttr: string;
  avgConfidence: number;
  apisMonitored: number;
}
