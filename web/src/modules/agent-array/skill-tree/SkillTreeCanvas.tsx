import React, { useMemo, useRef, useState } from 'react';
import type { AgentSkill, AgentProfile } from '../../types';
import { SkillNode } from './SkillNode';
import { SkillConfigInspector } from './SkillConfigInspector';

const categoryLabels: Record<string, string> = {
  basic: '基础技能', tool: '工具技能', workflow: '工作流',
  permission: '权限', advanced: '高阶', quality: '质量',
};

const treeLabels: Record<string, string> = {
  common: '通用技能树',
  profession: '职业技能树',
};

function buildEdges(skills: AgentSkill[]) {
  const edges: { from: AgentSkill; to: AgentSkill }[] = [];
  const map = new Map(skills.map(s => [s.id, s]));
  for (const skill of skills) {
    for (const depId of skill.dependencies) {
      const dep = map.get(depId);
      if (dep) edges.push({ from: dep, to: skill });
    }
  }
  return edges;
}

export function SkillTreeCanvas({ agent, selectedSkill, onSelectSkill }: {
  agent: AgentProfile | null;
  selectedSkill: AgentSkill | null;
  onSelectSkill: (skill: AgentSkill | null) => void;
}) {
  const edges = useMemo(() => agent ? buildEdges(agent.skills) : [], [agent]);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const dragRef = useRef({
    pointerId: -1,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
    moved: false,
  });

  const beginPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest('.skill-node')) return;

    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: panOffset.x,
      originY: panOffset.y,
      moved: false,
    };
    setIsPanning(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const updatePan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isPanning || dragRef.current.pointerId !== event.pointerId) return;

    const dx = event.clientX - dragRef.current.startX;
    const dy = event.clientY - dragRef.current.startY;
    if (!dragRef.current.moved && Math.hypot(dx, dy) < 3) {
      return;
    }
    if (!dragRef.current.moved) {
      dragRef.current.moved = true;
    }
    setPanOffset({
      x: dragRef.current.originX + dx,
      y: dragRef.current.originY + dy,
    });
  };

  const endPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragRef.current.pointerId !== event.pointerId) return;

    setIsPanning(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current.pointerId = -1;
  };

  if (!agent) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 300, background: 'rgba(255,247,232,0.5)', borderRadius: 12, border: '1px solid var(--border-stone)' }}>
        <p className="text-sm" style={{color:'var(--text-muted)'}}>请先选择一个 Agent</p>
      </div>
    );
  }

  const skills = agent.skills;
  // Calculate bounding box for SVG
  const margin = 15;
  const svgW = 100 + margin * 2;
  const svgH = 100 + margin * 2;

  return (
    <div className="relative" style={{ display: 'flex', minHeight: 420 }}>
      {/* Canvas area */}
      <div className="relative flex-1 overflow-hidden rounded-lg"
        onPointerDown={beginPan}
        onPointerMove={updatePan}
        onPointerUp={endPan}
        onPointerCancel={endPan}
        style={{
          background: `radial-gradient(circle at top left, rgba(255,255,255,0.55), transparent 26rem), linear-gradient(135deg, #f8ecd3 0%, #f1dfbd 100%)`,
          border: '1px solid var(--border-stone)',
          boxShadow: 'inset 0 0 0 2px rgba(255,255,255,0.45), 0 2px 4px rgba(91,63,28,0.12)',
          cursor: isPanning ? 'grabbing' : 'grab',
          touchAction: 'none',
        }}
      >
        {/* Map line pattern overlay */}
        <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.04]">
          <defs>
            <pattern id={`grid-${agent.id}`} width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#5c3c18" strokeWidth="0.5" />
            </pattern>
            <pattern id={`diag-${agent.id}`} width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 0 60 L 60 0" fill="none" stroke="#5c3c18" strokeWidth="0.3" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill={`url(#grid-${agent.id})`} />
          <rect width="100%" height="100%" fill={`url(#diag-${agent.id})`} />
        </svg>

        <div
          className="absolute inset-0"
          style={{
            transform: `translate(${panOffset.x}px, ${panOffset.y}px)`,
            willChange: isPanning ? 'transform' : undefined,
          }}
        >
        {/* SVG Edges */}
        <svg className="pointer-events-none absolute inset-0 h-full w-full" style={{ overflow: 'visible' }}>
          {edges.map((edge, i) => {
            const fromPct = edge.from.position;
            const toPct = edge.to.position;
            const fromDepEnabled = edge.to.dependencies.every(d => {
              const dep = skills.find(s => s.id === d);
              return dep && dep.status === 'enabled';
            });
            const toDepMissing = edge.to.dependencies.some(d => {
              const dep = skills.find(s => s.id === d);
              return !dep || dep.status !== 'enabled';
            });
            const isMissing = edge.to.status === 'locked' || (edge.to.status === 'available' && toDepMissing);
            const isError = edge.to.status === 'error' || edge.from.status === 'error';

            let strokeColor = 'var(--accent-teal)';
            let strokeDash = '';
            if (isError) { strokeColor = 'var(--accent-red)'; strokeDash = '6,3'; }
            else if (isMissing) { strokeColor = '#1f1f1f'; strokeDash = '4,3'; }
            else if (!fromDepEnabled) { strokeColor = 'var(--accent-orange)'; strokeDash = '4,3'; }

            return (
              <line
                key={`edge-${i}`}
                x1={`${fromPct.x + margin}%`}
                y1={`${fromPct.y + margin}%`}
                x2={`${toPct.x + margin}%`}
                y2={`${toPct.y + margin}%`}
                stroke={strokeColor}
                strokeWidth={isMissing ? 1.5 : 2}
                strokeDasharray={strokeDash || 'none'}
                opacity={isMissing ? 0.4 : 0.7}
              />
            );
          })}
        </svg>

        <div className="absolute left-3 top-3 rounded-md px-3 py-2 text-xs font-semibold" style={{ background: 'rgba(255,247,232,0.9)', border: '1px solid var(--border-light)', color: 'var(--text-main)' }}>
          通用技能树
        </div>
        <div className="absolute right-3 top-3 rounded-md px-3 py-2 text-xs font-semibold" style={{ background: 'rgba(255,247,232,0.9)', border: '1px solid var(--border-light)', color: 'var(--text-main)' }}>
          职业技能树
        </div>
        <div className="absolute bottom-3 left-1/2 top-12 w-px -translate-x-1/2" style={{ background: 'linear-gradient(180deg, transparent, var(--border-stone), transparent)' }} />

        {/* Skill nodes */}
        {skills.map(skill => (
          <SkillNode
            key={skill.id}
            skill={skill}
            selected={selectedSkill?.id === skill.id}
            onClick={onSelectSkill}
          />
        ))}

        {/* Legend */}
        <div className="absolute bottom-2 right-2 rounded-md p-2 text-[10px]"
          style={{ background: 'rgba(255,247,232,0.9)', border: '1px solid var(--border-light)' }}
        >
          <div className="font-medium mb-1" style={{color:'var(--text-secondary)'}}>图例</div>
          {Object.entries(categoryLabels).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5 py-0.5">
              <span className="inline-block h-2.5 w-2.5 rounded" style={{ background: `var(--skill-${key})` }} />
              <span style={{color:'var(--text-muted)'}}>{label}</span>
            </div>
          ))}
          <div className="mt-1 border-t pt-1" style={{ borderColor: 'var(--border-light)' }}>
            {Object.entries(treeLabels).map(([key, label]) => (
              <div key={key} className="flex items-center gap-1.5 py-0.5">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: key === 'common' ? 'var(--accent-blue)' : 'var(--accent-purple)' }} />
                <span style={{color:'var(--text-muted)'}}>{label}</span>
              </div>
            ))}
            <div className="flex items-center gap-1.5 py-0.5">
              <span className="inline-block h-2.5 w-2.5 rounded" style={{ background: '#1f1f1f' }} />
              <span style={{color:'var(--text-muted)'}}>黑色：未来规划</span>
            </div>
          </div>
        </div>
        </div>
      </div>

      {/* Config inspector sidebar */}
      {selectedSkill && (
        <div className="ml-3 w-72 shrink-0">
          <SkillConfigInspector skill={selectedSkill} onClose={() => onSelectSkill(null)} />
        </div>
      )}
    </div>
  );
}
