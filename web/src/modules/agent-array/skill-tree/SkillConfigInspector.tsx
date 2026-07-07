import React from "react";
import { X, Shield, CheckCircle, AlertTriangle, Lock, Zap, Ban, Hash, GitBranch, Clock, Database, Server } from "lucide-react";
import type { AgentSkill, DriftStatus } from "../../../types";

const categoryLabels: Record<string, string> = {
  basic: "\u57fa\u7840\u6280\u80fd", tool: "\u5de5\u5177\u6280\u80fd", workflow: "\u5de5\u4f5c\u6d41",
  permission: "\u6743\u9650", advanced: "\u9ad8\u9636", quality: "\u8d28\u91cf",
};

const treeLabels: Record<string, string> = {
  common: "\u901a\u7528\u6280\u80fd\u6811",
  profession: "\u804c\u4e1a\u6280\u80fd\u6811",
};

const statusLabels: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  enabled: { label: "\u5df2\u542f\u7528", color: "var(--accent-green)", icon: <CheckCircle size={14} /> },
  disabled: { label: "\u5df2\u7981\u7528", color: "var(--accent-orange)", icon: <Ban size={14} /> },
  error: { label: "\u5f02\u5e38", color: "var(--accent-red)", icon: <AlertTriangle size={14} /> },
  warning: { label: "\u8b66\u544a", color: "var(--accent-gold)", icon: <AlertTriangle size={14} /> },
  available: { label: "\u53ef\u542f\u7528", color: "var(--accent-blue)", icon: <Zap size={14} /> },
  locked: { label: "\u672a\u89e3\u9501", color: "#b8a88a", icon: <Lock size={14} /> },
};

const driftMeta: Record<DriftStatus, { label: string; color: string; icon: React.ReactNode }> = {
  ok: { label: "\u6b63\u5e38", color: "var(--accent-green)", icon: <CheckCircle size={12} /> },
  no_baseline: { label: "\u65e0\u57fa\u7ebf", color: "var(--accent-gold)", icon: <AlertTriangle size={12} /> },
  drift: { label: "\u6f02\u79fb", color: "var(--accent-red)", icon: <AlertTriangle size={12} /> },
  missing_priority: { label: "\u7f3a\u4f18\u5148\u7ea7", color: "var(--accent-orange)", icon: <AlertTriangle size={12} /> },
  stale_version: { label: "\u7248\u672c\u8fc7\u65e7", color: "var(--accent-orange)", icon: <AlertTriangle size={12} /> },
};

function WorkspaceFields({ skill }: { skill: AgentSkill }) {
  const drift = skill.driftStatus ? (driftMeta[skill.driftStatus] ?? driftMeta.ok) : null;
  return (
    <div className="mt-4 space-y-3">
      <div className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>
        <GitBranch size={12} className="inline mr-1" />
        Skill \u5de5\u574a\u4fe1\u606f
      </div>
      <div className="grid gap-2">
        {skill.version && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Clock size={10} className="inline mr-1" />\u7248\u672c
            </div>
            <code className="text-[10px]" style={{ color: "var(--text-main)" }}>{skill.version}</code>
          </div>
        )}
        {skill.sha256 && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Hash size={10} className="inline mr-1" />SHA256
            </div>
            <code className="text-[10px] break-all" style={{ color: "var(--text-main)" }}>{skill.sha256}</code>
          </div>
        )}
        {skill.baselineSha256 && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Database size={10} className="inline mr-1" />\u57fa\u7ebf SHA256
            </div>
            <code className="text-[10px] break-all" style={{ color: "var(--text-main)" }}>{skill.baselineSha256}</code>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {skill.sourceAlias && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>\u6765\u6e90</div>
            <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.sourceAlias}</div>
          </div>
        )}
        {skill.sourceRuntime && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Server size={10} className="inline mr-1" />\u8fd0\u884c\u65f6
            </div>
            <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.sourceRuntime}</div>
          </div>
        )}
      </div>
      {(skill.loadPriority !== undefined || skill.updateMechanism) && (
        <div className="grid grid-cols-2 gap-2">
          {skill.loadPriority !== undefined && (
            <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
              <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>\u52a0\u8f7d\u4f18\u5148\u7ea7</div>
              <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.loadPriority}</div>
            </div>
          )}
          {skill.updateMechanism && (
            <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
              <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>\u66f4\u65b0\u673a\u5236</div>
              <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.updateMechanism}</div>
            </div>
          )}
        </div>
      )}
      {drift && (
        <div className="flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium"
          style={{ background: `${drift.color}15`, border: `1px solid ${drift.color}30`, color: drift.color }}
        >
          {drift.icon}
          <span>\u6f02\u79fb\u72b6\u6001: {drift.label}</span>
        </div>
      )}
      {skill.agentIds && skill.agentIds.length > 0 && (
        <div>
          <div className="text-[10px] font-medium mb-1" style={{ color: "var(--text-secondary)" }}>\u5173\u8054 Agent</div>
          <div className="flex flex-wrap gap-1">
            {skill.agentIds.map((id) => (
              <span key={id} className="rounded px-2 py-0.5 text-[10px]"
                style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)", color: "var(--text-secondary)" }}
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SkillConfigInspector({ skill, onClose }: {
  skill: AgentSkill;
  onClose: () => void;
}) {
  const st = statusLabels[skill.status] ?? statusLabels.locked;

  return (
    <div className="rounded-lg p-4"
      style={{
        background: "var(--bg-panel)",
        border: "1px solid var(--border-stone)",
        boxShadow: "var(--shadow-panel)",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="skill-node-shape diamond flex h-8 w-8 items-center justify-center text-white text-sm"
            style={{ background: `var(--skill-${skill.category})` }}
          >
            \u25c7
          </span>
          <div>
            <div className="text-sm font-semibold" style={{color:"var(--text-main)"}}>{skill.name}</div>
            <div className="text-xs" style={{color:"var(--text-muted)"}}>{treeLabels[skill.tree]} \u00b7 {categoryLabels[skill.category] ?? skill.category}</div>
          </div>
        </div>
        <button onClick={onClose} className="rounded p-1 hover:bg-black/5" style={{color:"var(--text-muted)"}}>
          <X size={16} />
        </button>
      </div>

      <div className="mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium"
        style={{
          background: `${st.color}15`,
          border: `1px solid ${st.color}30`,
          color: st.color,
        }}
      >
        {st.icon}
        <span>{st.label} \u00b7 {skill.status === "locked" ? "\u672a\u6765\u89c4\u5212" : `Lv.${skill.level}`}</span>
      </div>

      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>\u63cf\u8ff0</div>
        <p className="mt-1 text-xs" style={{color:"var(--text-main)"}}>{skill.description}</p>
      </div>

      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>\u4f9d\u8d56\u6280\u80fd</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {skill.dependencies.length ? skill.dependencies.map(dep => (
            <span key={dep} className="rounded px-2 py-0.5 text-[10px]"
              style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)", color: "var(--text-secondary)" }}
            >
              {dep}
            </span>
          )) : <span className="text-xs" style={{color:"var(--text-muted)"}}>\u65e0\u4f9d\u8d56</span>}
        </div>
      </div>

      {skill.permissions.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1 text-xs font-medium" style={{color:"var(--text-secondary)"}}>
            <Shield size={12} /> \u6743\u9650\u8981\u6c42
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {skill.permissions.map(p => (
              <span key={p} className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px]"
                style={{ background: "#fff1eb", border: "1px solid #f5c6b8", color: "var(--accent-red)" }}
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {Object.keys(skill.config).length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>\u914d\u7f6e\u53c2\u6570</div>
          <div className="mt-1 space-y-1.5">
            {Object.entries(skill.config).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between rounded px-2 py-1 text-xs"
                style={{ background: "var(--bg-panel-soft)" }}
              >
                <span style={{color:"var(--text-secondary)"}}>{key}</span>
                <code className="rounded px-1 py-0.5 text-[10px]" style={{ background: "rgba(255,255,255,0.7)", color: "var(--text-main)" }}>
                  {typeof val === "object" ? JSON.stringify(val) : String(val)}
                </code>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>\u8fd0\u884c\u6307\u6807</div>
        <div className="mt-1 grid grid-cols-2 gap-2">
          <MetricItem label="\u6210\u529f\u7387" value={skill.status === "locked" ? "--" : `${(skill.metrics.successRate * 100).toFixed(0)}%`} color={skill.metrics.successRate > 0.9 ? "var(--accent-green)" : "var(--accent-orange)"} />
          <MetricItem label="\u5e73\u5747\u5ef6\u8fdf" value={skill.status === "locked" ? "--" : `${skill.metrics.avgLatencyMs}ms`} color="var(--accent-blue)" />
          <MetricItem label="\u8c03\u7528\u6b21\u6570" value={skill.status === "locked" ? "--" : String(skill.metrics.usageCount)} color="var(--text-secondary)" />
          {skill.metrics.lastError && (
            <div className="col-span-2 rounded px-2 py-1 text-[10px]"
              style={{ background: "#fff1eb", border: "1px solid #f5c6b8", color: "var(--accent-red)" }}
            >
              \u6700\u540e\u9519\u8bef: {skill.metrics.lastError}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border px-3 py-2 text-xs" style={{ borderColor: "var(--border-light)", background: "var(--bg-panel-soft)", color: "var(--text-secondary)" }}>
        {skill.status === "locked" ? "\u9ed1\u8272\u8282\u70b9\u4ee3\u8868\u672a\u6765\u89c4\u5212\u80fd\u529b\uff1a\u5f53\u524d\u6ca1\u6709\u771f\u5b9e\u540e\u7aef\u3001\u914d\u7f6e\u6e90\u6216\u6d4b\u8bd5\u5165\u53e3\uff0c\u6682\u4e0d\u5141\u8bb8\u64cd\u4f5c\u3002" : "\u6280\u80fd\u6811 v1 \u4e3a\u53ea\u8bfb\u89c6\u56fe\uff1b\u771f\u5b9e\u914d\u7f6e\u4fee\u6539\u8bf7\u4ece Agent \u8be6\u60c5\u62bd\u5c49\u7684\u201c\u53ef\u7f16\u8f91\u914d\u7f6e\u201d\u9875\u7b7e\u8fdb\u5165\u3002"}
      </div>

      {(skill.version || skill.sourceRuntime || skill.sourceAlias || skill.sha256 || skill.driftStatus) && (
        <WorkspaceFields skill={skill} />
      )}
    </div>
  );
}

function MetricItem({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
      <div className="text-[10px]" style={{color:"var(--text-muted)"}}>{label}</div>
      <div className="text-xs font-semibold" style={{color}}>{value}</div>
    </div>
  );
}
