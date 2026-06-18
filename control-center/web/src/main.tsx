import React from "react";
import ReactDOM from "react-dom/client";
import { AlertTriangle, CheckCircle2, PauseCircle, Play, Power, RefreshCcw, Server, Square, Terminal, XCircle } from "lucide-react";
import "./styles.css";

type ComponentStatus = {
  name: string;
  port: number | null;
  port_listening: boolean;
  pid_file: string | null;
  pid: number | null;
  pid_running: boolean;
  process_name: string | null;
};

type ProviderStatus = {
  model: string;
  provider: string;
  mode: string;
  config: string;
};

type StackStatus = {
  codex: ProviderStatus;
  openclaw: ComponentStatus;
  moonbridge: ComponentStatus;
  codex_agent: ComponentStatus;
  codex_desktop_running: boolean;
  stack_root: string;
};

type OperationResult = {
  ok: boolean;
  component: string;
  action: string;
  message: string;
  pid?: number | null;
  port?: number | null;
  duration_ms: number;
};

type OperationRecord = {
  timestamp: string;
  component: string;
  action: string;
  ok: boolean;
  message: string;
  duration_ms: number;
};

type LogTail = {
  path: string;
  lines: string[];
};

const componentRows = [
  { key: "openclaw", title: "OpenClaw Gateway", logs: "openclaw" },
  { key: "moonbridge", title: "MoonBridge", logs: "moonbridge" },
  { key: "codex_agent", title: "Feishu Codex Agent", logs: "codex-agent" },
] as const;

function isRunning(component: ComponentStatus): boolean {
  return component.pid_running || component.port_listening;
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return data as T;
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
  const Icon = active ? CheckCircle2 : XCircle;
  return (
    <div className={`inline-flex h-8 items-center gap-2 rounded-md border px-3 text-sm ${active ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-stone-300 bg-stone-50 text-stone-700"}`}>
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function ActionButton({ label, icon, danger = false, disabled, onClick }: { label: string; icon: React.ReactNode; danger?: boolean; disabled: boolean; onClick: () => void }) {
  return (
    <button
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${
        danger
          ? "border-red-300 bg-red-50 text-red-800 hover:bg-red-100"
          : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
      }`}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ComponentPanel({
  component,
  title,
  disabled,
  onAction,
  onLogs,
}: {
  component: ComponentStatus;
  title: string;
  disabled: boolean;
  onAction: (action: string) => void;
  onLogs: () => void;
}) {
  const running = isRunning(component);
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">
            PID {component.pid ?? "none"} {component.port ? `· Port ${component.port}` : ""}
          </p>
        </div>
        <StatusPill active={running} label={running ? "Running" : "Stopped"} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <ActionButton disabled={disabled} icon={<Play size={16} />} label="Start" onClick={() => onAction("start")} />
        <ActionButton disabled={disabled} icon={<Square size={16} />} label="Stop" onClick={() => onAction("stop")} />
        <ActionButton disabled={disabled} icon={<RefreshCcw size={16} />} label="Restart" onClick={() => onAction("restart")} />
        <ActionButton disabled={disabled} icon={<Terminal size={16} />} label="Logs" onClick={onLogs} />
      </div>
    </section>
  );
}

function App() {
  const [token, setToken] = React.useState("");
  const [status, setStatus] = React.useState<StackStatus | null>(null);
  const [operations, setOperations] = React.useState<OperationRecord[]>([]);
  const [result, setResult] = React.useState<OperationResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [logs, setLogs] = React.useState<{ component: string; logs: LogTail[] } | null>(null);
  const [confirmDesktopStop, setConfirmDesktopStop] = React.useState(false);

  const refresh = React.useCallback(async () => {
    const [nextStatus, nextOperations] = await Promise.all([
      readJson<StackStatus>("/api/status"),
      readJson<{ operations: OperationRecord[] }>("/api/operations"),
    ]);
    setStatus(nextStatus);
    setOperations(nextOperations.operations);
  }, []);

  React.useEffect(() => {
    readJson<{ token: string }>("/api/session")
      .then((session) => setToken(session.token))
      .catch((exc: Error) => setError(exc.message));
    refresh().catch((exc: Error) => setError(exc.message));
    const timer = window.setInterval(() => {
      refresh().catch((exc: Error) => setError(exc.message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  async function run(path: string) {
    if (!token) {
      setError("Control token is not ready.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await readJson<OperationResult>(path, {
        method: "POST",
        headers: { "X-Control-Token": token },
      });
      setResult(next);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  async function loadLogs(component: string) {
    setError("");
    try {
      setLogs(await readJson<{ component: string; logs: LogTail[] }>(`/api/logs/${component}`));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  const providerMode = status?.codex.mode ?? "unknown";

  return (
    <main className="min-h-screen bg-stone-100 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-5">
        <header className="flex flex-col gap-4 border-b border-slate-300 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950">Feishu Codex Control</h1>
            <p className="mt-1 text-sm text-slate-600">{status?.stack_root ?? "Loading stack status..."}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill active={providerMode === "moonbridge"} label={`Provider: ${providerMode}`} />
            <StatusPill active={Boolean(status?.codex_desktop_running)} label="Codex Desktop" />
          </div>
        </header>

        {error ? (
          <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {result ? (
          <div className={`rounded-md border p-3 text-sm ${result.ok ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900"}`}>
            <strong>{result.component} {result.action}</strong>: {result.message} ({result.duration_ms} ms)
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          {status
            ? componentRows.map((row) => (
                <ComponentPanel
                  key={row.key}
                  component={status[row.key]}
                  disabled={busy}
                  title={row.title}
                  onAction={(action) => run(`/api/${row.logs}/${action}`)}
                  onLogs={() => loadLogs(row.logs)}
                />
              ))
            : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Codex Provider</h2>
            <p className="mt-1 text-sm text-slate-600">Model {status?.codex.model ?? "unknown"}</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <ActionButton disabled={busy || providerMode === "native"} icon={<Server size={16} />} label="Native" onClick={() => run("/api/codex-provider/native")} />
              <ActionButton disabled={busy || providerMode === "moonbridge"} icon={<Server size={16} />} label="MoonBridge" onClick={() => run("/api/codex-provider/moonbridge")} />
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Stack Actions</h2>
            <div className="mt-4 grid gap-2">
              <ActionButton disabled={busy} icon={<Play size={16} />} label="Start Native Stack" onClick={() => run("/api/stack/start-native")} />
              <ActionButton disabled={busy} icon={<Play size={16} />} label="Start MoonBridge Stack" onClick={() => run("/api/stack/start-moonbridge")} />
              <ActionButton disabled={busy} icon={<PauseCircle size={16} />} label="Stop Stack" onClick={() => run("/api/stack/stop")} />
            </div>
          </section>

          <section className="rounded-lg border border-red-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-red-950">Codex Desktop</h2>
            <p className="mt-1 text-sm text-slate-600">Independent desktop process control.</p>
            <div className="mt-4 grid gap-2">
              {!confirmDesktopStop ? (
                <ActionButton disabled={busy} danger icon={<Power size={16} />} label="Stop Codex Desktop" onClick={() => setConfirmDesktopStop(true)} />
              ) : (
                <>
                  <ActionButton disabled={busy} danger icon={<Power size={16} />} label="Confirm Stop" onClick={() => run("/api/codex-desktop/stop")} />
                  <ActionButton disabled={busy} icon={<XCircle size={16} />} label="Cancel" onClick={() => setConfirmDesktopStop(false)} />
                </>
              )}
            </div>
          </section>
        </div>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Operation Log</h2>
            <div className="mt-3 max-h-80 overflow-auto">
              {operations.length ? operations.map((operation, index) => (
                <div key={`${operation.timestamp}-${index}`} className="border-b border-slate-100 py-2 text-sm last:border-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-slate-900">{operation.component} {operation.action}</span>
                    <span className={operation.ok ? "text-emerald-700" : "text-red-700"}>{operation.ok ? "ok" : "failed"} · {operation.duration_ms} ms</span>
                  </div>
                  <p className="mt-1 text-slate-600">{operation.message}</p>
                </div>
              )) : <p className="text-sm text-slate-600">No operations yet.</p>}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Logs</h2>
            <div className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-100">
              {logs ? logs.logs.map((log) => (
                <div key={log.path} className="mb-4 last:mb-0">
                  <div className="mb-2 text-slate-400">{log.path}</div>
                  <pre className="whitespace-pre-wrap">{log.lines.join("\n") || "(empty)"}</pre>
                </div>
              )) : <pre>Select Logs on a component.</pre>}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
