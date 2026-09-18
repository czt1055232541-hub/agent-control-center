const owners: Record<string, string> = {
  "config-health": "acc.config-center",
  watchdog: "acc.task-battlefield",
  "agent-diagnostics": "acc.logs-diagnostics",
  "agent-topology": "acc.agent-array",
  infrastructure: "acc.dashboard",
};

export function visibleDashboardPanels<T extends { id: string }>(items: T[], enabledIds: string[]): T[] {
  const enabled = new Set(enabledIds);
  return items.filter(item => enabled.has(owners[item.id]));
}
