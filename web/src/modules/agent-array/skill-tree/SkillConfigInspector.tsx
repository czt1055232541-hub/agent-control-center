import React from "react";
import { X, Shield, CheckCircle, AlertTriangle, Lock, Zap, Ban, Hash, GitBranch, Clock, Database, Server } from "lucide-react";
import type { AgentSkill, DriftStatus } from "../../../types";

const categoryLabels: Record<string, string> = {
  basic: "基础技能", tool: "工具技能", workflow: "工作流",
  permission: "权限", advanced: "高阶", quality: "质量",
};

const treeLabels: Record<string, string> = {
  common: "通用技能树",
  profession: "职业技能树",
};

const statusLabels: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  enabled: { label: "已启用", color: "var(--accent-green)", icon: <CheckCircle size={14} /> },
  disabled: { label: "已禁用", color: "var(--accent-orange)", icon: <Ban size={14} /> },
  error: { label: "异常", color: "var(--accent-red)", icon: <AlertTriangle size={14} /> },
  warning: { label: "警告", color: "var(--accent-gold)", icon: <AlertTriangle size={14} /> },
  available: { label: "可启用", color: "var(--accent-blue)", icon: <Zap size={14} /> },
  locked: { label: "未解锁", color: "#b8a88a", icon: <Lock size={14} /> },
};

const driftMeta: Record<DriftStatus, { label: string; color: string; icon: React.ReactNode }> = {
  ok: { label: "正常", color: "var(--accent-green)", icon: <CheckCircle size={12} /> },
  no_baseline: { label: "无基线", color: "var(--accent-gold)", icon: <AlertTriangle size={12} /> },
  drift: { label: "漂移", color: "var(--accent-red)", icon: <AlertTriangle size={12} /> },
  missing_priority: { label: "缺优先级", color: "var(--accent-orange)", icon: <AlertTriangle size={12} /> },
  stale_version: { label: "版本过旧", color: "var(--accent-orange)", icon: <AlertTriangle size={12} /> },
};

function WorkspaceFields({ skill }: { skill: AgentSkill }) {
  const drift = skill.driftStatus ? (driftMeta[skill.driftStatus] ?? driftMeta.ok) : null;
  return (
    <div className="mt-4 space-y-3">
      <div className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>
        <GitBranch size={12} className="inline mr-1" />
        Skill 工坊信息
      </div>
      <div className="grid gap-2">
        {skill.version && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Clock size={10} className="inline mr-1" />版本
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
              <Database size={10} className="inline mr-1" />基线 SHA256
            </div>
            <code className="text-[10px] break-all" style={{ color: "var(--text-main)" }}>{skill.baselineSha256}</code>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {skill.sourceAlias && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>来源</div>
            <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.sourceAlias}</div>
          </div>
        )}
        {skill.sourceRuntime && (
          <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
            <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              <Server size={10} className="inline mr-1" />运行时
            </div>
            <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.sourceRuntime}</div>
          </div>
        )}
      </div>
      {(skill.loadPriority !== undefined || skill.updateMechanism) && (
        <div className="grid grid-cols-2 gap-2">
          {skill.loadPriority !== undefined && (
            <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
              <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>加载优先级</div>
              <div className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{skill.loadPriority}</div>
            </div>
          )}
          {skill.updateMechanism && (
            <div className="rounded px-2 py-1.5" style={{ background: "var(--bg-panel-soft)" }}>
              <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>更新机制</div>
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
          <span>漂移状态: {drift.label}</span>
        </div>
      )}
      {skill.agentIds && skill.agentIds.length > 0 && (
        <div>
          <div className="text-[10px] font-medium mb-1" style={{ color: "var(--text-secondary)" }}>关联 Agent</div>
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
            ◇
          </span>
          <div>
            <div className="text-sm font-semibold" style={{color:"var(--text-main)"}}>{skill.name}</div>
            <div className="text-xs" style={{color:"var(--text-muted)"}}>{treeLabels[skill.tree]} · {categoryLabels[skill.category] ?? skill.category}</div>
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
        <span>{st.label} · {skill.status === "locked" ? "未来规划" : `Lv.${skill.level}`}</span>
      </div>

      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>描述</div>
        <p className="mt-1 text-xs" style={{color:"var(--text-main)"}}>{skill.description}</p>
      </div>

      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>依赖技能</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {skill.dependencies.length ? skill.dependencies.map(dep => (
            <span key={dep} className="rounded px-2 py-0.5 text-[10px]"
              style={{ background: "var(--bg-panel-soft)", border: "1px solid var(--border-light)", color: "var(--text-secondary)" }}
            >
              {dep}
            </span>
          )) : <span className="text-xs" style={{color:"var(--text-muted)"}}>无依赖</span>}
        </div>
      </div>

      {skill.permissions.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1 text-xs font-medium" style={{color:"var(--text-secondary)"}}>
            <Shield size={12} /> 权限要求
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
          <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>配置参数</div>
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
        <div className="text-xs font-medium" style={{color:"var(--text-secondary)"}}>运行指标</div>
        <div className="mt-1 grid grid-cols-2 gap-2">
          <MetricItem label="成功率" value={skill.status === "locked" ? "--" : `${(skill.metrics.successRate * 100).toFixed(0)}%`} color={skill.metrics.successRate > 0.9 ? "var(--accent-green)" : "var(--accent-orange)"} />
          <MetricItem label="平均延迟" value={skill.status === "locked" ? "--" : `${skill.metrics.avgLatencyMs}ms`} color="var(--accent-blue)" />
          <MetricItem label="调用次数" value={skill.status === "locked" ? "--" : String(skill.metrics.usageCount)} color="var(--text-secondary)" />
          {skill.metrics.lastError && (
            <div className="col-span-2 rounded px-2 py-1 text-[10px]"
              style={{ background: "#fff1eb", border: "1px solid #f5c6b8", color: "var(--accent-red)" }}
            >
              最后错误: {skill.metrics.lastError}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border px-3 py-2 text-xs" style={{ borderColor: "var(--border-light)", background: "var(--bg-panel-soft)", color: "var(--text-secondary)" }}>
        {skill.status === "locked" ? "黑色节点代表未来规划能力：当前没有真实后端、配置源或测试入口，暂不允许操作。" : "技能树 v1 为只读视图；真实配置修改请从 Agent 详情抽屉的“可编辑配置”页签进入。"}
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
