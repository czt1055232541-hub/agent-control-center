import React from "react";
import {
  BarChart3, GitBranch, AlertTriangle, FileText,
  CheckCircle, Info, AlertOctagon, ShieldAlert, RotateCw,
} from "lucide-react";
import type { AgentSkill, AgentProfile, SkillWorkshopTab } from "../../../types";
import { SkillTreeCanvas } from "./SkillTreeCanvas";
import { SkillInventoryTable } from "./SkillInventoryTable";
import { SkillDriftReportPanel } from "./SkillDriftReportPanel";
import { SkillRuntimeComparison } from "./SkillRuntimeComparison";
import { useSkillWorkshop, type SkillWorkshopState } from "../../../hooks/useSkillWorkshop";
import { toAgentProfiles } from "./viewModels";
import type { AgentConfig } from "../../../types";

const tabs: { key: SkillWorkshopTab; label: string; icon: React.ReactNode }[] = [
  { key: "overview", label: "\u6982\u89c8", icon: <BarChart3 size={14} /> },
  { key: "skill-tree", label: "\u6280\u80fd\u6811", icon: <GitBranch size={14} /> },
  { key: "comparison", label: "\u7248\u672c\u5bf9\u6bd4", icon: <FileText size={14} /> },
  { key: "drift-report", label: "\u6f02\u79fb\u62a5\u544a", icon: <AlertTriangle size={14} /> },
];

interface SkillWorkshopPageProps {
  agents: AgentConfig[];
  adventureSelectedAgent: AgentProfile | null;
  selectedSkill: AgentSkill | null;
  onSelectSkill: (skill: AgentSkill | null) => void;
}

export function SkillWorkshopPage({
  agents,
  adventureSelectedAgent,
  selectedSkill,
  onSelectSkill,
}: SkillWorkshopPageProps) {
  const [activeTab, setActiveTab] = React.useState<SkillWorkshopTab>("overview");
  const ws = useSkillWorkshop();

  const isFallback = !ws.backendAvailable && ws.consecutiveFailures >= 3;
  const adventureAgents = React.useMemo(() => toAgentProfiles(agents), [agents]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            \u6280\u80fd\u6811\u5de5\u574a
          </h3>
          {ws.loading && (
            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
              <RotateCw size={12} className="animate-spin" />
              \u52a0\u8f7d\u4e2d...
            </span>
          )}
          {isFallback && (
            <span
              className="rounded px-2 py-0.5 text-xs font-medium"
              style={{ background: "#fff3cd", border: "1px solid #ffc107", color: "#856404" }}
            >
              \u9759\u6001\u6f14\u793a / \u540e\u7aef\u4e0d\u53ef\u7528
            </span>
          )}
        </div>
        {!isFallback && !ws.loading && ws.summary && (
          <button
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors hover:bg-black/5"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--border-light)" }}
            onClick={() => ws.refresh()}
          >
            <RotateCw size={12} />
            \u5237\u65b0
          </button>
        )}
      </div>

      <div className="flex gap-1 border-b" style={{ borderColor: "var(--border-light)" }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className="flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-xs font-medium transition-all"
            style={{
              color: activeTab === tab.key ? "var(--accent-teal)" : "var(--text-secondary)",
              borderBottom: activeTab === tab.key ? "2px solid var(--accent-teal)" : "2px solid transparent",
              background: activeTab === tab.key ? "rgba(24,166,166,0.06)" : "transparent",
            }}
          >
            {tab.icon}
            {tab.label}
            {tab.key === "drift-report" && ws.driftReport && ws.driftReport.summary.driftCount > 0 && (
              <span
                className="flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold text-white"
                style={{ background: "var(--accent-red)" }}
              >
                {ws.driftReport.summary.driftCount}
              </span>
            )}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "overview" && (
          <WorkshopOverview ws={ws} isFallback={isFallback} adventureAgents={adventureAgents} />
        )}
        {activeTab === "skill-tree" && (
          isFallback ? (
            <SkillTreeCanvas
              agent={adventureSelectedAgent}
              selectedSkill={selectedSkill}
              onSelectSkill={onSelectSkill}
            />
          ) : (
            <WorkshopSkillTree
              ws={ws}
              adventureSelectedAgent={adventureSelectedAgent}
              selectedSkill={selectedSkill}
              onSelectSkill={onSelectSkill}
            />
          )
        )}
        {activeTab === "comparison" && (
          isFallback ? (
            <StaticComparisonPlaceholder adventureAgents={adventureAgents} />
          ) : (
            <SkillRuntimeComparison comparisons={ws.comparisonData} loading={ws.loading} />
          )
        )}
        {activeTab === "drift-report" && (
          isFallback ? (
            <StaticDriftPlaceholder />
          ) : (
            <SkillDriftReportPanel report={ws.driftReport} loading={ws.loading} />
          )
        )}
      </div>
    </div>
  );
}

function WorkshopOverview({
  ws,
  isFallback,
  adventureAgents,
}: {
  ws: SkillWorkshopState;
  isFallback: boolean;
  adventureAgents: AgentProfile[];
}) {
  if (isFallback) {
    const totalSkills = adventureAgents.reduce((sum, a) => sum + a.totalSkills, 0);
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <OverviewCard icon={<GitBranch size={18} />} label="\u6280\u80fd\u603b\u6570" value={String(totalSkills)} color="var(--accent-blue)" />
        <OverviewCard icon={<CheckCircle size={18} />} label="Agent \u6570\u91cf" value={String(adventureAgents.length)} color="var(--accent-green)" />
        <OverviewCard icon={<Info size={18} />} label="\u6570\u636e\u6e90" value="\u9759\u6001\u6f14\u793a" sub="viewModels.ts" color="var(--accent-gold)" />
        <OverviewCard icon={<AlertOctagon size={18} />} label="\u72b6\u6001" value="\u540e\u7aef\u4e0d\u53ef\u7528" sub="\u5df2\u5207\u6362\u81f3\u9759\u6001\u6a21\u5f0f" color="var(--accent-orange)" />
      </div>
    );
  }

  if (ws.loading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-lg p-4"
            style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}
          >
            <div className="mb-2 h-4 w-16 rounded" style={{ background: "var(--border-stone)" }} />
            <div className="h-8 w-12 rounded" style={{ background: "var(--border-stone)" }} />
          </div>
        ))}
      </div>
    );
  }

  const s = ws.summary;
  if (!s) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <OverviewCard icon={<GitBranch size={18} />} label="\u6280\u80fd\u603b\u6570" value={String(s.totalSkills)}
          sub={s.lastScanTime ? `\u6700\u540e\u626b\u63cf: ${new Date(s.lastScanTime).toLocaleTimeString()}` : "\u5c1a\u672a\u626b\u63cf"}
          color="var(--accent-blue)" />
        <OverviewCard icon={<AlertTriangle size={18} />} label="\u6f02\u79fb\u6280\u80fd" value={String(s.driftCount)}
          sub={s.driftCount > 0 ? "\u9700\u8981\u5173\u6ce8" : "\u5168\u90e8\u6b63\u5e38"}
          color={s.driftCount > 0 ? "var(--accent-red)" : "var(--accent-green)"} />
        <OverviewCard icon={<ShieldAlert size={18} />} label="\u4e25\u91cd\u7b49\u7ea7" value={`P0:${s.p0Count} P1:${s.p1Count} P2:${s.p2Count}`}
          sub={s.p0Count > 0 ? "\u5b58\u5728 P0 \u4e25\u91cd\u6f02\u79fb" : "\u65e0\u4e25\u91cd\u6f02\u79fb"}
          color={s.p0Count > 0 ? "var(--accent-red)" : "var(--accent-orange)"} />
        <OverviewCard icon={<BarChart3 size={18} />} label="\u53d7\u5f71\u54cd\u8fd0\u884c\u65f6" value={String(s.affectedRuntimes.length)}
          sub={s.affectedRuntimes.join(", ") || "\u65e0"}
          color="var(--accent-teal)" />
      </div>

      <div className="rounded-lg p-4" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}>
        <div className="mb-2 flex items-center gap-2">
          <FileText size={14} style={{ color: "var(--text-secondary)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>Agent \u6280\u80fd\u5206\u5e03</span>
        </div>
        <SkillInventoryTable skills={ws.skills} compact />
      </div>
    </div>
  );
}

function OverviewCard({
  icon, label, value, sub, color,
}: {
  icon: React.ReactNode; label: string; value: string; sub?: string; color: string;
}) {
  return (
    <div className="rounded-lg p-4" style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <div className="flex items-center gap-2 mb-2" style={{ color }}>
        {icon}
        <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{label}</span>
      </div>
      <div className="text-xl font-bold" style={{ color }}>{value}</div>
      {sub && <div className="mt-1 text-[10px]" style={{ color: "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}

function WorkshopSkillTree({
  ws, adventureSelectedAgent, selectedSkill, onSelectSkill,
}: {
  ws: SkillWorkshopState;
  adventureSelectedAgent: AgentProfile | null;
  selectedSkill: AgentSkill | null;
  onSelectSkill: (skill: AgentSkill | null) => void;
}) {
  if (ws.loading) {
    return <div className="flex items-center justify-center p-12 text-sm" style={{ color: "var(--text-muted)" }}>\u52a0\u8f7d\u6280\u80fd\u6811\u6570\u636e\u4e2d...</div>;
  }

  const enrichedProfile = React.useMemo(() => {
    if (!adventureSelectedAgent) return null;
    const wsSkills: AgentSkill[] = ws.skills
      .filter((s) => s.agentIds.includes(adventureSelectedAgent.id))
      .map((s, i) => ({
        id: s.skillId,
        name: s.displayName,
        category: "tool" as const,
        tree: "profession" as const,
        level: s.loadPriority > 0 ? Math.min(Math.ceil(s.loadPriority / 10), 5) : 1,
        status: s.drift.status === "drift" ? "error" as const
          : s.drift.status === "no_baseline" ? "warning" as const
          : "enabled" as const,
        description: `${s.sourceAlias} \u00b7 ${s.runtime} \u00b7 ${s.actual.skillMdSha256.slice(0, 8)}`,
        dependencies: [],
        permissions: [],
        position: { x: 50 + (i % 3) * 20, y: 10 + Math.floor(i / 3) * 18 },
        config: {},
        metrics: { successRate: 1, avgLatencyMs: 0, usageCount: 1 },
        version: s.actual.version,
        sourceRuntime: s.runtime,
        sourceAlias: s.sourceAlias,
        sha256: s.actual.skillMdSha256,
        baselineSha256: s.baseline.skillMdSha256,
        driftStatus: s.drift.status,
        loadPriority: s.loadPriority,
        updateMechanism: s.updateMechanism,
        agentIds: s.agentIds,
      }));
    return { ...adventureSelectedAgent, skills: wsSkills };
  }, [ws.skills, adventureSelectedAgent]);

  if (!enrichedProfile) {
    return <div className="flex items-center justify-center p-12 text-sm" style={{ color: "var(--text-muted)" }}>\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a Agent</div>;
  }

  return (
    <SkillTreeCanvas agent={enrichedProfile} selectedSkill={selectedSkill} onSelectSkill={onSelectSkill} />
  );
}

function StaticComparisonPlaceholder({ adventureAgents }: { adventureAgents: AgentProfile[] }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
      style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <FileText size={36} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>\u7248\u672c\u5bf9\u6bd4\u9700\u8981\u540e\u7aef Skill Workshop API \u652f\u6301</p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        \u5f53\u524d\u5904\u4e8e\u9759\u6001\u6f14\u793a\u6a21\u5f0f\uff0c\u5df2\u52a0\u8f7d {adventureAgents.length} \u4e2a Agent \u7684\u6280\u80fd\u6811\u9759\u6001\u6570\u636e
      </p>
    </div>
  );
}

function StaticDriftPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
      style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <AlertTriangle size={36} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>\u6f02\u79fb\u62a5\u544a\u9700\u8981\u540e\u7aef Skill Workshop API \u652f\u6301</p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        \u542f\u52a8\u540e\u7aef\u670d\u52a1\u540e\uff0c\u7cfb\u7edf\u5c06\u81ea\u52a8\u68c0\u6d4b\u540c\u540d\u8bcd\u6761\u8de8\u8fd0\u884c\u65f6 hash \u6f02\u79fb
      </p>
    </div>
  );
}
