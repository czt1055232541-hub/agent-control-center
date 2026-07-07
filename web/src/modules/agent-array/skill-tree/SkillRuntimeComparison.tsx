import React from "react";
import { GitCompare, Hash, Layers, Clock, AlertTriangle, CheckCircle, ChevronDown, ChevronRight } from "lucide-react";
import type { SkillRuntimeComparisonItem, SkillWorkshopSkill } from "../../../types";

const runtimeColors: Record<string, string> = {
  "lark-cli": "#2f80c9",
  "openclaw-npm": "#18a6a6",
  codeX: "#8e5bbf",
};

interface SkillRuntimeComparisonProps {
  comparisons: SkillRuntimeComparisonItem[];
  loading: boolean;
}

export function SkillRuntimeComparison({ comparisons, loading }: SkillRuntimeComparisonProps) {
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
        \u52a0\u8f7d\u7248\u672c\u5bf9\u6bd4\u6570\u636e...
      </div>
    );
  }

  if (!comparisons.length) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 rounded-lg p-12"
        style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}
      >
        <GitCompare size={36} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          \u6682\u65e0\u8de8\u8fd0\u884c\u65f6\u6280\u80fd\u5bf9\u6bd4\u6570\u636e
        </p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          \u5f53\u6280\u80fd\u5728\u591a\u4e2a\u8fd0\u884c\u65f6\u4e2d\u5b58\u5728\u65f6\uff0c\u5c06\u5728\u6b64\u5904\u5c55\u793a\u7248\u672c\u5bf9\u6bd4
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 rounded-lg p-3" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-stone)" }}>
        <GitCompare size={16} style={{ color: "var(--accent-teal)" }} />
        <span className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
          \u8de8\u8fd0\u884c\u65f6\u7248\u672c\u5bf9\u6bd4
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {comparisons.length} \u4e2a\u6280\u80fd\u8de8\u8fd0\u884c\u65f6\u5b58\u5728 \u00b7 {comparisons.filter((c) => c.hasDrift).length} \u4e2a\u5b58\u5728\u6f02\u79fb
        </span>
        <div className="ml-auto flex gap-2 text-[10px]">
          <span className="flex items-center gap-1" style={{ color: "var(--accent-red)" }}>
            <AlertTriangle size={10} /> \u6f02\u79fb
          </span>
          <span className="flex items-center gap-1" style={{ color: "var(--accent-green)" }}>
            <CheckCircle size={10} /> \u4e00\u81f4
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {comparisons.map((item) => {
          const isExpanded = expanded.has(item.skillId);
          return (
            <div
              key={item.skillId}
              className="overflow-hidden rounded-lg"
              style={{
                background: "var(--bg-panel)",
                border: `1px solid ${item.hasDrift ? "var(--accent-red)30" : "var(--border-light)"}`,
              }}
            >
              <button
                onClick={() => toggle(item.skillId)}
                className="flex w-full items-center gap-3 p-3 text-left transition-colors hover:bg-black/[0.02]"
              >
                {item.hasDrift ? (
                  <AlertTriangle size={14} style={{ color: "var(--accent-red)" }} />
                ) : (
                  <CheckCircle size={14} style={{ color: "var(--accent-green)" }} />
                )}
                <span className="text-sm font-medium flex-1" style={{ color: "var(--text-main)" }}>
                  {item.displayName}
                </span>
                <span className="rounded px-2 py-0.5 text-[10px]" style={{ background: "var(--bg-panel-soft)", color: "var(--text-secondary)", border: "1px solid var(--border-light)" }}>
                  {item.runtimeCount} \u4e2a\u8fd0\u884c\u65f6
                </span>
                {isExpanded ? <ChevronDown size={14} style={{ color: "var(--text-muted)" }} /> : <ChevronRight size={14} style={{ color: "var(--text-muted)" }} />}
              </button>

              {isExpanded && (
                <div className="border-t" style={{ borderColor: "var(--border-light)", background: "var(--bg-panel-soft)" }}>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr>
                          <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u8fd0\u884c\u65f6</th>
                          <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u6765\u6e90</th>
                          <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>
                            <span className="flex items-center gap-1"><Hash size={10} /> Hash</span>
                          </th>
                          <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>
                            <span className="flex items-center gap-1"><Clock size={10} /> \u4fee\u6539\u65f6\u95f4</span>
                          </th>
                          <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u72b6\u6001</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.instances.map((inst) => (
                          <tr
                            key={inst.sourceAlias + inst.runtime}
                            className="border-t transition-colors hover:bg-black/[0.02]"
                            style={{ borderColor: "var(--border-light)" }}
                          >
                            <td className="px-3 py-2">
                              <span
                                className="rounded px-1.5 py-0.5 text-[10px]"
                                style={{
                                  background: `${runtimeColors[inst.runtime] ?? "#888"}18`,
                                  color: runtimeColors[inst.runtime] ?? "#888",
                                }}
                              >
                                <Layers size={10} className="inline mr-1" />
                                {inst.runtime}
                              </span>
                            </td>
                            <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>{inst.sourceAlias}</td>
                            <td className="px-3 py-2 font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
                              {inst.actual.skillMdSha256.slice(0, 12)}
                            </td>
                            <td className="px-3 py-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                              {inst.actual.mtime ? new Date(inst.actual.mtime).toLocaleString() : "-"}
                            </td>
                            <td className="px-3 py-2">
                              <span
                                className="rounded px-1.5 py-0.5 text-[10px]"
                                style={{
                                  background: inst.drift.status === "drift" ? "rgba(216,60,46,0.1)" : "rgba(59,168,90,0.1)",
                                  color: inst.drift.status === "drift" ? "var(--accent-red)" : "var(--accent-green)",
                                }}
                              >
                                {inst.drift.status === "drift" ? "\u6f02\u79fb" : "\u4e00\u81f4"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
