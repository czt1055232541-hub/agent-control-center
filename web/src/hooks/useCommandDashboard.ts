import React from "react";
import { readJson } from "../api";
import type { AgentConfig, DashboardSummary, ExplainedDiagnosticItem } from "../types";

async function readOptional<T>(path: string): Promise<T | null> {
  try {
    return await readJson<T>(path);
  } catch {
    return null;
  }
}

export function useCommandDashboard() {
  const [summary, setSummary] = React.useState<DashboardSummary | null>(null);
  const [agents, setAgents] = React.useState<AgentConfig[]>([]);
  const [infrastructure, setInfrastructure] = React.useState<AgentConfig[]>([]);
  const [explainedDiagnostics, setExplainedDiagnostics] = React.useState<ExplainedDiagnosticItem[]>([]);

  const refreshDashboard = React.useCallback(async () => {
    const [nextSummary, nextAgents, nextInfrastructure] = await Promise.all([
      readOptional<DashboardSummary>("/api/dashboard/summary"),
      readOptional<{ agents: AgentConfig[] }>("/api/agents"),
      readOptional<{ agents: AgentConfig[] }>("/api/infrastructure"),
    ]);
    if (nextSummary) setSummary(nextSummary);
    if (nextAgents) setAgents(nextAgents.agents);
    if (nextInfrastructure) setInfrastructure(nextInfrastructure.agents);
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
    }, 2000);
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
