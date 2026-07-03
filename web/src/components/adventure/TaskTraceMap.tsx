import React from 'react';
import { User, Bot, Wrench, FileText, CheckCircle, ArrowDown, Clock } from 'lucide-react';
import type { TaskTraceNode } from '../../types';

const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  user: { icon: <User size={14} />, color: 'var(--accent-blue)' },
  agent: { icon: <Bot size={14} />, color: 'var(--accent-purple)' },
  tool: { icon: <Wrench size={14} />, color: 'var(--skill-tool)' },
  summary: { icon: <FileText size={14} />, color: 'var(--accent-gold)' },
  complete: { icon: <CheckCircle size={14} />, color: 'var(--accent-green)' },
};

function TraceNodeItem({ node, depth = 0 }: { node: TaskTraceNode; depth?: number }) {
  const cfg = typeConfig[node.type] ?? typeConfig.tool;
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <div className="flex items-start gap-3 py-2" style={{ paddingLeft: depth * 28 + 12 }}>
        {/* Connector line */}
        {depth > 0 && (
          <div className="absolute left-0 top-0 h-full w-px" style={{ background: 'var(--border-light)', marginLeft: depth * 28 + 16 }} />
        )}
        {/* Node dot */}
        <div className="relative mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
          style={{
            background: `${cfg.color}18`,
            border: `2px solid ${cfg.color}`,
            color: cfg.color,
          }}
        >
          {cfg.icon}
        </div>
        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium" style={{color:'var(--text-main)'}}>{node.label}</span>
            {node.latencyMs != null && (
              <span className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px]"
                style={{ background: 'var(--bg-panel-soft)', color: 'var(--text-muted)' }}
              >
                <Clock size={10} /> {(node.latencyMs / 1000).toFixed(1)}s
              </span>
            )}
            {node.status === 'error' && (
              <span className="rounded px-1.5 py-0.5 text-[10px] font-medium"
                style={{ background: 'rgba(201,84,63,0.12)', color: 'var(--accent-red)' }}
              >
                失败
              </span>
            )}
          </div>
        </div>
      </div>
      {/* Children */}
      {hasChildren && (
        <div className="relative">
          {node.children!.map((child) => (
            <TraceNodeItem key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function TaskTraceMap({ trace }: { trace: TaskTraceNode | null }) {
  if (!trace) {
    return (
      <div className="parchment-panel flex items-center justify-center p-8">
        <p className="text-sm" style={{color:'var(--text-muted)'}}>选择一次运行记录查看调用链</p>
      </div>
    );
  }

  return (
    <div className="parchment-panel overflow-hidden">
      <div className="border-b px-4 py-3" style={{ borderColor: 'var(--border-light)' }}>
        <h3 className="text-sm font-semibold" style={{color:'var(--text-main)'}}>任务调用链</h3>
      </div>
      <div className="px-2 py-2">
        <TraceNodeItem node={trace} depth={0} />
      </div>
    </div>
  );
}
