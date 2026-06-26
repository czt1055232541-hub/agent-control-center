import React from "react";
import ReactDOM from "react-dom/client";
import { AlertTriangle, FileText, PauseCircle, Play, RefreshCcw, ShieldCheck, Wrench } from "lucide-react";
import "./styles.css";
import { componentRows, logOptions } from "./types";
import { ActionButton } from "./components/ActionButton";
import { StatusPill } from "./components/StatusPill";
import { ComponentPanel } from "./components/ComponentPanel";
import { DiagnosticCard } from "./components/DiagnosticCard";
import { CodexRuntimePanel } from "./components/CodexRuntimePanel";
import { useStatus } from "./hooks/useStatus";
import { useOperations } from "./hooks/useOperations";
import { useLogs } from "./hooks/useLogs";
import { useMigration } from "./hooks/useMigration";

function App() {
  const { token, status, diagnostics, refresh, loadDiagnostics } = useStatus();
  const { operations, result, error, busy, run, setError, setResult } = useOperations(token, refresh);
  const { logs, selectedLog, logLines, loadLogs, setSelectedLog, setLogLines } = useLogs();
  const mig = useMigration(token, refresh);

  // Wrap switchModel to use the operations error/result sinks
  const wrappedSwitchModel = React.useCallback(
    (model: string) => mig.switchModel(model, setError, setResult),
    [mig, setError, setResult],
  );

  // Initial data loads for threads and moonbridge models
  React.useEffect(() => {
    mig.loadThreads().catch(() => {});
    mig.loadMoonbridgeModels().catch(() => {});
  }, []);

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
            migrationSessionId={mig.migrationSessionId}
            migrationTargetProvider={mig.migrationTargetProvider}
            migrationResult={result}
            threads={mig.threads}
            confirmStop={mig.confirmDesktopStop}
            confirmRestart={mig.confirmDesktopRestart}
            availableModels={mig.availableMoonbridgeModels}
            switchingModel={mig.switchingMoonbridgeModel}
            setMigrationSessionId={mig.setMigrationSessionId}
            setMigrationTargetProvider={mig.setMigrationTargetProvider}
            setConfirmStop={mig.setConfirmDesktopStop}
            setConfirmRestart={mig.setConfirmDesktopRestart}
            run={run}
            loadLogs={loadLogs}
            loadDiagnostics={loadDiagnostics}
            switchModel={wrappedSwitchModel}
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
              <ActionButton disabled={busy} icon={<RefreshCcw size={16} />} label="Refresh" onClick={() => loadDiagnostics()} />
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
                <select className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm" value={selectedLog} onChange={(event) => setSelectedLog(event.target.value)}>
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
