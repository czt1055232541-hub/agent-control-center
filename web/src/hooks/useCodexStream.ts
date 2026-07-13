import React from "react";
import { readJson } from "../api";
import type { CodexStreamEvent, CodexStreamPayload, CodexStreamRun } from "../types";

type StreamWsMessage =
  | { type: "event"; run_id: string; event: CodexStreamEvent }
  | { type: "heartbeat"; run_id: string; events: [] };

export function useCodexStream() {
  const [runs, setRuns] = React.useState<CodexStreamRun[]>([]);
  const [runId, setRunId] = React.useState("latest");
  const [events, setEvents] = React.useState<CodexStreamEvent[]>([]);
  const [connected, setConnected] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadRuns = React.useCallback(async () => {
    const result = await readJson<{ streams: CodexStreamRun[] }>("/api/codex-agent/streams?limit=20");
    setRuns(result.streams);
    return result.streams;
  }, []);

  const loadStream = React.useCallback(async (target = runId) => {
    try {
      const result = await readJson<CodexStreamPayload>(`/api/codex-agent/streams/${encodeURIComponent(target)}`);
      setEvents(result.events);
      setError(null);
      return result;
    } catch (exc) {
      setEvents([]);
      setError(exc instanceof Error ? exc.message : String(exc));
      return null;
    }
  }, [runId]);

  React.useEffect(() => {
    loadRuns().catch(() => {});
    loadStream("latest").catch(() => {});
  }, [loadRuns, loadStream]);

  React.useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: number | null = null;
    let closed = false;
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/codex-agent/stream?run_id=${encodeURIComponent(runId)}`);
      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };
      ws.onmessage = (message) => {
        try {
          const data = JSON.parse(message.data) as StreamWsMessage;
          if (data.type === "event") {
            setEvents((current) => {
              const key = eventKey(data.event);
              if (current.some((item) => eventKey(item) === key)) {
                return current;
              }
              return [...current, data.event].slice(-500);
            });
          }
        } catch {
          // Ignore malformed stream frames.
        }
      };
      ws.onerror = () => {
        setConnected(false);
        ws?.close();
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          reconnectTimeout = window.setTimeout(connect, 3000);
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (reconnectTimeout !== null) window.clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [runId]);

  return { runs, runId, events, connected, error, setRunId, loadRuns, loadStream };
}

function eventKey(event: CodexStreamEvent): string {
  return [event.run_id, event.timestamp, event.phase, event.stream, event.text].join("|");
}
