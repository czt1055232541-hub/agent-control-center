import React from 'react';
import { Play, Clock, DollarSign } from 'lucide-react';

export function TopStatusBar({ totalAgents, onlineAgents, runningAgents, taskQueue, dailyTokens, tokenBudget, tokensPercent }: {
  totalAgents: number;
  onlineAgents: number;
  runningAgents: number;
  taskQueue: number;
  dailyTokens: number;
  tokenBudget: number;
  tokensPercent: number;
}) {
  return (
    <div className="parchment-panel flex flex-wrap items-center gap-4 px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="status-dot online" />
        <span className="text-sm font-medium" style={{color:'var(--text-main)'}}>{onlineAgents}/{totalAgents} 在线</span>
      </div>
      <div className="flex items-center gap-2">
        <Play size={14} style={{color:'var(--accent-orange)'}} />
        <span className="text-sm" style={{color:'var(--text-secondary)'}}>{runningAgents} 执行中</span>
      </div>
      <div className="flex items-center gap-2">
        <Clock size={14} style={{color:'var(--accent-blue)'}} />
        <span className="text-sm" style={{color:'var(--text-secondary)'}}>{taskQueue} 任务队列</span>
      </div>
      <div className="flex items-center gap-2">
        <DollarSign size={14} style={{color:'var(--accent-gold)'}} />
        <span className="text-sm" style={{color:'var(--text-secondary)'}}>Token {tokenBudget > 0 ? `${tokensPercent.toFixed(0)}%` : '待接入'}</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <div className="progress-bar w-24">
          <div className="progress-bar-fill" style={{width:tokensPercent+'%',background:'var(--accent-teal)'}} />
        </div>
        <span className="text-xs" style={{color:'var(--text-muted)'}}>{tokenBudget > 0 ? `${dailyTokens.toLocaleString()} / ${tokenBudget.toLocaleString()}` : '--'}</span>
      </div>
    </div>
  );
}
