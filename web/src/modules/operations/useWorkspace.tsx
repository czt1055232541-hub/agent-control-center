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

import { WatchdogCard, ConfigHealthCard, InfrastructureHealth, OperationLog, LogsPanel, CodexLiveStreamPanel, type ConfigContractStatus } from "./WorkspacePanels";
export function useWorkspace(token: string, page: string) {
  const { plugins, pluginsError } = usePluginInventory();
  const enabled = (id: string) => plugins.some((plugin) => plugin.id === id);
  const dashboardEnabled = enabled("acc.dashboard");
  const diagnosticsEnabled = enabled("acc.logs-diagnostics");
  const backupEnabled = enabled("acc.backup-migration");
  const providerEnabled = enabled("acc.model-provider");
  const configEnabled = enabled("acc.config-center");
  const { status, diagnostics, error: statusError, refresh, loadDiagnostics } = useStatus(dashboardEnabled, diagnosticsEnabled);
  const { operations, result, error, busy, run, setError, setResult } = useOperations(token, refresh, dashboardEnabled);
  const { logs, selectedLog, logLines, error: logsError, loadLogs, setSelectedLog, setLogLines } = useLogs(diagnosticsEnabled);
  const mig = useMigration(token, refresh);
  const { summary, agents, infrastructure, explainedDiagnostics, refreshDashboard } = useCommandDashboard(dashboardEnabled, enabled("acc.agent-array"), diagnosticsEnabled);
  const { watchdog, error: watchdogError, refreshWatchdog } = useWatchdog(enabled("acc.task-battlefield"));
  const codexStream = useCodexStream(diagnosticsEnabled && page === "diagnostics");
  const [configStatus, setConfigStatus] = React.useState<ConfigContractStatus | null>(null);
  const [selectedAgent, setSelectedAgent] = React.useState<AgentConfig | null>(null);
  React.useEffect(() => {
    if (backupEnabled && page === "provider") mig.loadThreads().catch(() => {});
    if (providerEnabled && page === "provider") mig.loadDeepSeekModels().catch(() => {});
  }, [page, backupEnabled, providerEnabled, mig.loadThreads, mig.loadDeepSeekModels]);

  React.useEffect(() => {
    if (!configEnabled || page !== "dashboard") return;
    readJson<ConfigContractStatus>("/api/config/status")
      .then(setConfigStatus)
      .catch((exc) => console.error("Configuration status check failed", exc));
  }, [configEnabled, page]);

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
  const providerInfrastructure = React.useMemo(
    () => infrastructure.filter((agent) => agent.id !== "codex-runtime"),
    [infrastructure],
  );
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



  return { token, status, diagnostics, statusError, result, error, busy, run, logsError, loadLogs, mig, summary, explainedDiagnostics, refreshDashboard, watchdogError, selectedAgent, setSelectedAgent, runAndRefresh, dashboardPanelItems, providerInfrastructureItems, diagnosticsItems, loadDiagnostics };
}

export function WorkspaceFrame({ workspace, children }: { workspace: ReturnType<typeof useWorkspace>; children: React.ReactNode }) {
  const { selectedAgent, token, setSelectedAgent, refreshDashboard, error, statusError, watchdogError, logsError, result } = workspace;
  const failure = error || statusError || watchdogError || logsError;
  return <>
    <AgentDrawer agent={selectedAgent} token={token} onClose={() => setSelectedAgent(null)} onSaved={refreshDashboard} />
    {failure ? <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{failure}</div> : null}
    {result ? <div role="status" className="rounded border p-3 text-sm">{result.component} {result.action}: {result.message}</div> : null}
    {children}
  </>;
}
