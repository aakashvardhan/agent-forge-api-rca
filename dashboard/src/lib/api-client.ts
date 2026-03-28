const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export interface HealthResponse {
  status: string;
  endpoint: string;
  latency_ms: number;
  timestamp: string;
  error_rate?: number;
}

export interface ChaosStatus {
  enabled: boolean;
  mode: string | null;
  error_rate: number;
  latency_min: number;
  latency_max: number;
}

export interface ChaosConfig {
  mode: string;
  error_rate: number;
  latency_min: number;
  latency_max: number;
}

export interface AnomalyRecord {
  id?: string;
  endpoint: string;
  z_score: number;
  latency_ms: number;
  error_rate: number;
  is_degraded: boolean;
  diagnosis: string;
  recommended_action: "REROUTE" | "ALERT" | "WAIT";
  timestamp: string;
}

export interface OverviewStats {
  totalIncidents: number;
  activeIncidents: number;
  resolvedToday: number;
  mttr: string;
  avgConfidence: number;
  apisMonitored: number;
}

export interface HealthMetric {
  time: string;
  latency: number;
  errorRate: number;
  throughput: number;
  uptime: number;
}

export interface AnalyzeResult {
  endpoint: string;
  method: string;
  status_code: number;
  latency_ms: number;
  anomaly_detected: boolean;
  error?: string;
}

export interface AgentInfo {
  name: string;
  status: "active" | "idle";
  description: string;
  eventsProcessed?: number;
  anomaliesDetected?: number;
  diagnosesGenerated?: number;
  actionsExecuted?: number;
  actionBreakdown?: Record<string, number>;
  lastActivity: string | null;
}

export interface PipelineTraceStep {
  agent: string;
  action: string;
  result: string;
  status: string;
}

export interface PipelineTrace {
  id: string;
  endpoint: string;
  timestamp: string;
  steps: PipelineTraceStep[];
}

export interface AgentStatusResponse {
  agents: AgentInfo[];
  pipeline: {
    totalRuns: number;
    thresholdK: number;
    casesStored: number;
  };
  recentTraces: PipelineTrace[];
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),
  getCheckout: () => request<HealthResponse>("/checkout"),
  getChaosStatus: () => request<ChaosStatus>("/chaos/status"),
  enableChaos: (config: ChaosConfig) =>
    request<{ message: string }>("/chaos/enable", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  disableChaos: () =>
    request<{ message: string }>("/chaos/disable", {
      method: "POST",
    }),
  getAnomalies: () => request<AnomalyRecord[]>("/anomalies"),
  getStats: () => request<OverviewStats>("/stats"),
  getMetricsHistory: () => request<HealthMetric[]>("/metrics/history"),
  analyzeEndpoint: (endpoint: string, method: string) =>
    request<AnalyzeResult>("/analyze", {
      method: "POST",
      body: JSON.stringify({ endpoint, method }),
    }),
  getAgentStatus: () => request<AgentStatusResponse>("/agents/status"),
};
