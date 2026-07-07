import React from "react";
import { Hash, Clock, Layers, AlertTriangle, CheckCircle, Info } from "lucide-react";
import type { SkillWorkshopSkill, DriftStatus } from "../../../types";

const driftBadge: Record<DriftStatus, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  ok: { label: "\u6b63\u5e38", color: "var(--accent-green)", bg: "rgba(59,168,90,0.1)", icon: <CheckCircle size={12} /> },
  no_baseline: { label: "\u65e0\u57fa\u7ebf", color: "var(--accent-gold)", bg: "rgba(216,167,46,0.1)", icon: <Info size={12} /> },
  drift: { label: "\u6f02\u79fb", color: "var(--accent-red)", bg: "rgba(216,60,46,0.1)", icon: <AlertTriangle size={12} /> },
  missing_priority: { label: "\u7f3a\u4f18\u5148\u7ea7", color: "var(--accent-orange)", bg: "rgba(232,138,40,0.1)", icon: <AlertTriangle size={12} /> },
  stale_version: { label: "\u7248\u672c\u8fc7\u65e7", color: "var(--accent-orange)", bg: "rgba(232,138,40,0.1)", icon: <AlertTriangle size={12} /> },
};

const runtimeColors: Record<string, string> = {
  "lark-cli": "#2f80c9",
  "openclaw-npm": "#18a6a6",
  codeX: "#8e5bbf",
};

interface SkillInventoryTableProps {
  skills: SkillWorkshopSkill[];
  compact?: boolean;
}

export function SkillInventoryTable({ skills, compact = false }: SkillInventoryTableProps) {
  const [groupBy, setGroupBy] = React.useState<"runtime" | "source" | "agent">("runtime");
  const [filterText, setFilterText] = React.useState("");

  const filtered = React.useMemo(() => {
    if (!filterText.trim()) return skills;
    const q = filterText.toLowerCase();
    return skills.filter(
      (s) =>
        s.displayName.toLowerCase().includes(q) ||
        s.sourceAlias.toLowerCase().includes(q) ||
        s.runtime.toLowerCase().includes(q) ||
        s.agentIds.some((a) => a.toLowerCase().includes(q))
    );
  }, [skills, filterText]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, SkillWorkshopSkill[]>();
    for (const skill of filtered) {
      const key =
        groupBy === "runtime"
          ? skill.runtime
          : groupBy === "source"
            ? skill.sourceAlias
            : skill.agentIds.join(", ") || "(\u65e0 Agent)";
      const existing = map.get(key);
      if (existing) {
        existing.push(skill);
      } else {
        map.set(key, [skill]);
      }
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered, groupBy]);

  if (!skills.length) {
    return (
      <div className="flex items-center justify-center p-8 text-sm" style={{ color: "var(--text-muted)" }}>
        \u6682\u65e0\u6280\u80fd\u6570\u636e
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {!compact && (
        <div className="flex items-center gap-3">
          <div className="flex rounded-md text-xs" style={{ border: "1px solid var(--border-light)" }}>
            {(["runtime", "source", "agent"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setGroupBy(mode)}
                className="px-3 py-1.5 font-medium transition-colors first:rounded-l-md last:rounded-r-md"
                style={{
                  background: groupBy === mode ? "var(--accent-teal)" : "transparent",
                  color: groupBy === mode ? "#fff" : "var(--text-secondary)",
                  borderRight: mode !== "agent" ? "1px solid var(--border-light)" : "none",
                }}
              >
                {mode === "runtime" ? "\u6309\u8fd0\u884c\u65f6" : mode === "source" ? "\u6309\u6765\u6e90" : "\u6309 Agent"}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="\u641c\u7d22\u6280\u80fd..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="rounded-md px-3 py-1.5 text-xs"
            style={{
              background: "var(--bg-panel-soft)",
              border: "1px solid var(--border-light)",
              color: "var(--text-main)",
              outline: "none",
            }}
          />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {filtered.length} / {skills.length} \u9879
          </span>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {grouped.map(([groupName, groupSkills]) => (
          <div key={groupName}>
            <div className="mb-1 flex items-center gap-2">
              <span
                className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold"
                style={{
                  background: `${runtimeColors[groupName] ?? "var(--accent-teal)"}18`,
                  color: runtimeColors[groupName] ?? "var(--accent-teal)",
                }}
              >
                <Layers size={10} />
                {groupBy === "runtime" ? "\u8fd0\u884c\u65f6" : groupBy === "source" ? "\u6765\u6e90" : "Agent"}: {groupName}
              </span>
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                ({groupSkills.length} \u9879)
              </span>
            </div>
            <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border-light)" }}>
              <table className="w-full text-left text-xs">
                <thead>
                  <tr style={{ background: "var(--bg-panel-soft)" }}>
                    {!compact && <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u6280\u80fd\u540d\u79f0</th>}
                    <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>{compact ? "\u6280\u80fd\u540d\u79f0" : ""}</th>
                    <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u6765\u6e90</th>
                    {!compact && <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u8fd0\u884c\u65f6</th>}
                    <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>Hash</th>
                    {!compact && <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u4f18\u5148\u7ea7</th>}
                    <th className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>\u72b6\u6001</th>
                  </tr>
                </thead>
                <tbody>
                  {groupSkills.map((skill) => {
                    const badge = driftBadge[skill.drift.status] ?? driftBadge.ok;
                    return (
                      <tr
                        key={skill.skillId + skill.sourceAlias}
                        className="border-t transition-colors hover:bg-black/[0.02]"
                        style={{ borderColor: "var(--border-light)" }}
                      >
                        {!compact && (
                          <td className="px-3 py-2 font-medium" style={{ color: "var(--text-main)" }}>
                            {skill.displayName}
                          </td>
                        )}
                        <td className="px-3 py-2 font-medium" style={{ color: "var(--text-main)" }}>
                          {compact ? skill.displayName : <code className="text-[10px]" style={{ color: "var(--text-secondary)" }}>{skill.skillId}</code>}
                        </td>
                        <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                          {skill.sourceAlias}
                        </td>
                        {!compact && (
                          <td className="px-3 py-2">
                            <span
                              className="rounded px-1.5 py-0.5 text-[10px]"
                              style={{
                                background: `${runtimeColors[skill.runtime] ?? "#888"}18`,
                                color: runtimeColors[skill.runtime] ?? "#888",
                              }}
                            >
                              {skill.runtime}
                            </span>
                          </td>
                        )}
                        <td className="px-3 py-2 font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
                          <span className="flex items-center gap-1">
                            <Hash size={10} />
                            {skill.actual.skillMdSha256.slice(0, 8)}
                          </span>
                        </td>
                        {!compact && (
                          <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                            {skill.loadPriority > 0 ? skill.loadPriority : "-"}
                          </td>
                        )}
                        <td className="px-3 py-2">
                          <span
                            className="flex w-fit items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
                            style={{ background: badge.bg, color: badge.color }}
                          >
                            {badge.icon}
                            {badge.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {!compact && (
        <div className="flex flex-wrap gap-3 rounded-md p-2 text-[10px]" style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)" }}>
          <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>\u56fe\u4f8b:</span>
          {Object.entries(driftBadge).map(([key, badge]) => (
            <span key={key} className="flex items-center gap-1" style={{ color: badge.color }}>
              {badge.icon}
              {badge.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
