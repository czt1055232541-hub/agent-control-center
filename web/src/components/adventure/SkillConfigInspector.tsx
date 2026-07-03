import React from 'react';
import { X, Shield, CheckCircle, AlertTriangle, Lock, Zap, Ban } from 'lucide-react';
import type { AgentSkill } from '../../types';

const categoryLabels: Record<string, string> = {
  basic: '基础技能', tool: '工具技能', workflow: '工作流',
  permission: '权限', advanced: '高阶', quality: '质量',
};

const statusLabels: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  enabled: { label: '已启用', color: 'var(--accent-green)', icon: <CheckCircle size={14} /> },
  disabled: { label: '已禁用', color: 'var(--accent-orange)', icon: <Ban size={14} /> },
  error: { label: '异常', color: 'var(--accent-red)', icon: <AlertTriangle size={14} /> },
  warning: { label: '警告', color: 'var(--accent-gold)', icon: <AlertTriangle size={14} /> },
  available: { label: '可启用', color: 'var(--accent-blue)', icon: <Zap size={14} /> },
  locked: { label: '未解锁', color: '#b8a88a', icon: <Lock size={14} /> },
};

export function SkillConfigInspector({ skill, onClose }: {
  skill: AgentSkill;
  onClose: () => void;
}) {
  const st = statusLabels[skill.status] ?? statusLabels.locked;

  return (
    <div className="rounded-lg p-4"
      style={{
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-stone)',
        boxShadow: 'var(--shadow-panel)',
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="skill-node-shape diamond flex h-8 w-8 items-center justify-center text-white text-sm"
            style={{ background: `var(--skill-${skill.category})` }}
          >
            ◇
          </span>
          <div>
            <div className="text-sm font-semibold" style={{color:'var(--text-main)'}}>{skill.name}</div>
            <div className="text-xs" style={{color:'var(--text-muted)'}}>{categoryLabels[skill.category] ?? skill.category}</div>
          </div>
        </div>
        <button onClick={onClose} className="rounded p-1 hover:bg-black/5" style={{color:'var(--text-muted)'}}>
          <X size={16} />
        </button>
      </div>

      {/* Status badge */}
      <div className="mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium"
        style={{
          background: `${st.color}15`,
          border: `1px solid ${st.color}30`,
          color: st.color,
        }}
      >
        {st.icon}
        <span>{st.label} · Lv.{skill.level}</span>
      </div>

      {/* Description */}
      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:'var(--text-secondary)'}}>描述</div>
        <p className="mt-1 text-xs" style={{color:'var(--text-main)'}}>{skill.description}</p>
      </div>

      {/* Dependencies */}
      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:'var(--text-secondary)'}}>依赖技能</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {skill.dependencies.length ? skill.dependencies.map(dep => (
            <span key={dep} className="rounded px-2 py-0.5 text-[10px]"
              style={{ background: 'var(--bg-panel-soft)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)' }}
            >
              {dep}
            </span>
          )) : <span className="text-xs" style={{color:'var(--text-muted)'}}>无依赖</span>}
        </div>
      </div>

      {/* Permissions */}
      {skill.permissions.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1 text-xs font-medium" style={{color:'var(--text-secondary)'}}>
            <Shield size={12} /> 权限要求
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {skill.permissions.map(p => (
              <span key={p} className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px]"
                style={{ background: '#fff1eb', border: '1px solid #f5c6b8', color: 'var(--accent-red)' }}
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Config parameters */}
      {Object.keys(skill.config).length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-medium" style={{color:'var(--text-secondary)'}}>配置参数</div>
          <div className="mt-1 space-y-1.5">
            {Object.entries(skill.config).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between rounded px-2 py-1 text-xs"
                style={{ background: 'var(--bg-panel-soft)' }}
              >
                <span style={{color:'var(--text-secondary)'}}>{key}</span>
                <code className="rounded px-1 py-0.5 text-[10px]" style={{ background: 'rgba(255,255,255,0.7)', color: 'var(--text-main)' }}>
                  {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                </code>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="mt-3">
        <div className="text-xs font-medium" style={{color:'var(--text-secondary)'}}>运行指标</div>
        <div className="mt-1 grid grid-cols-2 gap-2">
          <MetricItem label="成功率" value={`${(skill.metrics.successRate * 100).toFixed(0)}%`} color={skill.metrics.successRate > 0.9 ? 'var(--accent-green)' : 'var(--accent-orange)'} />
          <MetricItem label="平均延迟" value={`${skill.metrics.avgLatencyMs}ms`} color="var(--accent-blue)" />
          <MetricItem label="调用次数" value={String(skill.metrics.usageCount)} color="var(--text-secondary)" />
          {skill.metrics.lastError && (
            <div className="col-span-2 rounded px-2 py-1 text-[10px]"
              style={{ background: '#fff1eb', border: '1px solid #f5c6b8', color: 'var(--accent-red)' }}
            >
              最后错误: {skill.metrics.lastError}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border px-3 py-2 text-xs" style={{ borderColor: 'var(--border-light)', background: 'var(--bg-panel-soft)', color: 'var(--text-secondary)' }}>
        技能树 v1 为只读视图；真实配置修改请从 Agent 详情抽屉的“可编辑配置”页签进入。
      </div>
    </div>
  );
}

function MetricItem({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded px-2 py-1.5" style={{ background: 'var(--bg-panel-soft)' }}>
      <div className="text-[10px]" style={{color:'var(--text-muted)'}}>{label}</div>
      <div className="text-xs font-semibold" style={{color}}>{value}</div>
    </div>
  );
}
