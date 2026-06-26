import { FolderOpen, Play, Power, RefreshCcw, Server, Terminal, XCircle } from "lucide-react";
import type { OperationResult, StackStatus, ThreadListItem, ThreadMigrationResult } from "../types";
import { ActionButton } from "./ActionButton";
import { StatusPill } from "./StatusPill";

export function CodexRuntimePanel({
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
  migrationResult: OperationResult | null;
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
  const isMigration = migrationResult?.component === "thread-migration";
  const mr = isMigration ? (migrationResult as ThreadMigrationResult) : null;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Codex Runtime</h2>
          <p className="mt-1 text-sm text-slate-600">
            Provider {providerMode} | Model {status?.codex.model ?? "unknown"} | PID{" "}
            {status?.codex_desktop.pid ?? "none"}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Agent{" "}
            {status?.codex_agent_follows_global_config
              ? "follows global config"
              : "uses a profile override"}{" "}
            | Args {status?.codex_agent_args ?? "unknown"}
          </p>
          <p className="mt-1 truncate text-xs text-slate-500">
            {status?.codex_desktop.executable ?? "Codex Desktop executable not detected"}
          </p>
        </div>
        <StatusPill active={running} label={running ? "Desktop Running" : "Desktop Stopped"} />
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Desktop</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <ActionButton
              disabled={busy || running}
              icon={<Play size={16} />}
              label="Start"
              onClick={() => run("/api/codex-desktop/start")}
            />
            {!confirmStop ? (
              <ActionButton
                disabled={busy || !running}
                danger
                icon={<Power size={16} />}
                label="Stop"
                onClick={() => setConfirmStop(true)}
              />
            ) : (
              <ActionButton
                disabled={busy}
                danger
                icon={<Power size={16} />}
                label="Confirm Stop"
                onClick={() => run("/api/codex-desktop/stop").then(() => setConfirmStop(false))}
              />
            )}
            {!confirmRestart ? (
              <ActionButton
                disabled={busy || !running}
                danger
                icon={<RefreshCcw size={16} />}
                label="Restart"
                onClick={() => setConfirmRestart(true)}
              />
            ) : (
              <ActionButton
                disabled={busy}
                danger
                icon={<RefreshCcw size={16} />}
                label="Confirm Restart"
                onClick={() =>
                  run("/api/codex-desktop/restart").then(() => setConfirmRestart(false))
                }
              />
            )}
            <ActionButton
              disabled={busy}
              icon={<Terminal size={16} />}
              label="Logs"
              onClick={() => loadLogs("codex-desktop")}
            />
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Provider</p>
          <div className="grid grid-cols-2 gap-2">
            <ActionButton
              disabled={busy || providerMode === "native"}
              icon={<Server size={16} />}
              label="Native"
              onClick={() => run("/api/codex-provider/native", loadDiagnostics)}
            />
            <ActionButton
              disabled={busy || providerMode === "moonbridge"}
              icon={<Server size={16} />}
              label="MoonBridge"
              onClick={() => run("/api/codex-provider/moonbridge", loadDiagnostics)}
            />
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
              {switchingModel ? (
                <p className="mt-1 text-xs text-slate-500">Switching model&hellip;</p>
              ) : null}
            </div>
          ) : null}
          {confirmStop || confirmRestart ? (
            <ActionButton
              disabled={busy}
              icon={<XCircle size={16} />}
              label="Cancel Desktop Action"
              onClick={() => {
                setConfirmStop(false);
                setConfirmRestart(false);
              }}
            />
          ) : null}
        </div>
      </div>

      <div className="mt-4 border-t border-slate-200 pt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          Thread Migration
        </p>
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
              run("/api/thread-migration/migrate", undefined, {
                session_id: migrationSessionId.trim(),
                target_provider: migrationTargetProvider,
                prompt: "Continue this work from the migrated context.",
              })
            }
          />
        </div>
        <div className="mt-3 rounded-md border border-slate-200">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Recent Threads
            </span>
            <span className="text-xs text-slate-500">{threads.length} items</span>
          </div>
          <div className="max-h-56 overflow-auto">
            {threads.length ? (
              threads.map((thread) => (
                <button
                  key={thread.session_id}
                  className="block w-full border-b border-slate-100 px-3 py-2 text-left last:border-0 hover:bg-slate-50"
                  type="button"
                  onClick={() => setMigrationSessionId(thread.session_id)}
                >
                  <div className="truncate text-sm font-medium text-slate-900">{thread.title}</div>
                  <div className="truncate text-xs text-slate-600">
                    {thread.provider} / {thread.model}
                  </div>
                  <div className="truncate text-xs text-slate-500">{thread.session_id}</div>
                </button>
              ))
            ) : (
              <div className="px-3 py-3 text-sm text-slate-500">No recent threads found.</div>
            )}
          </div>
        </div>
        {mr ? (
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <div>Thread title: {mr.source_title ?? "unknown"}</div>
            <div>Source session: {mr.source_session_id ?? "unknown"}</div>
            <div>Target provider: {mr.target_provider ?? "unknown"}</div>
            <div>Launch mode: {mr.launch_mode ?? "unknown"}</div>
            <div className="truncate">Summary: {mr.summary_path ?? "n/a"}</div>
            <div className="mt-3">
              <ActionButton
                disabled={busy || !mr.summary_path}
                icon={<FolderOpen size={16} />}
                label="Open Summary Folder"
                onClick={() =>
                  run("/api/thread-migration/open-summary-folder", undefined, {
                    summary_path: mr.summary_path,
                  })
                }
              />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
