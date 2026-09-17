import React from "react";
import { readJson } from "../api";
import type { LogTail } from "../types";

export function useLogs(enabled = true) {
  const [logs, setLogs] = React.useState<{ component: string; logs: LogTail[] } | null>(null);
  const [selectedLog, setSelectedLog] = React.useState("operations");
  const [logLines, setLogLines] = React.useState(120);
  const [error, setError] = React.useState<string | null>(null);

  const selectedLogRef = React.useRef(selectedLog);
  selectedLogRef.current = selectedLog;
  const logLinesRef = React.useRef(logLines);
  logLinesRef.current = logLines;

  const loadLogs = React.useCallback(async (component?: string, lines?: number): Promise<void> => {
    if (!enabled) return;
    const comp = component ?? selectedLogRef.current;
    const lineCount = lines ?? logLinesRef.current;
    const result = await readJson<{ component: string; logs: LogTail[] }>(
      `/api/logs/${comp}?lines=${lineCount}`
    );
    setSelectedLog(comp);
    setLogs(result);
    setError(null);
  }, [enabled]);

  // Periodic log polling
  React.useEffect(() => {
    if (!enabled) return;
    const logTimer = window.setInterval(() => {
      loadLogs().catch((exc) => setError(exc instanceof Error ? exc.message : String(exc)));
    }, 3000);
    return () => window.clearInterval(logTimer);
  }, [enabled, loadLogs]);

  return { logs, selectedLog, logLines, error, loadLogs, setSelectedLog, setLogLines };
}
