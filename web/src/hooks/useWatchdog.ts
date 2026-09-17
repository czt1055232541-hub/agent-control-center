import React from "react";
import { readJson } from "../api";
import type { CurrentWatchdogStatus } from "../types";

export function useWatchdog(enabled = true) {
  const [watchdog, setWatchdog] = React.useState<CurrentWatchdogStatus | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refreshWatchdog = React.useCallback(async () => {
    if (!enabled) return;
    try {
      const next = await readJson<CurrentWatchdogStatus>("/api/watchdog/current");
      setWatchdog(next);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      throw exc;
    }
  }, [enabled]);

  React.useEffect(() => {
    if (!enabled) return;
    refreshWatchdog().catch(() => {});
    const timer = window.setInterval(() => {
      refreshWatchdog().catch(() => {});
    }, 5000);
    return () => window.clearInterval(timer);
  }, [enabled, refreshWatchdog]);

  return { watchdog, error, refreshWatchdog };
}
