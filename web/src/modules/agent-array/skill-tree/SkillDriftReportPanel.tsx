import React from "react";
import {
  AlertTriangle, ShieldAlert, AlertOctagon, Info,
  Download, ExternalLink, ChevronDown, ChevronRight,
} from "lucide-react";
import type { SkillDriftReport, SkillDriftReportItem, DriftSeverity } from "../../../types";

const severityMeta: Record<DriftSeverity, { label: string; color: string; bg: string; icon: React.ReactNode; order: number }> = {
  critical: { label: "P0 严重", color: "var(--accent-red)", bg: "rgba(216,60,46,0.08)", icon: <ShieldAlert size={14} />, order: 0 },
  error: { label: "P1 错误", color: "var(--accent-orange)", bg: "rgba(232,138,40,0.08)", icon: <AlertOctagon size={14} />, order: 1 },
  warning: { label: "P2 警告", color: "var(--accent-gold)", bg: "rgba(216,167,46,0.08)", icon: <AlertTriangle size={14} />, order: 2 },
  info: { label: "信息", color: "var(--accent-blue)", bg: "rgba(47,128,201,0.08)", icon: <Info size={14} />, order: 3 },
  normal: { label: "正常", color: "var(--accent-green)", bg: "rgba(59,168,90,0.08)", icon: <Info size={14} />, order: 4 },
};

interface SkillDriftReportPanelProps {
  report: SkillDriftReport | null;
  loading: boolean;
}

export function SkillDriftReportPanel({ report, loading }: SkillDriftReportPanelProps) {
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-sm" style={{ color: "var(--text-muted)" }}>
        加载漂移报告...
      </div>
    );
  }

  if (!report || !report.items.length) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
        style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}
      >
        <CheckCircleIcon />
        <p className="text-sm font-medium" style={{ color: "var(--accent-green)" }}>
          未检测到技能漂移
        </p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {report ? `生成时间: ${new Date(report.generatedAt).toLocaleString()}` : "尚未生成报告"}
        </p>
      </div>
    );
  }

  const sorted = [...report.items].sort(
    (a, b) => (severityMeta[a.drift.severity]?.order ?? 99) - (severityMeta[b.drift.severity]?.order ?? 99)
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg p-4"
        style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} style={{ color: report.summary.driftCount > 0 ? "var(--accent-red)" : "var(--accent-green)" }} />
          <span className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            漂移报告
          </span>
        </div>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          共 {report.summary.totalSkills} 技能 · {report.summary.driftCount} 漂移 · {report.summary.noBaselineCount} 无基线
        </span>
        <div className="ml-auto flex flex-wrap gap-1.5">
          {report.summary.p0Count > 0 && (
            <span className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold" style={{ background: "rgba(216,60,46,0.12)", color: "var(--accent-red)" }}>
              <ShieldAlert size={10} /> P0: {report.summary.p0Count}
            </span>
          )}
          {report.summary.p1Count > 0 && (
            <span className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold" style={{ background: "rgba(232,138,40,0.12)", color: "var(--accent-orange)" }}>
              <AlertOctagon size={10} /> P1: {report.summary.p1Count}
            </span>
          )}
          <span className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold" style={{ background: "rgba(216,167,46,0.12)", color: "var(--accent-gold)" }}>
            <AlertTriangle size={10} /> P2: {report.summary.p2Count}
          </span>
        </div>
        <button
          className="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium hover:bg-black/5"
          style={{ color: "var(--text-secondary)", border: "1px solid var(--border-light)" }}
          onClick={() => {
            const text = JSON.stringify(report, null, 2);
            const blob = new Blob([text], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `skill-drift-report-${report.generatedAt.slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          <Download size={10} />
          导出 JSON
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {sorted.map((item, index) => {
          const sev = severityMeta[item.drift.severity] ?? severityMeta.info;
          const isExpanded = expanded.has(item.skillId + item.sourceAlias);
          return (
            <div
              key={item.skillId + item.sourceAlias}
              className="rounded-lg overflow-hidden"
              style={{ background: "var(--bg-panel)", border: `1px solid ${sev.color}30` }}
            >
              <button
                onClick={() => toggle(item.skillId + item.sourceAlias)}
                className="flex w-full items-center gap-3 p-3 text-left transition-colors hover:bg-black/[0.02]"
              >
                <span className="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-bold" style={{ background: sev.bg, color: sev.color }}>
                  {sev.icon}
                  {sev.label}
                </span>
                <span className="text-sm font-medium flex-1" style={{ color: "var(--text-main)" }}>
                  {item.displayName}
                </span>
                <span className="rounded px-2 py-0.5 text-[10px]" style={{ background: "var(--bg-panel-soft)", color: "var(--text-secondary)", border: "1px solid var(--border-light)" }}>
                  {item.sourceAlias} · {item.runtime}
                </span>
                {isExpanded ? <ChevronDown size={14} style={{ color: "var(--text-muted)" }} /> : <ChevronRight size={14} style={{ color: "var(--text-muted)" }} />}
              </button>

              {isExpanded && (
                <div className="border-t px-4 py-3" style={{ borderColor: "var(--border-light)", background: "var(--bg-panel-soft)" }}>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <div className="text-[10px] font-medium mb-1" style={{ color: "var(--text-secondary)" }}>实际 Hash</div>
                      <code className="text-[10px] break-all" style={{ color: "var(--text-main)" }}>{item.actualHash}</code>
                    </div>
                    <div>
                      <div className="text-[10px] font-medium mb-1" style={{ color: "var(--text-secondary)" }}>基线 Hash</div>
                      <code className="text-[10px] break-all" style={{ color: item.baselineHash ? "var(--text-main)" : "var(--text-muted)" }}>
                        {item.baselineHash ?? "未建立基线"}
                      </code>
                    </div>
                  </div>
                  {item.drift.reasons.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] font-medium mb-1" style={{ color: "var(--text-secondary)" }}>漂移原因</div>
                      <ul className="space-y-1">
                        {item.drift.reasons.map((reason, ri) => (
                          <li key={ri} className="flex items-start gap-1 text-[10px]" style={{ color: sev.color }}>
                            <ExternalLink size={10} className="mt-0.5 shrink-0" />
                            {reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {item.suggestion && (
                    <div className="mt-3 rounded p-2 text-[10px]" style={{ background: `${sev.color}10`, color: sev.color, border: `1px solid ${sev.color}20` }}>
                      <span className="font-semibold">建议: </span>
                      {item.suggestion}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
        报告生成时间: {new Date(report.generatedAt).toLocaleString()} · 漂移报告为只读视图，不自动修改任何技能文件
      </div>
    </div>
  );
}

function CheckCircleIcon() {
  return (
    <div
      className="flex h-12 w-12 items-center justify-center rounded-full"
      style={{ background: "rgba(59,168,90,0.12)" }}
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    </div>
  );
}
