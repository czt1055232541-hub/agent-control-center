import React from 'react';
import { Eye, Logs, ChevronRight } from 'lucide-react';
import type { AgentProfile } from '../../types';

const statusConfig: Record<string, { dotClass: string; label: string }> = {
  online: { dotClass: 'online', label: '在线' },
  running: { dotClass: 'running', label: '执行中' },
  idle: { dotClass: 'idle', label: '空闲' },
  error: { dotClass: 'error', label: '异常' },
  offline: { dotClass: 'offline', label: '离线' },
};

const categoryLabels: Record<string, string> = {
  basic: '基础', tool: '工具', workflow: '工作流',
  permission: '权限', advanced: '高阶', quality: '质量',
};

export function AgentCard({ agent, selected, onSelect }: {
  agent: AgentProfile;
  selected: boolean;
  onSelect: (agent: AgentProfile) => void;
}) {
  const cfg = statusConfig[agent.status] ?? statusConfig.offline;
  const enabledByCategory = (cat: string) =>
    agent.skills.filter(s => s.category === cat && s.status === 'enabled').length;
  const skillCategories = ['basic', 'tool', 'workflow', 'permission', 'advanced', 'quality'];

  return (
    <button
      onClick={() => onSelect(agent)}
      className="agent-card flex flex-col items-start gap-2 p-4 text-left transition-all duration-150"
      style={{
        background: 'var(--bg-panel)',
        border: selected ? '2px solid var(--accent-teal)' : '1px solid var(--border-stone)',
        borderRadius: 12,
        boxShadow: selected
          ? '0 0 0 2px rgba(24,166,166,0.18), 0 8px 18px rgba(80,50,20,0.12)'
          : '0 2px 0 rgba(111,76,32,0.18), 0 8px 18px rgba(80,50,20,0.08)',
        minWidth: 200,
        maxWidth: 260,
      }}
    >
      {/* Header: avatar + name + status */}
      <div className="flex w-full items-center gap-3">
        <div className="agent-avatar flex items-center justify-center text-lg"
          style={{
            width: 48, height: 48, borderRadius: '50%',
            border: '2px solid var(--accent-gold)',
            background: `radial-gradient(circle at 30% 20%, #fff8cc, ${agent.color} 55%, #17446b)`,
          }}
        >
          {agent.classIcon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold" style={{color:'var(--text-main)'}}>{agent.name}</span>
            <ChevronRight size={14} style={{color:'var(--text-muted)'}} />
          </div>
          <div className="text-xs" style={{color:'var(--text-secondary)'}}>{agent.title}</div>
        </div>
      </div>

      {/* Status row */}
      <div className="flex w-full items-center gap-3 text-xs" style={{color:'var(--text-secondary)'}}>
        <span className="flex items-center gap-1">
          <span className={`status-dot ${cfg.dotClass}`} />
          {cfg.label}
        </span>
        <span>{agent.enabledSkills}/{agent.totalSkills} 技能</span>
        <span>{agent.boundSessions} 绑定</span>
      </div>

      {/* Stability bar */}
      <div className="w-full">
        <div className="flex items-center justify-between text-xs" style={{color:'var(--text-muted)'}}>
          <span>稳定度</span>
          <span>{agent.stability > 0 ? `${(agent.stability * 100).toFixed(0)}%` : '--'}</span>
        </div>
        <div className="progress-bar mt-1">
          <div className="progress-bar-fill" style={{
            width: `${agent.stability * 100}%`,
            background: agent.stability > 0.9 ? 'var(--accent-green)' : agent.stability > 0.7 ? 'var(--accent-orange)' : 'var(--accent-red)',
          }} />
        </div>
      </div>

      {/* Skill badges */}
      <div className="flex w-full flex-wrap gap-1">
        {skillCategories.map(cat => {
          const cnt = enabledByCategory(cat);
          if (cnt === 0) return null;
          return (
            <span key={cat} className="rounded px-1.5 py-0.5 text-[10px] font-medium text-white"
              style={{ background: `var(--skill-${cat})` }}
            >
              {categoryLabels[cat]} {cnt}
            </span>
          );
        })}
      </div>

      {/* Mini operations */}
      <div className="mt-1 flex w-full gap-2 border-t pt-2" style={{ borderColor: 'var(--border-light)' }}>
        <span className="flex cursor-pointer items-center gap-1 text-xs transition-opacity hover:opacity-70" style={{color:'var(--text-muted)'}}>
          <Eye size={12} /> 详情
        </span>
        <span className="flex cursor-pointer items-center gap-1 text-xs transition-opacity hover:opacity-70" style={{color:'var(--text-muted)'}}>
          <Logs size={12} /> 日志
        </span>
        <span className="ml-auto text-xs" style={{color:'var(--text-muted)'}}>
          {agent.model.split('/').pop()}
        </span>
      </div>
    </button>
  );
}
