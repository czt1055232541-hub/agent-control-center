import React from "react";
import { readJson } from "../api";
import type { AgentConfig, DashboardSummary, ExplainedDiagnosticItem } from "../types";

export function useCommandDashboard() {
  const [summary, setSummary] = React.useState<DashboardSummary | null>(null);
  const [agents, setAgents] = React.useState<AgentConfig[]>([]);
  const [infrastructure, setInfrastructure] = React.useState<AgentConfig[]>([]);
  const [explainedDiagnostics, setExplainedDiagnostics] = React.useState<ExplainedDiagnosticItem[]>([]);

  const refreshDashboard = React.useCallback(async () => {
    const [nextSummary, nextAgents, nextInfrastructure] = await Promise.all([
      readJson<DashboardSummary>("/api/dashboard/summary"),
      readJson<{ agents: AgentConfig[] }>("/api/agents"),
      readJson<{ agents: AgentConfig[] }>("/api/infrastructure"),
    ]);
    setSummary(nextSummary);
    setAgents(nextAgents.agents);
    setInfrastructure(nextInfrastructure.agents);
  }, []);

  const refreshExplainedDiagnostics = React.useCallback(async () => {
    const nextDiagnostics = await readJson<{ items: ExplainedDiagnosticItem[] }>("/api/diagnostics/explained");
    setExplainedDiagnostics(nextDiagnostics.items);
  }, []);

  React.useEffect(() => {
    refreshDashboard().catch(() => {});
    refreshExplainedDiagnostics().catch(() => {});
    const timer = window.setInterval(() => {
      refreshDashboard().catch(() => {});
    }, 5000);
    const diagnosticsTimer = window.setInterval(() => {
      refreshExplainedDiagnostics().catch(() => {});
    }, 30000);
    return () => {
      window.clearInterval(timer);
      window.clearInterval(diagnosticsTimer);
    };
  }, [refreshDashboard, refreshExplainedDiagnostics]);

  return { summary, agents, infrastructure, explainedDiagnostics, refreshDashboard };
}
