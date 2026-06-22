import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  FolderOpen,
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

type ThreadMigrationResult = OperationResult & {
  source_session_id?: string | null;
  source_title?: string | null;
  target_provider?: string | null;
  target_model?: string | null;
  summary_path?: string | null;
  summary_dir?: string | null;
  launched_command?: string | null;
  launch_mode?: string | null;
};

type ThreadListItem = {
  session_id: string;
  title: string;
  provider: string;
  model: string;
  updated_at: string;
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
  onOpenUi,
}: {
  component: ComponentStatus;
  title: string;
  disabled: boolean;
  onAction: (action: string) => void;
  onLogs: () => void;
  onOpenUi?: () => void;
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
        {onOpenUi ? <ActionButton disabled={disabled || !component.port} icon={<FolderOpen size={16} />} label="Open UI" onClick={onOpenUi} /> : null}
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
  migrationSessionId,
  migrationTargetProvider,
  migrationResult,
  threads,
  confirmStop,
  confirmRestart,
  availableModels,
  switchingModel,
  setMigrationSessionId,
  setMigrationTargetProvider,
  setConfirmStop,
  setConfirmRestart,
  run,
  loadLogs,
  loadDiagnostics,
  switchModel,
}: {
  status: StackStatus | null;
  providerMode: string;
  busy: boolean;
  migrationSessionId: string;
  migrationTargetProvider: string;
  migrationResult: ThreadMigrationResult | null;
  threads: ThreadListItem[];
  confirmStop: boolean;
  confirmRestart: boolean;
  availableModels: string[];
  switchingModel: boolean;
  setMigrationSessionId: (value: string) => void;
  setMigrationTargetProvider: (value: string) => void;
  setConfirmStop: (value: boolean) => void;
  setConfirmRestart: (value: boolean) => void;
  run: (path: string, after?: () => Promise<void>, body?: unknown) => Promise<void>;
  loadLogs: (component?: string, lines?: number) => Promise<void>;
  loadDiagnostics: () => Promise<void>;
  switchModel: (model: string) => Promise<void>;
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
          {providerMode === "moonbridge" && availableModels.length > 0 ? (
            <div className="mt-2">
              <select
                className="h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm"
                value={status?.codex.model ?? ""}
                disabled={busy || switchingModel}
                onChange={(event) => switchModel(event.target.value)}
              >
                {availableModels.map((modelName) => (
                  <option key={modelName} value={modelName}>
                    {modelName}
                  </option>
                ))}
              </select>
              {switchingModel ? <p className="mt-1 text-xs text-slate-500">Switching model&hellip;</p> : null}
            </div>
          ) : null}
          {(confirmStop || confirmRestart) ? (
            <ActionButton disabled={busy} icon={<XCircle size={16} />} label="Cancel Desktop Action" onClick={() => {
              setConfirmStop(false);
              setConfirmRestart(false);
            }} />
          ) : null}
        </div>
      </div>

      <div className="mt-4 border-t border-slate-200 pt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Thread Migration</p>
        <div className="grid gap-2 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
          <input
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
            placeholder="Session ID"
            type="text"
            value={migrationSessionId}
            onChange={(event) => setMigrationSessionId(event.target.value)}
          />
          <select
            className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm"
            value={migrationTargetProvider}
            onChange={(event) => setMigrationTargetProvider(event.target.value)}
          >
            <option value="native">Native</option>
            <option value="moonbridge">MoonBridge</option>
          </select>
          <ActionButton
            disabled={busy || !migrationSessionId.trim()}
            icon={<RefreshCcw size={16} />}
            label="Migrate Thread"
            onClick={() =>
              run(
                "/api/thread-migration/migrate",
                undefined,
                {
                  session_id: migrationSessionId.trim(),
                  target_provider: migrationTargetProvider,
                  prompt: "Continue this work from the migrated context.",
                },
              )
            }
          />
        </div>
        <div className="mt-3 rounded-md border border-slate-200">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Recent Threads</span>
            <span className="text-xs text-slate-500">{threads.length} items</span>
          </div>
          <div className="max-h-56 overflow-auto">
            {threads.length ? threads.map((thread) => (
              <button
                key={thread.session_id}
                className="block w-full border-b border-slate-100 px-3 py-2 text-left last:border-0 hover:bg-slate-50"
                type="button"
                onClick={() => setMigrationSessionId(thread.session_id)}
              >
                <div className="truncate text-sm font-medium text-slate-900">{thread.title}</div>
                <div className="truncate text-xs text-slate-600">{thread.provider} / {thread.model}</div>
                <div className="truncate text-xs text-slate-500">{thread.session_id}</div>
              </button>
            )) : (
              <div className="px-3 py-3 text-sm text-slate-500">No recent threads found.</div>
            )}
          </div>
        </div>
        {migrationResult?.component === "thread-migration" ? (
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <div>Thread title: {migrationResult.source_title ?? "unknown"}</div>
            <div>Source session: {migrationResult.source_session_id ?? "unknown"}</div>
            <div>Target provider: {migrationResult.target_provider ?? "unknown"}</div>
            <div>Launch mode: {migrationResult.launch_mode ?? "unknown"}</div>
            <div className="truncate">Summary: {migrationResult.summary_path ?? "n/a"}</div>
            <div className="mt-3">
              <ActionButton
                disabled={busy || !migrationResult.summary_path}
                icon={<FolderOpen size={16} />}
                label="Open Summary Folder"
                onClick={() =>
                  run(
                    "/api/thread-migration/open-summary-folder",
                    undefined,
                    { summary_path: migrationResult.summary_path },
                  )
                }
              />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function App() {
  const [token, setToken] = React.useState("");
  const [status, setStatus] = React.useState<StackStatus | null>(null);
  const [operations, setOperations] = React.useState<OperationRecord[]>([]);
  const [diagnostics, setDiagnostics] = React.useState<Diagnostics | null>(null);
  const [result, setResult] = React.useState<ThreadMigrationResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [logs, setLogs] = React.useState<{ component: string; logs: LogTail[] } | null>(null);
  const [selectedLog, setSelectedLog] = React.useState("operations");
  const [logLines, setLogLines] = React.useState(120);
  const [migrationSessionId, setMigrationSessionId] = React.useState("");
  const [migrationTargetProvider, setMigrationTargetProvider] = React.useState("moonbridge");
  const [threads, setThreads] = React.useState<ThreadListItem[]>([]);
  const [confirmDesktopStop, setConfirmDesktopStop] = React.useState(false);
  const [confirmDesktopRestart, setConfirmDesktopRestart] = React.useState(false);
  const [availableMoonbridgeModels, setAvailableMoonbridgeModels] = React.useState<string[]>([]);
  const [switchingMoonbridgeModel, setSwitchingMoonbridgeModel] = React.useState(false);

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

  const loadThreads = React.useCallback(async () => {
    const next = await readJson<{ threads: ThreadListItem[] }>("/api/thread-migration/threads?limit=20");
    setThreads(Array.isArray(next.threads) ? next.threads : []);
  }, []);

  const loadMoonbridgeModels = React.useCallback(async () => {
    try {
      const data = await readJson<{ models: string[] }>("/api/moonbridge/available-models");
      setAvailableMoonbridgeModels(data.models ?? []);
    } catch {
      setAvailableMoonbridgeModels([]);
    }
  }, []);

  const switchMoonbridgeModel = React.useCallback(async (model: string) => {
    if (!token) {
      setError("Control token is not ready.");
      return;
    }
    setSwitchingMoonbridgeModel(true);
    setError("");
    try {
      const next = await readJson<OperationResult>("/api/moonbridge/model/switch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: JSON.stringify({ model }),
      });
      setResult(next);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setSwitchingMoonbridgeModel(false);
    }
 }, [token, refresh]);

 const selectedLogRef = React.useRef(selectedLog);
 selectedLogRef.current = selectedLog;
  const logLinesRef = React.useRef(logLines);
  logLinesRef.current = logLines;

  const loadLogs = React.useCallback(async (component?: string, lines?: number) => {
    const comp = component ?? selectedLogRef.current;
    const lineCount = lines ?? logLinesRef.current;
    setError("");
    try {
      const result = await readJson<{ component: string; logs: LogTail[] }>(`/api/logs/${comp}?lines=${lineCount}`);
      setSelectedLog(comp);
      setLogs(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, []);

 React.useEffect(() => {
   readJson<{ token: string }>("/api/session")
     .then((session) => setToken(session.token))
     .catch((exc: Error) => setError(exc.message));
   refresh().catch((exc: Error) => setError(exc.message));
   loadDiagnostics().catch((exc: Error) => setError(exc.message));
   loadThreads().catch((exc: Error) => setError(exc.message));
   loadMoonbridgeModels().catch((exc: Error) => setError(exc.message));
   loadLogs("operations", 120).catch((exc: Error) => setError(exc.message));
    const statusTimer = window.setInterval(() => {
     refresh().catch((exc: Error) => setError(exc.message));
   }, 2000);
    const logTimer = window.setInterval(() => {
      loadLogs();
    }, 3000);
    return () => {
      window.clearInterval(statusTimer);
      window.clearInterval(logTimer);
    };
  }, []);

  async function run(path: string, after?: () => Promise<void>, body?: unknown) {
    if (!token) {
      setError("Control token is not ready.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await readJson<ThreadMigrationResult>(path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
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
            <h1 className="text-2xl font-semibold text-slate-950">Agent Control Center</h1>
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
                  onOpenUi={row.key === "openclaw" ? () => run("/api/openclaw/open-ui") : undefined}
                />
              ))
            : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <CodexRuntimePanel
            status={status}
            providerMode={providerMode}
            busy={busy}
            migrationSessionId={migrationSessionId}
            migrationTargetProvider={migrationTargetProvider}
            migrationResult={result}
            threads={threads}
            confirmStop={confirmDesktopStop}
            confirmRestart={confirmDesktopRestart}
            availableModels={availableMoonbridgeModels}
            switchingModel={switchingMoonbridgeModel}
            setMigrationSessionId={setMigrationSessionId}
            setMigrationTargetProvider={setMigrationTargetProvider}
            setConfirmStop={setConfirmDesktopStop}
            setConfirmRestart={setConfirmDesktopRestart}
            run={run}
            loadLogs={loadLogs}
            loadDiagnostics={loadDiagnostics}
            switchModel={switchMoonbridgeModel}
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
