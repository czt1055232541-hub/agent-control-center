import React from 'react';
import type { AgentSkill, SkillCategory, SkillStatus } from '../../../types';

const shapeMap: Record<SkillCategory, string> = {
  basic: 'circle',
  tool: 'hexagon',
  workflow: 'square',
  permission: 'shield',
  advanced: 'diamond',
  quality: 'chest',
};

const iconMap: Record<SkillCategory, string> = {
  basic: '⟐', tool: '⬡', workflow: '▣',
  permission: '⛊', advanced: '◇', quality: '⬙',
};

const statusBorder: Record<SkillStatus, string> = {
  enabled: 'var(--accent-teal)',
  disabled: 'var(--accent-orange)',
  error: 'var(--accent-red)',
  warning: 'var(--accent-gold)',
  available: 'var(--accent-blue)',
  locked: '#1f1f1f',
};

export function SkillNode({ skill, selected, onClick }: {
  skill: AgentSkill;
  selected: boolean;
  onClick: (skill: AgentSkill) => void;
}) {
  const shape = shapeMap[skill.category] || 'circle';
  const categoryColor = `var(--skill-${skill.category})`;
  const borderColor = statusBorder[skill.status] || 'var(--border-stone)';
  const isLocked = skill.status === 'locked';

  return (
    <div
      onClick={() => onClick(skill)}
      className="skill-node"
      style={{
        position: 'absolute',
        left: `${skill.position.x}%`,
        top: `${skill.position.y}%`,
        transform: 'translate(-50%, -50%)',
        minWidth: 130,
        height: 44,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 10px',
        borderRadius: 10,
        background: isLocked ? 'rgba(31,31,31,0.88)' : 'rgba(255, 247, 232, 0.96)',
        border: selected ? `2px solid ${borderColor}` : `1px solid ${borderColor}`,
        boxShadow: selected
          ? `0 0 0 3px rgba(24,166,166,0.15), 0 2px 0 rgba(112,76,33,0.18)`
          : `0 2px 0 rgba(112,76,33,0.18)`,
        cursor: isLocked ? 'not-allowed' : 'pointer',
        opacity: 1,
        zIndex: selected ? 10 : 1,
      }}
    >
      <span
        className={`skill-node-shape ${shape}`}
        style={{
          background: isLocked ? '#050505' : categoryColor,
          width: 24, height: 24,
          display: 'grid', placeItems: 'center',
          color: '#fff', fontSize: 12,
          flexShrink: 0,
        }}
      >
        {iconMap[skill.category]}
      </span>
      <div className="min-w-0">
        <div className="truncate text-xs font-medium" style={{color: isLocked ? '#f6ead2' : 'var(--text-main)'}}>
          {skill.name}
        </div>
        <div className="text-[10px]" style={{color: isLocked ? '#caa875' : 'var(--text-muted)'}}>
          {skill.tree === 'common' ? '通用' : '职业'} · {isLocked ? '规划中' : `Lv.${skill.level}`}
        </div>
      </div>
    </div>
  );
}
