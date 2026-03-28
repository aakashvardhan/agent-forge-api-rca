import { useState, useEffect, useRef, useCallback } from "react";

interface PollingOptions<T> {
  fetcher: () => Promise<T>;
  interval: number;
  enabled?: boolean;
}

export function usePolling<T>({ fetcher, interval, enabled = true }: PollingOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    try {
      const result = await fetcher();
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Fetch failed");
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    if (!enabled) return;
    poll();
    intervalRef.current = setInterval(poll, interval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll, interval, enabled]);

  return { data, error, loading };
}

export interface TimeSeriesPoint {
  time: string;
  value: number;
}

export function useTimeSeries(maxPoints = 20) {
  const [series, setSeries] = useState<TimeSeriesPoint[]>([]);

  const addPoint = useCallback(
    (value: number) => {
      setSeries((prev) => {
        const next = [
          ...prev,
          { time: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }), value },
        ];
        return next.slice(-maxPoints);
      });
    },
    [maxPoints]
  );

  return { series, addPoint };
}
