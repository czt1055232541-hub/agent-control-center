import React from "react";
import { AlertTriangle, FileText, PauseCircle, Play, Power, RefreshCcw, ShieldCheck, Wrench } from "lucide-react";
import { logOptions } from "../../types";
import { ActionButton } from "../../components/common/ActionButton";
import { StatusPill } from "../../components/common/StatusPill";
import { DiagnosticCard } from "../../components/common/DiagnosticCard";
import { CodexRuntimePanel } from "../../components/common/CodexRuntimePanel";
import { SortableGrid, type SortableGridItem } from "../../components/common/SortableGrid";
import { AgentCard } from "../../modules/agent-array/AgentCard";
import { AgentDrawer } from "../../modules/agent-array/AgentDrawer";
import { AgentTopology } from "../../modules/agent-array/AgentTopology";
import { DiagnosticCenter } from "../../modules/logs-diagnostics/DiagnosticCenter";
import { SummaryCards } from "../../modules/dashboard/SummaryCards";
import { statusClasses, statusLabel } from "../../components/common/statusStyles";
import { useStatus } from "../../hooks/useStatus";
import { useOperations } from "../../hooks/useOperations";
import { useLogs } from "../../hooks/useLogs";
import { useMigration } from "../../hooks/useMigration";
import { useCommandDashboard } from "../../hooks/useCommandDashboard";
import { useWatchdog } from "../../hooks/useWatchdog";
import { useCodexStream } from "../../hooks/useCodexStream";
import { usePluginInventory } from "../../hooks/usePluginInventory";
import type { AgentConfig, CodexStreamEvent, CodexStreamRun, CurrentWatchdogStatus } from "../../types";
import { readJson } from "../../api";

export type ConfigContractStatus = {
  ok: boolean;
  contract_version: number;
  peer_status: string;
  errors: Array<{ code: string; message: string }>;
  warnings: Array<{ code: string; message: string }>;
  drift: Array<{ field: string }>;
};

function formatCountdown(seconds: number | null): string {
  if (seconds === null || seconds === undefined) {
    return "未启用";
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `距离下次提醒 ${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export function WatchdogCard({
  watchdog,
  busy,
  run,
}: {
  watchdog: CurrentWatchdogStatus | null;
  busy: boolean;
  run: (path: string, after?: () => Promise<void>) => void;
}) {
  const [now, setNow] = React.useState(() => Date.now());

  React.useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const countdownSeconds = React.useMemo(() => {
    if (!watchdog?.enabled || !watchdog.next_check_at) {
      return watchdog?.enabled ? watchdog.countdown_seconds : null;
    }
    const nextAt = new Date(watchdog.next_check_at).getTime();
    if (Number.isNaN(nextAt)) {
      return watchdog.countdown_seconds;
    }
    return Math.max(0, Math.floor((nextAt - now) / 1000));
  }, [now, watchdog]);

  const isEnabled = Boolean(watchdog?.enabled);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Watchdog 看护</h2>
          <p className="mt-1 text-sm text-slate-600">绿色表示启用中，灰色表示已关闭。</p>
        </div>
        <ActionButton
          disabled={busy || !isEnabled}
          danger
          icon={<Power size={16} />}
          label="强制关闭"
          onClick={() => {
            if (window.confirm("强制关闭当前 watchdog？这会停止当前任务的自动看护提醒。")) {
              run("/api/watchdog/force-stop");
            }
          }}
        />
      </div>
      <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <span className={`inline-flex h-4 w-4 rounded-full ${isEnabled ? "bg-emerald-500" : "bg-slate-300"}`} />
          <div>
            <div className="text-sm font-medium text-slate-900">{isEnabled ? "启用中" : "已关闭"}</div>
            <div className="text-sm text-slate-600">{formatCountdown(countdownSeconds)}</div>
          </div>
        </div>
        <div className="text-xs text-slate-500">
          {watchdog?.task_id ? `TASK ${watchdog.task_id}` : "当前没有 active watchdog"}
          {watchdog?.phase ? ` · ${watchdog.phase}` : ""}
          {watchdog?.assignee ? ` · ${watchdog.assignee}` : ""}
        </div>
      </div>
    </section>
  );
}

export function ConfigHealthCard({ status }: { status: ConfigContractStatus | null }) {
  const healthy = Boolean(status?.ok && status.peer_status === "available" && status.drift.length === 0);
  return (
    <section className={`rounded-md border p-4 ${healthy ? "border-emerald-300 bg-emerald-50" : "border-amber-300 bg-amber-50"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">共享配置契约</h2>
          <p className="mt-1 text-sm text-slate-600">
            {status ? `v${status.contract_version} · Agent 配置 ${status.peer_status}` : "正在校验控制面与 Agent 运行配置…"}
          </p>
        </div>
        <span className="rounded border border-current px-2 py-1 text-xs">
          {status ? `${status.errors.length} 错误 / ${status.warnings.length} 警告 / ${status.drift.length} 漂移` : "检查中"}
        </span>
      </div>
      {status?.drift.length ? (
        <p className="mt-2 text-xs text-amber-900">漂移字段：{status.drift.map((item) => item.field).join("、")}。详细值仅在配置中心以脱敏形式提供。</p>
      ) : null}
    </section>
  );
}

export function InfrastructureHealth({ infrastructure, onSelect }: { infrastructure: AgentConfig[]; onSelect: (agent: AgentConfig) => void }) {
  const infrastructureItems = React.useMemo<SortableGridItem[]>(() => infrastructure.map((item) => ({
    id: item.id,
    node: (
      <button
        className="h-full w-full rounded-md border border-slate-200 bg-slate-50 p-3 text-left hover:bg-slate-100"
        onClick={() => onSelect(item)}
        type="button"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-slate-900">{item.name}</span>
          <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[11px] ${statusClasses(item.status)}`}>{statusLabel(item.status)}</span>
        </div>
        <div className="mt-2 text-xs text-slate-500">{item.pid ? `PID ${item.pid}` : "无进程"} · {item.port ? `Port ${item.port}` : "无端口"}</div>
      </button>
    ),
  })), [infrastructure, onSelect]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3">
        <h2 className="text-base font-semibold text-slate-950">基础设施健康摘要</h2>
        <p className="mt-1 text-sm text-slate-600">这些组件承载真实 Agent 能力，详细控制在“模型与 Provider”。</p>
      </div>
      <SortableGrid
        ariaLabel="Infrastructure cards"
        className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4"
        items={infrastructureItems}
        maxColSpan={3}
        storageKey="acc.dashboard.infrastructureLayout"
      />
    </section>
  );
}

export function StackActions({
  busy,
  run,
  loadDiagnostics,
  refreshDashboard,
}: {
  busy: boolean;
  run: (path: string, after?: () => Promise<void>) => void;
  loadDiagnostics: () => Promise<void>;
  refreshDashboard: () => Promise<void>;
}) {
  const afterStackAction = async () => {
    await loadDiagnostics();
    await refreshDashboard();
  };
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">Agent Stack Actions</h2>
      <p className="mt-1 text-sm text-slate-600">启动/停止 Feishu Codex Agent 栈；不会改变 ChatGPT/Codex App provider。</p>
      <div className="mt-4 grid gap-2">
        <ActionButton disabled={busy} icon={<Play size={16} />} label="Start Agent Stack (Native)" onClick={() => run("/api/stack/start-native", afterStackAction)} />
        <ActionButton disabled={busy} icon={<Play size={16} />} label="Start Agent Stack (DeepSeek)" onClick={() => run("/api/stack/start-deepseek", afterStackAction)} />
        <ActionButton disabled={busy} danger icon={<PauseCircle size={16} />} label="Stop Agent Stack" onClick={() => run("/api/stack/stop", afterStackAction)} />
      </div>
    </section>
  );
}

export function RawDiagnostics({
  busy,
  diagnostics,
  loadDiagnostics,
  run,
}: {
  busy: boolean;
  diagnostics: ReturnType<typeof useStatus>["diagnostics"];
  loadDiagnostics: () => Promise<void>;
  run: (path: string, after?: () => Promise<void>) => void;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Raw Diagnostics</h2>
          <p className="mt-1 text-sm text-slate-600">Codex doctor / DeepSeek env / Lark auth diagnostics</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ActionButton disabled={busy} icon={<RefreshCcw size={16} />} label="Refresh" onClick={() => loadDiagnostics()} />
          <ActionButton
            disabled={busy}
            danger
            icon={<Power size={16} />}
            label="Close Control Center"
            onClick={() => {
              if (window.confirm("Close Agent Control Center only? OpenClaw and Codex processes will remain running.")) {
                run("/api/control-center/shutdown");
              }
            }}
          />
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
          title="DeepSeek Env"
          ok={Boolean(diagnostics?.deepseek_env.ok)}
          body={
            diagnostics?.deepseek_env.present
              ? `${diagnostics.deepseek_env.env_key} is set`
              : diagnostics?.deepseek_env.error || "Not loaded"
          }
          footer={`${diagnostics?.deepseek_env.base_url ?? "n/a"} | ${diagnostics?.deepseek_env.duration_ms ?? 0} ms`}
        />
        <DiagnosticCard
          title="Lark Auth"
          ok={Boolean(diagnostics?.lark_auth_status.ok)}
          body={diagnostics?.lark_auth_status.stdout || diagnostics?.lark_auth_status.stderr || "Not loaded"}
          footer={`exit ${diagnostics?.lark_auth_status.returncode ?? "n/a"} | ${diagnostics?.lark_auth_status.duration_ms ?? 0} ms`}
        />
      </div>
    </section>
  );
}

export function LogsPanel({
  busy,
  logs,
  selectedLog,
  logLines,
  loadLogs,
  setSelectedLog,
  setLogLines,
}: {
  busy: boolean;
  logs: ReturnType<typeof useLogs>["logs"];
  selectedLog: string;
  logLines: number;
  loadLogs: (component?: string, lines?: number) => Promise<void>;
  setSelectedLog: (component: string) => void;
  setLogLines: (lines: number) => void;
}) {
  return (
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
  );
}

export function CodexLiveStreamPanel({
  runs,
  runId,
  events,
  connected,
  error,
  setRunId,
  refresh,
}: {
  runs: CodexStreamRun[];
  runId: string;
  events: CodexStreamEvent[];
  connected: boolean;
  error: string | null;
  setRunId: (runId: string) => void;
  refresh: () => Promise<void>;
}) {
  const latest = runs[0];
  const lastEvent = events.at(-1);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Codex Live Stream</h2>
          <p className="mt-1 text-xs text-slate-500">
            {connected ? "WebSocket connected" : "WebSocket reconnecting"} · {lastEvent?.timestamp ?? latest?.updated_at ?? "no stream yet"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm" value={runId} onChange={(event) => setRunId(event.target.value)}>
            <option value="latest">latest</option>
            {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id} · {run.status}</option>)}
          </select>
          <ActionButton disabled={false} icon={<RefreshCcw size={16} />} label="Refresh" onClick={refresh} />
        </div>
      </div>
      {error ? <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">{error}</div> : null}
      <div className="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-100">
        {events.length ? events.map((event, index) => (
          <div key={`${event.run_id}-${event.timestamp}-${index}`} className={event.stream === "stderr" || event.phase === "error" ? "text-rose-300" : event.stream === "stdout" ? "text-sky-200" : "text-emerald-200"}>
            <span className="text-slate-500">{event.timestamp ?? "--"} </span>
            <span>[{event.phase}/{event.stream}] </span>
            <span className="whitespace-pre-wrap">{event.text}</span>
          </div>
        )) : <pre className="text-slate-400">No Codex subprocess stream has been recorded yet.</pre>}
      </div>
    </div>
  );
}

export function OperationLog({ operations }: { operations: ReturnType<typeof useOperations>["operations"] }) {
  return (
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
  );
}
