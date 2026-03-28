import { useState, useCallback, useEffect, useRef } from "react";
import { api, type AnomalyRecord } from "@/lib/api-client";
import type { Incident, Severity, Anomaly } from "@/lib/types";

const POLL_INTERVAL = 5000;

function actionToSeverity(action: string): Severity {
  if (action === "REROUTE") return "critical";
  if (action === "ALERT") return "high";
  return "medium";
}

function inferStatusCode(a: AnomalyRecord): number {
  if (a.error_rate > 0.3) return 500;
  if (a.is_degraded) return 200;
  if (a.z_score > 5) return 503;
  return 200;
}

function buildAnomalies(a: AnomalyRecord): Anomaly[] {
  const result: Anomaly[] = [];
  if (a.z_score > 2) {
    result.push({
      type: "Latency Spike",
      metric: "Response Time",
      expected: "< 100ms",
      actual: `${Math.round(a.latency_ms)}ms`,
      severity: a.z_score > 5 ? "critical" : "high",
    });
  }
  if (a.error_rate > 0.1) {
    result.push({
      type: "Error Rate Surge",
      metric: "Error Rate",
      expected: "< 1%",
      actual: `${(a.error_rate * 100).toFixed(1)}%`,
      severity: a.error_rate > 0.5 ? "critical" : "high",
    });
  }
  if (a.is_degraded) {
    result.push({
      type: "Response Degradation",
      metric: "Response Body",
      expected: "All required fields",
      actual: "Missing fields",
      severity: "medium",
    });
  }
  return result;
}

function buildRemediation(a: AnomalyRecord): string[] {
  const steps: string[] = [];
  if (a.z_score > 2) {
    steps.push("Review connection pool and timeout configuration");
    steps.push("Implement circuit breaker pattern for fault isolation");
  }
  if (a.error_rate > 0.1) {
    steps.push("Add retry logic with exponential backoff and jitter");
    steps.push("Configure fallback responses for degraded operation");
  }
  if (a.is_degraded) {
    steps.push("Validate response schema at the API gateway");
    steps.push("Add graceful degradation handling in clients");
  }
  steps.push("Set up monitoring alerts for early anomaly detection");
  return steps;
}

function anomalyToIncident(a: AnomalyRecord): Incident {
  const anomalyList = buildAnomalies(a);
  const remediationSteps = buildRemediation(a);
  const confidence = Math.min(95, Math.max(60, Math.round(85 + (a.z_score - 3) * 2)));

  return {
    id: a.id ?? `ANO-${Date.now()}`,
    endpoint: a.endpoint,
    method: "GET",
    status: "completed",
    severity: actionToSeverity(a.recommended_action),
    timestamp: a.timestamp,
    responseTime: Math.round(a.latency_ms),
    statusCode: inferStatusCode(a),
    errorRate: a.error_rate * 100,
    summary: a.diagnosis,
    rootCause: {
      anomalies: anomalyList,
      diagnosis: a.diagnosis,
      remediationSteps,
      confidence,
      analyzedAt: a.timestamp,
      agentTrace: [
        { agent: "Monitor Agent", action: `Anomaly detected on ${a.endpoint}`, result: `Z-score ${a.z_score.toFixed(1)}, action: ${a.recommended_action}`, timestamp: a.timestamp },
        { agent: "Diagnostic Agent", action: "Correlated metrics and identified patterns", result: a.diagnosis, timestamp: a.timestamp },
        { agent: "Remediation Agent", action: "Generated fix recommendations", result: `${remediationSteps.length} steps proposed`, timestamp: a.timestamp },
      ],
    },
  };
}

export function useIncidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasAutoSelected = useRef(false);

  const fetchIncidents = useCallback(async () => {
    try {
      const anomalies = await api.getAnomalies();
      const mapped = anomalies.map(anomalyToIncident);
      setIncidents(mapped);
      if (!hasAutoSelected.current && mapped.length > 0) {
        setSelectedId(mapped[0].id);
        hasAutoSelected.current = true;
      }
    } catch {
      // keep existing data on fetch failure
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIncidents();
    intervalRef.current = setInterval(fetchIncidents, POLL_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchIncidents]);

  const selectedIncident = incidents.find((i) => i.id === selectedId) ?? null;

  const submitEndpoint = useCallback(
    async (url: string, method: string) => {
      await api.analyzeEndpoint(url, method);
      await fetchIncidents();
    },
    [fetchIncidents],
  );

  return { incidents, selectedIncident, selectedId, setSelectedId, submitEndpoint, loading };
}
