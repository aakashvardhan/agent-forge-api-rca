import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Zap, ZapOff, AlertTriangle, Clock, Flame, Loader2 } from "lucide-react";
import { api, type ChaosStatus, type ChaosConfig } from "@/lib/api-client";
import { toast } from "sonner";
import { motion } from "framer-motion";

const CHAOS_MODES = [
  { id: "latency", label: "Latency", icon: Clock, description: "Inject artificial latency" },
  { id: "errors", label: "Errors", icon: AlertTriangle, description: "Return random errors" },
  { id: "degraded", label: "Degraded", icon: Flame, description: "Simulate degraded state" },
] as const;

export default function ChaosControl() {
  const [mode, setMode] = useState("latency");
  const [errorRate, setErrorRate] = useState(0.5);
  const [latencyMin, setLatencyMin] = useState(200);
  const [latencyMax, setLatencyMax] = useState(2000);
  const [chaosStatus, setChaosStatus] = useState<ChaosStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const s = await api.getChaosStatus();
      setChaosStatus(s);
      setStatusError(null);
    } catch (err: any) {
      setStatusError(err.message);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchStatus]);

  const handleEnable = async () => {
    setEnabling(true);
    try {
      await api.enableChaos({ mode, error_rate: errorRate, latency_min: latencyMin, latency_max: latencyMax });
      toast.success("Chaos enabled", { description: `Mode: ${mode}` });
      fetchStatus();
    } catch (err: any) {
      toast.error("Failed to enable chaos", { description: err.message });
    } finally {
      setEnabling(false);
    }
  };

  const handleDisable = async () => {
    setDisabling(true);
    try {
      await api.disableChaos();
      toast.success("Chaos disabled");
      fetchStatus();
    } catch (err: any) {
      toast.error("Failed to disable chaos", { description: err.message });
    } finally {
      setDisabling(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <Zap className="h-6 w-6 text-warning" />
          Chaos Control
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Inject faults to test resilience and observe RCA in action</p>
      </div>

      {/* Current Status */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="glass">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center justify-between">
              Current Chaos Status
              {chaosStatus?.enabled ? (
                <Badge className="bg-destructive/15 text-destructive border-destructive/30" variant="outline">
                  <Flame className="h-3 w-3 mr-1" /> ACTIVE
                </Badge>
              ) : (
                <Badge className="bg-success/15 text-success border-success/30" variant="outline">
                  <ZapOff className="h-3 w-3 mr-1" /> INACTIVE
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statusError ? (
              <p className="text-xs text-destructive font-mono">{statusError}</p>
            ) : chaosStatus ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                <div className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Mode</p>
                  <p className="text-sm font-bold font-mono text-foreground">{chaosStatus.mode ?? "—"}</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Error Rate</p>
                  <p className="text-sm font-bold font-mono text-foreground">{(chaosStatus.error_rate * 100).toFixed(0)}%</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Lat Min</p>
                  <p className="text-sm font-bold font-mono text-foreground">{chaosStatus.latency_min}ms</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Lat Max</p>
                  <p className="text-sm font-bold font-mono text-foreground">{chaosStatus.latency_max}ms</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Loading...</p>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Configuration */}
      <div className="grid gap-5 md:grid-cols-2">
        {/* Mode Selection */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="glass h-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Chaos Mode</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {CHAOS_MODES.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`w-full flex items-center gap-3 rounded-lg p-3 text-left transition-all ${
                    mode === m.id
                      ? "bg-primary/10 border border-primary/30 text-foreground"
                      : "bg-secondary/30 border border-transparent text-muted-foreground hover:bg-secondary/60"
                  }`}
                >
                  <m.icon className={`h-4 w-4 ${mode === m.id ? "text-primary" : ""}`} />
                  <div>
                    <p className="text-sm font-medium">{m.label}</p>
                    <p className="text-[11px] text-muted-foreground">{m.description}</p>
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Sliders */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="glass h-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex justify-between">
                  <Label className="text-xs text-muted-foreground">Error Rate</Label>
                  <span className="text-xs font-mono text-foreground">{(errorRate * 100).toFixed(0)}%</span>
                </div>
                <Slider value={[errorRate]} onValueChange={([v]) => setErrorRate(v)} min={0} max={1} step={0.05} />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <Label className="text-xs text-muted-foreground">Latency Min</Label>
                  <span className="text-xs font-mono text-foreground">{latencyMin}ms</span>
                </div>
                <Slider value={[latencyMin]} onValueChange={([v]) => setLatencyMin(v)} min={0} max={5000} step={50} />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <Label className="text-xs text-muted-foreground">Latency Max</Label>
                  <span className="text-xs font-mono text-foreground">{latencyMax}ms</span>
                </div>
                <Slider value={[latencyMax]} onValueChange={([v]) => setLatencyMax(v)} min={0} max={10000} step={100} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Actions */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="flex gap-3">
        <Button onClick={handleEnable} disabled={enabling} className="flex-1 gap-2" variant="default">
          {enabling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          Enable Chaos
        </Button>
        <Button onClick={handleDisable} disabled={disabling} className="flex-1 gap-2" variant="outline">
          {disabling ? <Loader2 className="h-4 w-4 animate-spin" /> : <ZapOff className="h-4 w-4" />}
          Disable Chaos
        </Button>
      </motion.div>
    </div>
  );
}
