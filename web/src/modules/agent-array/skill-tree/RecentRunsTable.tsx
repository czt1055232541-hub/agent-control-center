import React from 'react';
import { CheckCircle, XCircle, Play, Clock } from 'lucide-react';
import type { RecentRun } from '../../../types';

const statusIcon: Record<string, React.ReactNode> = {
  success: <CheckCircle size={14} style={{color:'var(--accent-green)'}} />,
  error: <XCircle size={14} style={{color:'var(--accent-red)'}} />,
  running: <Play size={14} style={{color:'var(--accent-orange)'}} />,
};

const statusBg: Record<string, string> = {
  success: 'rgba(59,168,90,0.08)',
  error: 'rgba(201,84,63,0.08)',
  running: 'rgba(216,138,29,0.08)',
};

export function RecentRunsTable({ runs, onSelectRun }: {
  runs: RecentRun[];
  onSelectRun: (run: RecentRun) => void;
}) {
  return (
    <div className="parchment-panel overflow-hidden">
      <div className="border-b px-4 py-3" style={{ borderColor: 'var(--border-light)' }}>
        <h3 className="text-sm font-semibold" style={{color:'var(--text-main)'}}>最近运行</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: 'var(--bg-panel-soft)' }}>
              <Th>任务 ID</Th>
              <Th>Agent</Th>
              <Th>角色</Th>
              <Th>状态</Th>
              <Th>耗时</Th>
              <Th>时间</Th>
              <Th>模型</Th>
              <Th>Token</Th>
            </tr>
          </thead>
          <tbody>
            {runs.length ? runs.map((run) => (
              <tr
                key={run.id}
                onClick={() => onSelectRun(run)}
                className="cursor-pointer transition-colors hover:brightness-95"
                style={{ background: statusBg[run.status] || 'transparent' }}
              >
                <Td><code style={{color:'var(--accent-teal)'}}>{run.taskId}</code></Td>
                <Td><span style={{color:'var(--text-main)'}}>{run.agentName}</span></Td>
                <Td><span style={{color:'var(--text-secondary)'}}>{run.agentRole}</span></Td>
                <Td><span className="flex items-center gap-1">{statusIcon[run.status]} {run.status}</span></Td>
                <Td><span style={{color:'var(--text-secondary)'}}>{(run.durationMs / 1000).toFixed(1)}s</span></Td>
                <Td><span style={{color:'var(--text-muted)'}}>{run.timestamp}</span></Td>
                <Td><span style={{color:'var(--text-secondary)'}}>{run.model}</span></Td>
                <Td><span style={{color:'var(--text-muted)'}}>{(run.tokensUsed / 1000).toFixed(1)}K</span></Td>
              </tr>
            )) : (
              <tr>
                <td className="px-3 py-6 text-center text-xs" colSpan={8} style={{ color: 'var(--text-muted)' }}>
                  暂无操作记录；这里会显示真实 Operation Log，而不是模拟任务。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left font-medium" style={{color:'var(--text-muted)', borderBottom: '1px solid var(--border-light)'}}>
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return (
    <td className="px-3 py-2" style={{borderBottom: '1px solid var(--border-light)'}}>
      {children}
    </td>
  );
}
