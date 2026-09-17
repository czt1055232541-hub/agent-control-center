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

import { useWorkspace, WorkspaceFrame } from "../operations/useWorkspace";
import { StackActions, RawDiagnostics } from "../operations/WorkspacePanels";
export function ProviderPage({ token }: { token: string }) {
  const workspace = useWorkspace(token, 'provider');
  const { status, diagnostics, statusError, result, error, busy, run, logsError, loadLogs, mig, summary, explainedDiagnostics, refreshDashboard, watchdogError, selectedAgent, setSelectedAgent, runAndRefresh, dashboardPanelItems, providerInfrastructureItems, diagnosticsItems, loadDiagnostics } = workspace;
  return <WorkspaceFrame workspace={workspace}>
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
          </WorkspaceFrame>;
}
