import React from 'react';
import { Cpu, Wrench, GitBranch } from 'lucide-react';
import type { AgentProfile } from '../../../types';
import { EquipmentSlots } from './EquipmentSlots';

const statusConfig: Record<string, { dotClass: string; label: string }> = {
  online: { dotClass: 'online', label: '在线' },
  running: { dotClass: 'running', label: '执行中' },
  idle: { dotClass: 'idle', label: '空闲' },
  error: { dotClass: 'error', label: '异常' },
  offline: { dotClass: 'offline', label: '离线' },
};

const tabs = ['概览', '技能树', '装备', '权限', '工作流', '测试评估', '日志'] as const;
type TabType = (typeof tabs)[number];

export function AgentDetailPanel({ agent, activeTab, onTabChange }: {
  agent: AgentProfile | null;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}) {
  if (!agent) {
    return (
      <div className="parchment-panel flex items-center justify-center p-12" style={{ minHeight: 300 }}>
        <div className="text-center" style={{color:'var(--text-muted)'}}>
          <Cpu size={48} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">选择一个 Agent 查看详情</p>
        </div>
      </div>
    );
  }

  const cfg = statusConfig[agent.status] ?? statusConfig.offline;

  return (
    <div className="parchment-panel overflow-hidden">
      {/* Agent header */}
      <div className="flex items-start gap-4 border-b p-4" style={{ borderColor: 'var(--border-light)' }}>
        <div className="flex h-14 w-14 items-center justify-center text-xl"
          style={{
            width: 56, height: 56, borderRadius: '50%',
            border: '2px solid var(--accent-gold)',
            background: `radial-gradient(circle at 30% 20%, #fff8cc, ${agent.color} 55%, #17446b)`,
          }}
        >
          {agent.classIcon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold" style={{color:'var(--text-main)'}}>{agent.name}</h3>
            <span className={`status-dot ${cfg.dotClass}`} />
            <span className="text-sm" style={{color:'var(--text-secondary)'}}>{cfg.label}</span>
          </div>
          <p className="text-sm" style={{color:'var(--text-secondary)'}}>{agent.title} · {agent.role}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(agent.backendActions ?? []).filter((action) => action.enabled).map((action) => (
              <span
                key={`${action.kind}-${action.key}`}
                className="rounded px-2 py-1 text-xs"
                style={{ background: 'var(--bg-panel-soft)', border: '1px solid var(--border-light)', color: action.danger ? 'var(--accent-red)' : 'var(--text-secondary)' }}
              >
                {action.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b px-4 pt-2" style={{ borderColor: 'var(--border-light)' }}>
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className="rounded-t-lg px-3 py-2 text-xs font-medium transition-all"
            style={{
              color: activeTab === tab ? 'var(--accent-teal)' : 'var(--text-secondary)',
              borderBottom: activeTab === tab ? '2px solid var(--accent-teal)' : '2px solid transparent',
              background: activeTab === tab ? 'rgba(24,166,166,0.06)' : 'transparent',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4">
        {activeTab === '概览' && (
          <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
            <div className="grid grid-cols-2 gap-3">
              <StatField label="定位" value={agent.role} />
              <StatField label="模型" value={agent.model} />
              <StatField label="Workspace" value={agent.workspace} />
              <StatField label="Provider" value={agent.provider} />
              <StatField label="创建时间" value={agent.lastInteraction} />
              <StatField label="最近交互" value={agent.lastInteraction} />
              <StatField label="绑定会话" value={String(agent.boundSessions)} />
              <StatField label="权限等级" value={agent.equipment.permissionSlots.join(', ')} />
            </div>
            <div className="flex flex-col gap-3" style={{ minWidth: 200 }}>
              <MetricCard label="稳定度" value={agent.stability > 0 ? `${(agent.stability * 100).toFixed(0)}%` : '--'} color={agent.stability > 0.9 ? 'var(--accent-green)' : 'var(--accent-orange)'} />
              <MetricCard label="成功率" value={agent.successRate ? `${(agent.successRate * 100).toFixed(0)}%` : '--'} color={agent.successRate > 0.9 ? 'var(--accent-green)' : 'var(--accent-orange)'} />
              <MetricCard label="平均响应" value={agent.avgLatencyMs ? `${(agent.avgLatencyMs / 1000).toFixed(1)}s` : '--'} color="var(--accent-blue)" />
              <MetricCard label="今日 Token" value={agent.dailyTokenUsed ? `${(agent.dailyTokenUsed / 1000).toFixed(0)}K` : '--'} color="var(--accent-gold)" />
            </div>
          </div>
        )}
        {activeTab === '装备' && <EquipmentSlots equipment={agent.equipment} />}
        {activeTab === '技能树' && (
          <div className="py-8 text-center" style={{color:'var(--text-muted)'}}>
            <GitBranch size={32} className="mx-auto mb-2 opacity-30" />
            <p className="text-sm">技能树在下方画布中展示</p>
          </div>
        )}
        {['权限', '工作流', '测试评估', '日志'].includes(activeTab) && (
          <div className="py-8 text-center" style={{color:'var(--text-muted)'}}>
            <Wrench size={32} className="mx-auto mb-2 opacity-30" />
            <p className="text-sm">{activeTab} 详情将在后续阶段接入真实数据源</p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md p-3" style={{ background: 'var(--bg-panel-soft)', border: '1px solid var(--border-light)' }}>
      <div className="text-xs" style={{color:'var(--text-muted)'}}>{label}</div>
      <div className="mt-1 text-sm font-medium" style={{color:'var(--text-main)'}}>{value || '--'}</div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-md p-3" style={{ background: 'var(--bg-panel-soft)', border: '1px solid var(--border-light)' }}>
      <div className="text-xs" style={{color:'var(--text-muted)'}}>{label}</div>
      <div className="mt-1 text-lg font-bold" style={{color}}>{value}</div>
    </div>
  );
}
