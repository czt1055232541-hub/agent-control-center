import React from "react";
import { readJson } from "../api";
import type { Diagnostics, StackStatus } from "../types";

export function useStatus(enabled = true, diagnosticsEnabled = true) {
  const [token, setToken] = React.useState("");
  const [status, setStatus] = React.useState<StackStatus | null>(null);
  const [diagnostics, setDiagnostics] = React.useState<Diagnostics | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (!enabled) return;
    try {
      const nextStatus = await readJson<StackStatus>("/api/status");
      setStatus(nextStatus);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      throw exc;
    }
  }, [enabled]);

  const loadDiagnostics = React.useCallback(async () => {
    if (!diagnosticsEnabled) return;
    const next = await readJson<Diagnostics>("/api/diagnostics");
    setDiagnostics(next);
  }, [diagnosticsEnabled]);

  // Initial load + WebSocket with HTTP fallback
  React.useEffect(() => {
    readJson<{ token: string }>("/api/session")
      .then((session) => setToken(session.token))
      .catch((exc) => setError(exc instanceof Error ? exc.message : String(exc)));
    refresh().catch(() => {});
    loadDiagnostics().catch(() => {});

    let statusTimer: number | null = null;
    let ws: WebSocket | null = null;
    let reconnectTimeout: number | null = null;

    const connectWs = () => {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/status`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (statusTimer !== null) {
          window.clearInterval(statusTimer);
          statusTimer = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as StackStatus;
          setStatus(data);
        } catch { /* ignore malformed messages */ }
      };

      ws.onclose = () => {
        if (statusTimer === null) {
          statusTimer = window.setInterval(() => {
            refresh().catch(() => {});
          }, 2000);
        }
        reconnectTimeout = window.setTimeout(connectWs, 5000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    if (enabled) connectWs();

    return () => {
      if (statusTimer !== null) window.clearInterval(statusTimer);
      if (reconnectTimeout !== null) window.clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [enabled, refresh, loadDiagnostics]);

  return { token, status, diagnostics, error, refresh, loadDiagnostics };
}
