import React from "react";
import { readJson } from "../api";
import type { CurrentWatchdogStatus } from "../types";

export function useWatchdog() {
  const [watchdog, setWatchdog] = React.useState<CurrentWatchdogStatus | null>(null);

  const refreshWatchdog = React.useCallback(async () => {
    const next = await readJson<CurrentWatchdogStatus>("/api/watchdog/current");
    setWatchdog(next);
  }, []);

  React.useEffect(() => {
    refreshWatchdog().catch(() => {});
    const timer = window.setInterval(() => {
      refreshWatchdog().catch(() => {});
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refreshWatchdog]);

  return { watchdog, refreshWatchdog };
}
