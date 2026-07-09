import React from "react";
import {
  BarChart3, GitBranch, AlertTriangle, FileText,
  CheckCircle, Info, AlertOctagon, ShieldAlert, RotateCw, History, Undo2,
} from "lucide-react";
import type { AgentProfile, SkillWorkshopTab } from "../../../types";
import { SkillInventoryTable } from "./SkillInventoryTable";
import { SkillDriftReportPanel } from "./SkillDriftReportPanel";
import { SkillRuntimeComparison } from "./SkillRuntimeComparison";
import { useSkillWorkshop, type SkillWorkshopState } from "../../../hooks/useSkillWorkshop";
import { useSkillTreeConfig } from "../../../hooks/useSkillTreeConfig";
import { toAgentProfiles } from "./viewModels";
import type { AgentConfig } from "../../../types";
import { ConfiguredSkillTree } from "./ConfiguredSkillTree";

const tabs: { key: SkillWorkshopTab; label: string; icon: React.ReactNode }[] = [
  { key: "overview", label: "概览", icon: <BarChart3 size={14} /> },
  { key: "skill-tree", label: "技能树", icon: <GitBranch size={14} /> },
  { key: "comparison", label: "版本对比", icon: <FileText size={14} /> },
  { key: "drift-report", label: "漂移报告", icon: <AlertTriangle size={14} /> },
  { key: "history", label: "版本管理", icon: <History size={14} /> },
];

interface SkillWorkshopPageProps {
  agents: AgentConfig[];
  adventureSelectedAgent: AgentProfile | null;
  token: string;
}

export function SkillWorkshopPage({
  agents,
  adventureSelectedAgent,
  token,
}: SkillWorkshopPageProps) {
  const [activeTab, setActiveTab] = React.useState<SkillWorkshopTab>("overview");
  const ws = useSkillWorkshop();
  const treeConfig = useSkillTreeConfig();

  const isFallback = !ws.backendAvailable;
  const adventureAgents = React.useMemo(() => toAgentProfiles(agents), [agents]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            技能树工坊
          </h3>
          {ws.loading && (
            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
              <RotateCw size={12} className="animate-spin" />
              加载中...
            </span>
          )}
          {isFallback && activeTab !== "skill-tree" && (
            <span
              className="rounded px-2 py-0.5 text-xs font-medium"
              style={{ background: "#fff3cd", border: "1px solid #ffc107", color: "#856404" }}
            >
              漂移 API 暂不可用
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
            刷新
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
          <ConfiguredSkillTree
            data={treeConfig.data}
            loading={treeConfig.loading}
            error={treeConfig.error}
            selectedAgent={adventureSelectedAgent}
            onRefresh={treeConfig.refresh}
          />
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
        {activeTab === "history" && (
          <WorkshopHistory ws={ws} token={token} />
        )}
      </div>
    </div>
  );
}

function WorkshopHistory({ ws, token }: { ws: ReturnType<typeof useSkillWorkshop>; token: string }) {
  const [selectedVersion, setSelectedVersion] = React.useState("");
  const [confirmText, setConfirmText] = React.useState("");

  React.useEffect(() => {
    ws.loadHistory().catch(() => {});
  }, []);

  React.useEffect(() => {
    const current = ws.history.find((item) => item.type === "baseline-current")?.versionId;
    const target = selectedVersion || ws.history.find((item) => item.type !== "baseline-current")?.versionId;
    if (current && target && current !== target) {
      ws.compareVersions(current, target).catch(() => {});
    }
  }, [ws.history, selectedVersion]);

  const targetVersion = selectedVersion || ws.history.find((item) => item.type !== "baseline-current")?.versionId || "";
  const canRollback = Boolean(token && targetVersion && confirmText === "ROLLBACK WORKSHOP" && !ws.writeBusy);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="rounded-lg p-4" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History size={15} style={{ color: "var(--accent-teal)" }} />
            <span className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>版本时间轴</span>
          </div>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-xs"
            style={{ border: "1px solid var(--border-light)", color: "var(--text-secondary)" }}
            onClick={() => ws.loadHistory()}
          >
            刷新
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {ws.history.length ? ws.history.map((version) => (
            <button
              key={version.versionId}
              type="button"
              onClick={() => {
                setSelectedVersion(version.versionId);
                setConfirmText("");
              }}
              className="rounded-md p-3 text-left"
              style={{
                background: selectedVersion === version.versionId ? "rgba(24,166,166,0.08)" : "var(--bg-panel-soft)",
                border: selectedVersion === version.versionId ? "1px solid var(--accent-teal)" : "1px solid var(--border-light)",
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>{version.versionId}</span>
                <span className="rounded px-2 py-0.5 text-[10px]" style={{ background: "var(--bg-panel)", color: "var(--text-muted)", border: "1px solid var(--border-light)" }}>
                  {version.type}
                </span>
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                {version.timestamp ? new Date(version.timestamp).toLocaleString() : "无时间戳"} · {version.skillCount} skills
              </div>
              <div className="mt-1 truncate text-[11px]" style={{ color: "var(--text-muted)" }}>{version.sourceFile}</div>
            </button>
          )) : (
            <div className="rounded-md p-6 text-center text-sm" style={{ background: "var(--bg-panel-soft)", color: "var(--text-muted)", border: "1px solid var(--border-light)" }}>
              暂无 baseline 或 snapshot 版本
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg p-4" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}>
        <div className="mb-3 flex items-center gap-2">
          <Undo2 size={15} style={{ color: "var(--accent-orange)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>回滚确认</span>
        </div>
        {ws.selectedDiff ? (
          <div className="mb-3 grid grid-cols-3 gap-2">
            <DiffMetric label="新增" value={ws.selectedDiff.summary.added} />
            <DiffMetric label="移除" value={ws.selectedDiff.summary.removed} />
            <DiffMetric label="变更" value={ws.selectedDiff.summary.changed} />
          </div>
        ) : null}
        {ws.selectedDiff && ws.selectedDiff.changed.length ? (
          <div className="mb-3 max-h-44 overflow-auto rounded-md p-2 text-xs" style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
            {ws.selectedDiff.changed.slice(0, 8).map((item) => (
              <div key={item.skillId} className="border-b py-1 last:border-0" style={{ borderColor: "var(--border-light)", color: "var(--text-secondary)" }}>
                <div className="font-medium" style={{ color: "var(--text-main)" }}>{item.displayName}</div>
                <div>{String(item.fromVersion || "").slice(0, 8)} → {String(item.toVersion || "").slice(0, 8)}</div>
              </div>
            ))}
          </div>
        ) : null}
        <label className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>
          输入 ROLLBACK WORKSHOP
          <input
            className="mt-1 w-full rounded-md px-3 py-2 text-xs"
            style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)", color: "var(--text-main)" }}
            value={confirmText}
            onChange={(event) => setConfirmText(event.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={!canRollback}
          className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-50"
          style={{ background: "var(--accent-red)", color: "white" }}
          onClick={() => ws.rollbackVersion(token, targetVersion, confirmText)}
        >
          <Undo2 size={13} />
          回滚到所选版本
        </button>
        {ws.writeError && <div className="mt-2 text-xs" style={{ color: "var(--accent-red)" }}>{ws.writeError}</div>}
        {ws.lastWriteResult && "ok" in ws.lastWriteResult && (
          <div className="mt-2 text-xs" style={{ color: "var(--accent-green)" }}>写入完成</div>
        )}
      </div>
    </div>
  );
}

function DiffMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md p-2 text-center" style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <div className="text-lg font-bold" style={{ color: "var(--accent-teal)" }}>{value}</div>
      <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>{label}</div>
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
        <OverviewCard icon={<GitBranch size={18} />} label="技能总数" value={String(totalSkills)} color="var(--accent-blue)" />
        <OverviewCard icon={<CheckCircle size={18} />} label="Agent 数量" value={String(adventureAgents.length)} color="var(--accent-green)" />
        <OverviewCard icon={<Info size={18} />} label="数据源" value="静态演示" sub="viewModels.ts" color="var(--accent-gold)" />
        <OverviewCard icon={<AlertOctagon size={18} />} label="状态" value="后端不可用" sub="已切换至静态模式" color="var(--accent-orange)" />
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
        <OverviewCard icon={<GitBranch size={18} />} label="技能总数" value={String(s.totalSkills)}
          sub={s.lastScanTime ? `最后扫描: ${new Date(s.lastScanTime).toLocaleTimeString()}` : "尚未扫描"}
          color="var(--accent-blue)" />
        <OverviewCard icon={<AlertTriangle size={18} />} label="漂移技能" value={String(s.driftCount)}
          sub={s.driftCount > 0 ? "需要关注" : "全部正常"}
          color={s.driftCount > 0 ? "var(--accent-red)" : "var(--accent-green)"} />
        <OverviewCard icon={<ShieldAlert size={18} />} label="严重等级" value={`P0:${s.p0Count} P1:${s.p1Count} P2:${s.p2Count}`}
          sub={s.p0Count > 0 ? "存在 P0 严重漂移" : "无严重漂移"}
          color={s.p0Count > 0 ? "var(--accent-red)" : "var(--accent-orange)"} />
        <OverviewCard icon={<BarChart3 size={18} />} label="受影响运行时" value={String(s.affectedRuntimes.length)}
          sub={s.affectedRuntimes.join(", ") || "无"}
          color="var(--accent-teal)" />
      </div>

      <div className="rounded-lg p-4" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}>
        <div className="mb-2 flex items-center gap-2">
          <FileText size={14} style={{ color: "var(--text-secondary)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>Agent 技能分布</span>
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

function StaticComparisonPlaceholder({ adventureAgents }: { adventureAgents: AgentProfile[] }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
      style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <FileText size={36} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>版本对比需要后端 Skill Workshop API 支持</p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        当前处于静态演示模式，已加载 {adventureAgents.length} 个 Agent 的技能树静态数据
      </p>
    </div>
  );
}

function StaticDriftPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
      style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
      <AlertTriangle size={36} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>漂移报告需要后端 Skill Workshop API 支持</p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        启动后端服务后，系统将自动检测同名词条跨运行时 hash 漂移
      </p>
    </div>
  );
}
