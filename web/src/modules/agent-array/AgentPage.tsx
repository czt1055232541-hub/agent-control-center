import React from 'react';
import type { AgentProfile } from "../../types";
import { TopStatusBar } from "./skill-tree/TopStatusBar";
import { AgentCard as AdventureAgentCard } from "./skill-tree/AgentCard";
import { AgentDetailPanel } from "./skill-tree/AgentDetailPanel";
import { SkillWorkshopPage } from "./skill-tree/SkillWorkshopPage";
import { RecentRunsTable } from "./skill-tree/RecentRunsTable";
import { TaskTraceMap } from "./skill-tree/TaskTraceMap";
import { recentRunsFromOperations, taskTraceFromAgents, toAgentProfiles } from "./skill-tree/viewModels";
import { SortableGrid, type SortableGridItem } from '../../components/common/SortableGrid';
import { useCommandDashboard } from '../../hooks/useCommandDashboard';
import { useOperations } from '../../hooks/useOperations';
import { usePluginInventory } from '../../hooks/usePluginInventory';

export function AgentPage({ token }: { token: string }) {
  const { agents, refreshDashboard } = useCommandDashboard(false, true, false);
  const { plugins } = usePluginInventory();
  const { operations } = useOperations(token, refreshDashboard, plugins.some(p => p.id === 'acc.dashboard'));
  const [adventureSelectedAgent, setAdventureSelectedAgent] = React.useState<AgentProfile | null>(null);
  const [activeDetailTab, setActiveDetailTab] = React.useState<string>("概览");
  const currentTrace = React.useMemo(() => taskTraceFromAgents(agents), [agents]);
  const recentRuns = React.useMemo(() => recentRunsFromOperations(operations), [operations]);
  const adventureAgents = React.useMemo(() => toAgentProfiles(agents), [agents]);
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

  );
}
