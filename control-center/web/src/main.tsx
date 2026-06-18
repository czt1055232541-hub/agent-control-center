import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  PauseCircle,
  Play,
  Power,
  RefreshCcw,
  Server,
  ShieldCheck,
  Square,
  Terminal,
  Wrench,
  XCircle,
} from "lucide-react";
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
  codex_desktop: {
    running: boolean;
    pid: number | null;
    process_count: number;
    executable: string | null;
  };
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

type CommandDiagnostic = {
  ok: boolean;
  returncode?: number;
  stdout?: string;
  stderr?: string;
  duration_ms: number;
};

type MoonBridgeDiagnostic = {
  ok: boolean;
  reachable: boolean;
  status: number | null;
  models: string[];
  error: string;
  duration_ms: number;
};

type Diagnostics = {
  codex_doctor: CommandDiagnostic;
  moonbridge_models: MoonBridgeDiagnostic;
  lark_auth_status: CommandDiagnostic;
};

const componentRows = [
  { key: "openclaw", title: "OpenClaw Gateway", logs: "openclaw" },
  { key: "moonbridge", title: "MoonBridge", logs: "moonbridge" },
  { key: "codex_agent", title: "Feishu Codex Agent", logs: "codex-agent" },
] as const;

const logOptions = [
  { value: "openclaw", label: "OpenClaw" },
  { value: "moonbridge", label: "MoonBridge" },
  { value: "codex-agent", label: "Codex Agent" },
  { value: "codex-desktop", label: "Codex Desktop" },
  { value: "control-center-api", label: "Control API" },
  { value: "operations", label: "Operations" },
];

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
            PID {component.pid ?? "none"} {component.port ? `| Port ${component.port}` : ""}
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

function DiagnosticCard({ title, ok, body, footer }: { title: string; ok: boolean; body: string; footer: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-slate-950">{title}</span>
        <StatusPill active={ok} label={ok ? "OK" : "Check"} />
      </div>
      <p className="mt-2 line-clamp-3 text-sm text-slate-700">{body || "(no output)"}</p>
      <p className="mt-2 text-xs text-slate-500">{footer}</p>
    </div>
  );
}

function CodexRuntimePanel({
  status,
  providerMode,
  busy,
  confirmStop,
  confirmRestart,
  setConfirmStop,
  setConfirmRestart,
  run,
  loadLogs,
  loadDiagnostics,
}: {
  status: StackStatus | null;
  providerMode: string;
  busy: boolean;
  confirmStop: boolean;
  confirmRestart: boolean;
  setConfirmStop: (value: boolean) => void;
  setConfirmRestart: (value: boolean) => void;
  run: (path: string, after?: () => Promise<void>) => Promise<void>;
  loadLogs: (component?: string, lines?: number) => Promise<void>;
  loadDiagnostics: () => Promise<void>;
}) {
  const running = Boolean(status?.codex_desktop.running ?? status?.codex_desktop_running);
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Codex Runtime</h2>
          <p className="mt-1 text-sm text-slate-600">
            Provider {providerMode} | Model {status?.codex.model ?? "unknown"} | PID {status?.codex_desktop.pid ?? "none"}
          </p>
          <p className="mt-1 truncate text-xs text-slate-500">{status?.codex_desktop.executable ?? "Codex Desktop executable not detected"}</p>
        </div>
        <StatusPill active={running} label={running ? "Desktop Running" : "Desktop Stopped"} />
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Desktop</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <ActionButton disabled={busy || running} icon={<Play size={16} />} label="Start" onClick={() => run("/api/codex-desktop/start")} />
            {!confirmStop ? (
              <ActionButton disabled={busy || !running} danger icon={<Power size={16} />} label="Stop" onClick={() => setConfirmStop(true)} />
            ) : (
              <ActionButton disabled={busy} danger icon={<Power size={16} />} label="Confirm Stop" onClick={() => run("/api/codex-desktop/stop").then(() => setConfirmStop(false))} />
            )}
            {!confirmRestart ? (
              <ActionButton disabled={busy || !running} danger icon={<RefreshCcw size={16} />} label="Restart" onClick={() => setConfirmRestart(true)} />
            ) : (
              <ActionButton disabled={busy} danger icon={<RefreshCcw size={16} />} label="Confirm Restart" onClick={() => run("/api/codex-desktop/restart").then(() => setConfirmRestart(false))} />
            )}
            <ActionButton disabled={busy} icon={<Terminal size={16} />} label="Logs" onClick={() => loadLogs("codex-desktop")} />
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Provider</p>
          <div className="grid grid-cols-2 gap-2">
            <ActionButton disabled={busy || providerMode === "native"} icon={<Server size={16} />} label="Native" onClick={() => run("/api/codex-provider/native", loadDiagnostics)} />
            <ActionButton disabled={busy || providerMode === "moonbridge"} icon={<Server size={16} />} label="MoonBridge" onClick={() => run("/api/codex-provider/moonbridge", loadDiagnostics)} />
          </div>
          {(confirmStop || confirmRestart) ? (
            <ActionButton disabled={busy} icon={<XCircle size={16} />} label="Cancel Desktop Action" onClick={() => {
              setConfirmStop(false);
              setConfirmRestart(false);
            }} />
          ) : null}
        </div>
      </div>
    </section>
  );
}

function App() {
  const [token, setToken] = React.useState("");
  const [status, setStatus] = React.useState<StackStatus | null>(null);
  const [operations, setOperations] = React.useState<OperationRecord[]>([]);
  const [diagnostics, setDiagnostics] = React.useState<Diagnostics | null>(null);
  const [result, setResult] = React.useState<OperationResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [logs, setLogs] = React.useState<{ component: string; logs: LogTail[] } | null>(null);
  const [selectedLog, setSelectedLog] = React.useState("operations");
  const [logLines, setLogLines] = React.useState(120);
  const [confirmDesktopStop, setConfirmDesktopStop] = React.useState(false);
  const [confirmDesktopRestart, setConfirmDesktopRestart] = React.useState(false);

  const refresh = React.useCallback(async () => {
    const [nextStatus, nextOperations] = await Promise.all([
      readJson<StackStatus>("/api/status"),
      readJson<{ operations: OperationRecord[] }>("/api/operations"),
    ]);
    setStatus(nextStatus);
    setOperations(nextOperations.operations);
  }, []);

  const loadDiagnostics = React.useCallback(async () => {
    const next = await readJson<Diagnostics>("/api/diagnostics");
    setDiagnostics(next);
  }, []);

  const loadLogs = React.useCallback(async (component = selectedLog, lines = logLines) => {
    setError("");
    try {
      setSelectedLog(component);
      setLogs(await readJson<{ component: string; logs: LogTail[] }>(`/api/logs/${component}?lines=${lines}`));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, [logLines, selectedLog]);

  React.useEffect(() => {
    readJson<{ token: string }>("/api/session")
      .then((session) => setToken(session.token))
      .catch((exc: Error) => setError(exc.message));
    refresh().catch((exc: Error) => setError(exc.message));
    loadDiagnostics().catch((exc: Error) => setError(exc.message));
    loadLogs("operations", 120).catch((exc: Error) => setError(exc.message));
    const timer = window.setInterval(() => {
      refresh().catch((exc: Error) => setError(exc.message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [loadDiagnostics, loadLogs, refresh]);

  async function run(path: string, after?: () => Promise<void>) {
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
      await after?.();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
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
          <CodexRuntimePanel
            status={status}
            providerMode={providerMode}
            busy={busy}
            confirmStop={confirmDesktopStop}
            confirmRestart={confirmDesktopRestart}
            setConfirmStop={setConfirmDesktopStop}
            setConfirmRestart={setConfirmDesktopRestart}
            run={run}
            loadLogs={loadLogs}
            loadDiagnostics={loadDiagnostics}
          />

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Stack Actions</h2>
            <div className="mt-4 grid gap-2">
              <ActionButton disabled={busy} icon={<Play size={16} />} label="Start Native Stack" onClick={() => run("/api/stack/start-native", loadDiagnostics)} />
              <ActionButton disabled={busy} icon={<Play size={16} />} label="Start MoonBridge Stack" onClick={() => run("/api/stack/start-moonbridge", loadDiagnostics)} />
              <ActionButton disabled={busy} icon={<PauseCircle size={16} />} label="Stop Stack" onClick={() => run("/api/stack/stop", loadDiagnostics)} />
            </div>
          </section>

        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Diagnostics</h2>
              <p className="mt-1 text-sm text-slate-600">Codex doctor, MoonBridge models, Lark auth, and backup cleanup.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <ActionButton disabled={busy} icon={<RefreshCcw size={16} />} label="Refresh" onClick={() => loadDiagnostics().catch((exc: Error) => setError(exc.message))} />
              <ActionButton disabled={busy} icon={<Wrench size={16} />} label="Clean Backups" onClick={() => run("/api/backups/clean", loadDiagnostics)} />
            </div>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <DiagnosticCard
              title="Codex Doctor"
              ok={Boolean(diagnostics?.codex_doctor.ok)}
              body={diagnostics?.codex_doctor.stdout || diagnostics?.codex_doctor.stderr || "Not loaded"}
              footer={`${diagnostics?.codex_doctor.duration_ms ?? 0} ms`}
            />
            <DiagnosticCard
              title="MoonBridge Models"
              ok={Boolean(diagnostics?.moonbridge_models.ok)}
              body={diagnostics?.moonbridge_models.models?.join(", ") || diagnostics?.moonbridge_models.error || "No models"}
              footer={`HTTP ${diagnostics?.moonbridge_models.status ?? "n/a"} | ${diagnostics?.moonbridge_models.duration_ms ?? 0} ms`}
            />
            <DiagnosticCard
              title="Lark Auth"
              ok={Boolean(diagnostics?.lark_auth_status.ok)}
              body={diagnostics?.lark_auth_status.stdout || diagnostics?.lark_auth_status.stderr || "Not loaded"}
              footer={`exit ${diagnostics?.lark_auth_status.returncode ?? "n/a"} | ${diagnostics?.lark_auth_status.duration_ms ?? 0} ms`}
            />
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-slate-950">Operation Log</h2>
            <div className="mt-3 max-h-80 overflow-auto">
              {operations.length ? operations.map((operation, index) => (
                <div key={`${operation.timestamp}-${index}`} className="border-b border-slate-100 py-2 text-sm last:border-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-slate-900">{operation.component} {operation.action}</span>
                    <span className={operation.ok ? "text-emerald-700" : "text-red-700"}>{operation.ok ? "ok" : "failed"} | {operation.duration_ms} ms</span>
                  </div>
                  <p className="mt-1 text-slate-600">{operation.message}</p>
                </div>
              )) : <p className="text-sm text-slate-600">No operations yet.</p>}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-base font-semibold text-slate-950">Logs</h2>
              <div className="flex flex-wrap gap-2">
                <select className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm" value={selectedLog} onChange={(event) => loadLogs(event.target.value)}>
                  {logOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <select className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm" value={logLines} onChange={(event) => {
                  const next = Number(event.target.value);
                  setLogLines(next);
                  loadLogs(selectedLog, next);
                }}>
                  {[80, 120, 200, 400].map((value) => <option key={value} value={value}>{value} lines</option>)}
                </select>
                <ActionButton disabled={busy} icon={<FileText size={16} />} label="Refresh" onClick={() => loadLogs(selectedLog)} />
              </div>
            </div>
            <div className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-100">
              {logs ? logs.logs.map((log) => (
                <div key={log.path} className="mb-4 last:mb-0">
                  <div className="mb-2 text-slate-400">{log.path}</div>
                  <pre className="whitespace-pre-wrap">{log.lines.join("\n") || "(empty)"}</pre>
                </div>
              )) : <pre>Select a log.</pre>}
            </div>
          </div>
        </section>

        <footer className="flex items-center gap-2 pb-2 text-xs text-slate-500">
          <ShieldCheck size={14} />
          <span>Write actions require a local token and run only against 127.0.0.1.</span>
        </footer>
      </div>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
