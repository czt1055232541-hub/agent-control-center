import React from "react";
import ReactDOM from "react-dom/client";
import { AlertTriangle, FileText, PauseCircle, Play, Power, RefreshCcw, ShieldCheck, Wrench } from "lucide-react";
import "./styles.css";
import { logOptions } from "../types";
import type { AgentProfile } from "../types";
import { TopStatusBar } from "../modules/agent-array/skill-tree/TopStatusBar";
import { AgentCard as AdventureAgentCard } from "../modules/agent-array/skill-tree/AgentCard";
import { AgentDetailPanel } from "../modules/agent-array/skill-tree/AgentDetailPanel";
import { SkillWorkshopPage } from "../modules/agent-array/skill-tree/SkillWorkshopPage";
import { RecentRunsTable } from "../modules/agent-array/skill-tree/RecentRunsTable";
import { TaskTraceMap } from "../modules/agent-array/skill-tree/TaskTraceMap";
import { clientRegistry } from "../plugins/clientPlugins";
import { recentRunsFromOperations, taskTraceFromAgents, toAgentProfiles } from "../modules/agent-array/skill-tree/viewModels";
import { ActionButton } from "../components/common/ActionButton";
import { StatusPill } from "../components/common/StatusPill";
import { DiagnosticCard } from "../components/common/DiagnosticCard";
import { CodexRuntimePanel } from "../components/common/CodexRuntimePanel";
import { SortableGrid, type SortableGridItem } from "../components/common/SortableGrid";
import { AgentCard } from "../modules/agent-array/AgentCard";
import { AgentDrawer } from "../modules/agent-array/AgentDrawer";
import { AgentTopology } from "../modules/agent-array/AgentTopology";
import { DiagnosticCenter } from "../modules/logs-diagnostics/DiagnosticCenter";
import { Sidebar, type CommandPage } from "./Sidebar";
import { SummaryCards } from "../modules/dashboard/SummaryCards";
import { statusClasses, statusLabel } from "../components/common/statusStyles";
import { useStatus } from "../hooks/useStatus";
import { useOperations } from "../hooks/useOperations";
import { useLogs } from "../hooks/useLogs";
import { useMigration } from "../hooks/useMigration";
import { useCommandDashboard } from "../hooks/useCommandDashboard";
import { useWatchdog } from "../hooks/useWatchdog";
import { useCodexStream } from "../hooks/useCodexStream";
import { usePluginInventory } from "../hooks/usePluginInventory";
import { PluginDetailPage } from "../modules/plugin-catalog/PluginDetailPage";
import type { AgentConfig, CodexStreamEvent, CodexStreamRun, CurrentWatchdogStatus } from "../types";
import { AppErrorBoundary } from "../components/common/AppErrorBoundary";
import { readJson } from "../api";

type ConfigContractStatus = {
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

function WatchdogCard({
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

function ConfigHealthCard({ status }: { status: ConfigContractStatus | null }) {
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

function InfrastructureHealth({ infrastructure, onSelect }: { infrastructure: AgentConfig[]; onSelect: (agent: AgentConfig) => void }) {
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

function StackActions({
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

function RawDiagnostics({
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
          <ActionButton disabled={busy} icon={<Wrench size={16} />} label="Clean Backups" onClick={() => run("/api/backups/clean", loadDiagnostics)} />
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

function LogsPanel({
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

function CodexLiveStreamPanel({
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

function OperationLog({ operations }: { operations: ReturnType<typeof useOperations>["operations"] }) {
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

function PlannedPage({ page }: { page: CommandPage }) {
  const plans: Record<CommandPage, { title: string; stage: string; dependencies: string[]; next: string[] }> = {
    dashboard: { title: "Dashboard 总览", stage: "已实现", dependencies: [], next: [] },
    agents: { title: "Agent 管理", stage: "已实现", dependencies: [], next: [] },
    provider: { title: "模型与 Provider", stage: "已实现", dependencies: [], next: [] },
    diagnostics: { title: "日志与诊断", stage: "已实现", dependencies: [], next: [] },
    tasks: {
      title: "任务监控",
      stage: "后续阶段",
      dependencies: ["OpenClaw 会话事件流", "Codex Agent 生成状态事件", "任务 ID 与消息 ID 关联"],
      next: ["定义任务事件 schema", "接入 sessions.json 增量读取", "补充生成中/排队/完成状态"],
    },
    feishu: {
      title: "飞书连接",
      stage: "后续阶段",
      dependencies: ["Lark auth status", "OpenClaw channel accounts", "Codex Agent bot env"],
      next: ["展示账号启用状态", "增加权限缺失诊断", "只读展示 chat/app/openId 脱敏摘要"],
    },
    routing: {
      title: "路由规则",
      stage: "后续阶段",
      dependencies: ["OpenClaw bindings", "A2A_BOTS", "群聊触发规则"],
      next: ["解析调度规则", "展示 @ 名称到 Agent 的映射", "设计只读冲突检查"],
    },
    config: {
      title: "配置中心",
      stage: "开发中",
      dependencies: ["当前 Agent 管理页的白名单写入 API", "配置备份目录", "脱敏 diff"],
      next: ["将更多低风险字段纳入白名单", "提供全局配置预览", "增加 schema 说明"],
    },
    backup: {
      title: "备份与迁移",
      stage: "后续阶段",
      dependencies: ["runtime/config-versions", "线程迁移 API", "备份清理 API"],
      next: ["列出配置版本", "支持选择版本回滚", "整合 Codex thread migration 结果"],
    },
  };
  const plan = plans[page];
  const plannedItems = React.useMemo<SortableGridItem[]>(() => [
    {
      id: "dependencies",
      node: (
        <div className="h-full rounded-md border border-slate-200 bg-slate-50 p-3">
          <h3 className="text-sm font-medium text-slate-900">依赖数据源</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            {plan.dependencies.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      ),
    },
    {
      id: "next",
      node: (
        <div className="h-full rounded-md border border-slate-200 bg-slate-50 p-3">
          <h3 className="text-sm font-medium text-slate-900">阶段任务</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            {plan.next.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      ),
    },
  ], [plan]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{plan.title}</h2>
          <p className="mt-1 text-sm text-slate-600">当前阶段：{plan.stage}。这里保留导航入口，但不放占位控件或不可用按钮。</p>
        </div>
        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">{plan.stage}</span>
      </div>
      <SortableGrid
        ariaLabel="Planned page cards"
        className="mt-4 grid gap-4 lg:grid-cols-2"
        items={plannedItems}
        maxColSpan={2}
        storageKey={`acc.${page}.plannedLayout`}
      />
    </section>
  );
}

function App() {
  const { plugins, pluginsError } = usePluginInventory();
  const enabled = (id: string) => plugins.some((plugin) => plugin.id === id);
  const dashboardEnabled = enabled("acc.dashboard");
  const diagnosticsEnabled = enabled("acc.logs-diagnostics");
  const backupEnabled = enabled("acc.backup-migration");
  const providerEnabled = enabled("acc.model-provider");
  const configEnabled = enabled("acc.config-center");
  const { token, status, diagnostics, error: statusError, refresh, loadDiagnostics } = useStatus(dashboardEnabled, diagnosticsEnabled);
  const { operations, result, error, busy, run, setError, setResult } = useOperations(token, refresh, dashboardEnabled);
  const { logs, selectedLog, logLines, error: logsError, loadLogs, setSelectedLog, setLogLines } = useLogs(diagnosticsEnabled);
  const mig = useMigration(token, refresh);
  const { summary, agents, infrastructure, explainedDiagnostics, refreshDashboard } = useCommandDashboard(dashboardEnabled, enabled("acc.agent-array"), diagnosticsEnabled);
  const { watchdog, error: watchdogError, refreshWatchdog } = useWatchdog(enabled("acc.task-battlefield"));
  const codexStream = useCodexStream(diagnosticsEnabled);
  const [configStatus, setConfigStatus] = React.useState<ConfigContractStatus | null>(null);
  const [selectedAgent, setSelectedAgent] = React.useState<AgentConfig | null>(null);
  const [requestedPage, setActivePage] = React.useState<CommandPage>("dashboard");
  const availableCards = plugins.flatMap((plugin) => plugin.cards).sort((a, b) => a.order - b.order);
  const activePage = availableCards.some((card) => card.page === requestedPage)
    ? requestedPage
    : availableCards[0]?.page ?? "__no_plugins__";
  const PluginPage = clientRegistry.resolve(activePage, plugins);
  const [adventureSelectedAgent, setAdventureSelectedAgent] = React.useState<AgentProfile | null>(null);
  const [activeDetailTab, setActiveDetailTab] = React.useState<string>("概览");

  React.useEffect(() => {
    if (backupEnabled) mig.loadThreads().catch(() => {});
    if (providerEnabled) mig.loadDeepSeekModels().catch(() => {});
  }, [backupEnabled, providerEnabled, mig.loadThreads, mig.loadDeepSeekModels]);

  React.useEffect(() => {
    if (!configEnabled) return;
    readJson<ConfigContractStatus>("/api/config/status")
      .then(setConfigStatus)
      .catch((exc) => console.error("Configuration status check failed", exc));
  }, [configEnabled]);

  const appProviderMode = status?.codex_app?.mode ?? status?.codex.mode ?? "unknown";
  const agentProviderMode = status?.codex_agent_provider?.mode ?? status?.codex.mode ?? "unknown";
  const runAndRefresh = React.useCallback(
    (path: string) =>
      run(path, async () => {
        await refreshDashboard();
        await refreshWatchdog();
      }),
    [run, refreshDashboard, refreshWatchdog],
  );
  const adventureAgents = React.useMemo(() => toAgentProfiles(agents), [agents]);
  const providerInfrastructure = React.useMemo(
    () => infrastructure.filter((agent) => agent.id !== "codex-runtime"),
    [infrastructure],
  );
  const recentRuns = React.useMemo(() => recentRunsFromOperations(operations), [operations]);
  const currentTrace = React.useMemo(() => taskTraceFromAgents(agents), [agents]);
  const dashboardPanelItems = React.useMemo<SortableGridItem[]>(() => [
    {
      id: "config-health",
      node: <ConfigHealthCard status={configStatus} />,
    },
    {
      id: "watchdog",
      node: (
        <WatchdogCard
          watchdog={watchdog}
          busy={busy}
          run={(path, after) =>
            run(path, async () => {
              await refreshDashboard();
              await refreshWatchdog();
              await after?.();
            })
          }
        />
      ),
    },
    {
      id: "agent-diagnostics",
      className: "xl:col-span-2",
      node: (
        <section className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)]">
          <AgentTopology agents={agents} onSelect={setSelectedAgent} />
          <DiagnosticCenter items={explainedDiagnostics} busy={busy} onRun={runAndRefresh} onLogs={(component) => loadLogs(component)} />
        </section>
      ),
    },
    {
      id: "infrastructure",
      className: "xl:col-span-2",
      node: <InfrastructureHealth infrastructure={infrastructure} onSelect={setSelectedAgent} />,
    },
  ], [
    agents,
    busy,
    configStatus,
    explainedDiagnostics,
    infrastructure,
    loadLogs,
    refreshDashboard,
    refreshWatchdog,
    run,
    runAndRefresh,
    watchdog,
  ]);
  const adventureAgentItems = React.useMemo<SortableGridItem[]>(() => adventureAgents.map((agent) => ({
    id: agent.id,
    node: (
      <AdventureAgentCard
        agent={agent}
        selected={adventureSelectedAgent?.id === agent.id}
        onSelect={(nextAgent) => setAdventureSelectedAgent(nextAgent)}
      />
    ),
  })), [adventureAgents, adventureSelectedAgent?.id]);
  const providerInfrastructureItems = React.useMemo<SortableGridItem[]>(() => providerInfrastructure.map((agent) => ({
    id: agent.id,
    node: (
      <AgentCard
        agent={agent}
        busy={busy}
        onRun={runAndRefresh}
        onLogs={(component) => loadLogs(component)}
        onSelect={setSelectedAgent}
      />
    ),
  })), [busy, loadLogs, providerInfrastructure, runAndRefresh]);
  const diagnosticsItems = React.useMemo<SortableGridItem[]>(() => [
    {
      id: "operation-log",
      node: <OperationLog operations={operations} />,
    },
    {
      id: "logs-panel",
      node: (
        <LogsPanel
          busy={busy}
          logs={logs}
          selectedLog={selectedLog}
          logLines={logLines}
          loadLogs={loadLogs}
          setSelectedLog={setSelectedLog}
          setLogLines={setLogLines}
        />
      ),
    },
    {
      id: "codex-live-stream",
      defaultSize: { colSpan: 2, rowSpan: 1 },
      node: (
        <CodexLiveStreamPanel
          runs={codexStream.runs}
          runId={codexStream.runId}
          events={codexStream.events}
          connected={codexStream.connected}
          error={codexStream.error}
          setRunId={(next) => {
            codexStream.setRunId(next);
            codexStream.loadStream(next).catch(() => {});
          }}
          refresh={async () => {
            await codexStream.loadRuns();
            await codexStream.loadStream(codexStream.runId);
          }}
        />
      ),
    },
  ], [busy, codexStream, loadLogs, logLines, logs, operations, selectedLog]);

  React.useEffect(() => {
    if (!adventureAgents.length) {
      setAdventureSelectedAgent(null);
      return;
    }
    setAdventureSelectedAgent((current) => {
      const next = adventureAgents.find((agent) => agent.id === current?.id) ?? adventureAgents[0];
      return next;
    });
  }, [adventureAgents]);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <AgentDrawer agent={selectedAgent} token={token} onClose={() => setSelectedAgent(null)} onSaved={refreshDashboard} />
      <div className="grid w-full gap-5 px-5 py-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Sidebar activePage={activePage} onNavigate={setActivePage} plugins={plugins} />
        <div className="flex min-w-0 flex-col gap-5">
          <header className="flex flex-col gap-4 border-b border-slate-300 pb-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-950">多 Agent 作战指挥台</h1>
              <p className="mt-1 text-sm text-slate-600">{status?.stack_root ?? "Loading stack status..."}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusPill active={appProviderMode === "deepseek"} label={`App: ${appProviderMode}`} />
              <StatusPill active={agentProviderMode === "deepseek"} label={`Agent: ${agentProviderMode}`} />
              <StatusPill active={Boolean(status?.codex_desktop_running)} label="Codex Desktop" />
            </div>
          </header>

          {error ?? statusError ?? watchdogError ?? logsError ?? pluginsError ? (
            <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span>{error ?? statusError ?? watchdogError ?? logsError ?? pluginsError}</span>
            </div>
          ) : null}

          {result ? (
            <div className={`rounded-md border p-3 text-sm ${result.ok ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900"}`}>
              <strong>{result.component} {result.action}</strong>: {result.message} ({result.duration_ms} ms)
            </div>
          ) : null}

          {activePage === "dashboard" ? (
            <>
              <SummaryCards summary={summary} />
              <SortableGrid
                ariaLabel="Dashboard panels"
                className="grid gap-4 xl:grid-cols-2"
                items={dashboardPanelItems}
                storageKey="acc.dashboard.panelOrder"
              />
            </>
          ) : null}

          {activePage === "agents" ? (
            <div className="flex flex-col gap-4">
              <TopStatusBar
                totalAgents={adventureAgents.length}
                onlineAgents={adventureAgents.filter(a => a.status === "online" || a.status === "running").length}
                runningAgents={adventureAgents.filter(a => a.status === "running").length}
                taskQueue={adventureAgents.filter(a => a.status === "running").length}
                dailyTokens={0}
                tokenBudget={0}
                tokensPercent={0}
              />
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <h2 className="text-base font-semibold" style={{color:'var(--text-main)'}}>Agent 阵容</h2>
                  <span className="rounded px-2 py-0.5 text-xs" style={{background:'var(--bg-panel-soft)',color:'var(--text-muted)',border:'1px solid var(--border-light)'}}>
                    {adventureAgents.length} 个真实角色
                  </span>
                </div>
                <SortableGrid
                  ariaLabel="Agent cards"
                  className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
                  items={adventureAgentItems}
                  maxColSpan={3}
                  storageKey="acc.agents.cardLayout"
                />
              </div>
              <AgentDetailPanel
                agent={adventureSelectedAgent}
                activeTab={activeDetailTab as any}
                onTabChange={(tab) => setActiveDetailTab(tab)}
              />
              <div>
                <SkillWorkshopPage
                  agents={agents}
                  adventureSelectedAgent={adventureSelectedAgent}
                  token={token}
                />
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <RecentRunsTable runs={recentRuns} onSelectRun={() => {}} />
                <TaskTraceMap trace={currentTrace} />
              </div>
            </div>
          ) : null}

          {PluginPage ? <PluginPage token={token} /> : null}

          {activePage === "provider" ? (
            <>
              <SortableGrid
                ariaLabel="Provider cards"
                className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-4"
                items={providerInfrastructureItems}
                storageKey="acc.provider.cardLayout"
              />
              <div className="grid gap-4 lg:grid-cols-3">
                <CodexRuntimePanel
                  status={status}
                  busy={busy}
                  migrationSessionId={mig.migrationSessionId}
                  migrationTargetProvider={mig.migrationTargetProvider}
                  migrationResult={result}
                  threads={mig.threads}
                  confirmStop={mig.confirmDesktopStop}
                  confirmRestart={mig.confirmDesktopRestart}
                  availableModels={mig.availableDeepSeekModels}
                  switchingModel={mig.switchingDeepSeekModel}
                  setMigrationSessionId={mig.setMigrationSessionId}
                  setMigrationTargetProvider={mig.setMigrationTargetProvider}
                  setConfirmStop={mig.setConfirmDesktopStop}
                  setConfirmRestart={mig.setConfirmDesktopRestart}
                  run={run}
                  loadLogs={loadLogs}
                  loadDiagnostics={loadDiagnostics}
                />
                <StackActions busy={busy} run={run} loadDiagnostics={loadDiagnostics} refreshDashboard={refreshDashboard} />
              </div>
            </>
          ) : null}

          {activePage === "diagnostics" ? (
            <>
              <DiagnosticCenter items={explainedDiagnostics} busy={busy} onRun={runAndRefresh} onLogs={(component) => loadLogs(component)} />
              <RawDiagnostics busy={busy} diagnostics={diagnostics} loadDiagnostics={loadDiagnostics} run={run} />
              <SortableGrid
                ariaLabel="Diagnostics panels"
                className="grid gap-4 lg:grid-cols-2"
                items={diagnosticsItems}
                storageKey="acc.diagnostics.panelLayout"
              />
            </>
          ) : null}

          {activePage === "backup" ? (
            <PlannedPage page={activePage} />
          ) : null}

          {!PluginPage && !new Set(["dashboard", "agents", "provider", "diagnostics", "backup"]).has(activePage) ? (
            <PluginDetailPage plugin={plugins.find((plugin) => plugin.cards.some((card) => card.page === activePage)) ?? null} />
          ) : null}

          <footer className="flex items-center gap-2 pb-2 text-xs text-slate-500">
            <ShieldCheck size={14} />
            <span>Write actions require a local token and run only against 127.0.0.1.</span>
          </footer>
        </div>
      </div>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <React.Suspense fallback={<main className="min-h-screen bg-slate-100 p-6 text-slate-600">正在加载控制中心…</main>}>
        <App />
      </React.Suspense>
    </AppErrorBoundary>
  </React.StrictMode>,
);
