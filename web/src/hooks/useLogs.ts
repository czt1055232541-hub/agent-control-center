import React from "react";
import { readJson } from "../api";
import type { LogTail } from "../types";

export function useLogs() {
  const [logs, setLogs] = React.useState<{ component: string; logs: LogTail[] } | null>(null);
  const [selectedLog, setSelectedLog] = React.useState("operations");
  const [logLines, setLogLines] = React.useState(120);

  const selectedLogRef = React.useRef(selectedLog);
  selectedLogRef.current = selectedLog;
  const logLinesRef = React.useRef(logLines);
  logLinesRef.current = logLines;

  const loadLogs = React.useCallback(async (component?: string, lines?: number): Promise<void> => {
    const comp = component ?? selectedLogRef.current;
    const lineCount = lines ?? logLinesRef.current;
    const result = await readJson<{ component: string; logs: LogTail[] }>(
      `/api/logs/${comp}?lines=${lineCount}`
    );
    setSelectedLog(comp);
    setLogs(result);
  }, []);

  // Periodic log polling
  React.useEffect(() => {
    const logTimer = window.setInterval(() => {
      loadLogs().catch(() => {});
    }, 3000);
    return () => window.clearInterval(logTimer);
  }, [loadLogs]);

  return { logs, selectedLog, logLines, loadLogs, setSelectedLog, setLogLines };
}
