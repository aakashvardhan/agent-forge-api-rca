import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { usePolling } from "@/hooks/use-polling";
import { api } from "@/lib/api-client";
import { BarChart3 } from "lucide-react";

export function HealthCharts() {
  const { data, loading } = usePolling({ fetcher: api.getMetricsHistory, interval: 5000 });
  const metrics = data ?? [];

  if (!loading && metrics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-muted-foreground">
        <BarChart3 className="h-8 w-8 mb-3 opacity-40" />
        <p className="text-sm font-medium">No metrics yet</p>
        <p className="text-xs mt-1">Data will appear as the backend processes requests</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="glass">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Response Latency (ms)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="latency" stroke="hsl(var(--chart-1))" fill="url(#latencyGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Error Rate (%)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="errorGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-4))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-4))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="errorRate" stroke="hsl(var(--chart-4))" fill="url(#errorGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Throughput (requests)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="throughputGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="throughput" stroke="hsl(var(--chart-2))" fill="url(#throughputGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Uptime (%)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="uptimeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-5))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-5))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="uptime" stroke="hsl(var(--chart-5))" fill="url(#uptimeGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
