import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Clock, Wifi, WifiOff, AlertTriangle, CheckCircle } from "lucide-react";
import { api, type HealthResponse } from "@/lib/api-client";
import { motion, AnimatePresence } from "framer-motion";

interface EndpointData {
  current: HealthResponse | null;
  error: string | null;
  history: { time: string; latency: number }[];
}

const MAX_POINTS = 20;
const POLL_INTERVAL = 3000;

function getTimestamp() {
  return new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function statusColor(status?: string) {
  if (!status) return "bg-muted text-muted-foreground";
  switch (status.toLowerCase()) {
    case "ok":
    case "healthy":
      return "bg-success/15 text-success border-success/30";
    case "degraded":
      return "bg-warning/15 text-warning border-warning/30";
    default:
      return "bg-destructive/15 text-destructive border-destructive/30";
  }
}

function StatusIcon({ status }: { status?: string }) {
  if (!status) return <WifiOff className="h-5 w-5 text-muted-foreground" />;
  switch (status.toLowerCase()) {
    case "ok":
    case "healthy":
      return <CheckCircle className="h-5 w-5 text-success" />;
    case "degraded":
      return <AlertTriangle className="h-5 w-5 text-warning" />;
    default:
      return <WifiOff className="h-5 w-5 text-destructive" />;
  }
}

function EndpointCard({ label, data }: { label: string; data: EndpointData }) {
  const { current, error, history } = data;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card className="glass glow-primary">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <StatusIcon status={error ? "error" : current?.status} />
              {label}
            </CardTitle>
            <Badge variant="outline" className={statusColor(error ? "error" : current?.status)}>
              {error ? "ERROR" : current?.status?.toUpperCase() || "UNKNOWN"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? (
            <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive font-mono">
              {error}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-secondary/50 p-3 text-center">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Latency</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {current?.latency_ms?.toFixed(0) ?? "—"}
                  <span className="text-xs text-muted-foreground ml-0.5">ms</span>
                </p>
              </div>
              <div className="rounded-lg bg-secondary/50 p-3 text-center">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Error Rate</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {current?.error_rate != null ? `${(current.error_rate * 100).toFixed(1)}%` : "0%"}
                </p>
              </div>
              <div className="rounded-lg bg-secondary/50 p-3 text-center">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Last Check</p>
                <p className="text-xs font-mono text-foreground mt-1">
                  {current?.timestamp ? new Date(current.timestamp).toLocaleTimeString("en-US", { hour12: false }) : "—"}
                </p>
              </div>
            </div>
          )}

          {/* Latency chart */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Latency (last 60s)</p>
            <ResponsiveContainer width="100%" height={120}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="time" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} width={40} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  formatter={(value: number) => [`${value.toFixed(0)} ms`, "Latency"]}
                />
                <Area type="monotone" dataKey="latency" stroke="hsl(var(--chart-1))" fill={`url(#grad-${label})`} strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function LiveStatus() {
  const [health, setHealth] = useState<EndpointData>({ current: null, error: null, history: [] });
  const [checkout, setCheckout] = useState<EndpointData>({ current: null, error: null, history: [] });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    const time = getTimestamp();

    // Poll /health
    try {
      const h = await api.getHealth();
      setHealth((prev) => ({
        current: h,
        error: null,
        history: [...prev.history, { time, latency: h.latency_ms }].slice(-MAX_POINTS),
      }));
    } catch (err: any) {
      setHealth((prev) => ({ ...prev, error: err.message || "Fetch failed" }));
    }

    // Poll /checkout
    try {
      const c = await api.getCheckout();
      setCheckout((prev) => ({
        current: c,
        error: null,
        history: [...prev.history, { time, latency: c.latency_ms }].slice(-MAX_POINTS),
      }));
    } catch (err: any) {
      setCheckout((prev) => ({ ...prev, error: err.message || "Fetch failed" }));
    }
  }, []);

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          Live Status
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Polling endpoints every 3 seconds — real-time latency & status
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
        </span>
        Polling active
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <EndpointCard label="/health" data={health} />
        <EndpointCard label="/checkout" data={checkout} />
      </div>
    </div>
  );
}
