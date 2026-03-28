import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AlertTriangle, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type AnomalyRecord } from "@/lib/api-client";
import { motion, AnimatePresence } from "framer-motion";

function ActionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    REROUTE: "bg-destructive/15 text-destructive border-destructive/30",
    ALERT: "bg-warning/15 text-warning border-warning/30",
    WAIT: "bg-success/15 text-success border-success/30",
  };
  return (
    <Badge variant="outline" className={`font-mono text-[10px] ${styles[action] || "bg-muted text-muted-foreground"}`}>
      {action}
    </Badge>
  );
}

export default function IncidentLog() {
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAnomalies = useCallback(async () => {
    try {
      const data = await api.getAnomalies();
      setAnomalies(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnomalies();
    intervalRef.current = setInterval(fetchAnomalies, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchAnomalies]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-destructive" />
            Incident Log
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time anomaly feed from the detection pipeline</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAnomalies} className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      <Card className="glass">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="p-6">
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive font-mono">
                {error}
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Make sure your backend is running at the configured API URL.
              </p>
            </div>
          ) : anomalies.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
              <AlertTriangle className="h-8 w-8 mb-3 opacity-40" />
              <p className="text-sm">No anomalies detected yet</p>
              <p className="text-xs mt-1">Enable chaos mode to generate incidents</p>
            </div>
          ) : (
            <ScrollArea className="max-h-[600px]">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="text-[10px] uppercase tracking-wider">Endpoint</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Z-Score</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Latency</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Error Rate</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Degraded</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Diagnosis</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Action</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <AnimatePresence>
                    {anomalies.map((a, i) => (
                      <motion.tr
                        key={a.id || `${a.endpoint}-${a.timestamp}-${i}`}
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-b transition-colors hover:bg-muted/50"
                      >
                        <TableCell className="font-mono text-xs font-medium text-foreground">{a.endpoint}</TableCell>
                        <TableCell className="font-mono text-xs">
                          <span className={a.z_score > 2 ? "text-destructive font-bold" : "text-muted-foreground"}>
                            {a.z_score.toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-xs text-foreground">{a.latency_ms.toFixed(0)}ms</TableCell>
                        <TableCell className="font-mono text-xs text-foreground">{(a.error_rate * 100).toFixed(1)}%</TableCell>
                        <TableCell>
                          {a.is_degraded ? (
                            <Badge variant="outline" className="bg-warning/15 text-warning border-warning/30 text-[10px]">YES</Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px]">NO</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">{a.diagnosis}</TableCell>
                        <TableCell><ActionBadge action={a.recommended_action} /></TableCell>
                        <TableCell className="font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                          {new Date(a.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                        </TableCell>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
