import React from 'react';
import { Cpu, FolderOpen, Wrench, BookOpen, Shield, GitBranch, BarChart3 } from 'lucide-react';
import type { AgentEquipment } from '../../types';

interface SlotCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | string[];
  color: string;
}

function SlotCard({ icon, label, value, color }: SlotCardProps) {
  const values = Array.isArray(value) ? value : [value];
  return (
    <div className="rounded-md p-3 transition-all hover:shadow-sm"
      style={{
        background: 'var(--bg-panel-soft)',
        border: '1px solid var(--border-light)',
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md text-white text-xs"
          style={{ background: color }}
        >
          {icon}
        </span>
        <span className="text-xs font-medium" style={{color:'var(--text-secondary)'}}>{label}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {values.map((v, i) => (
          <span key={i} className="rounded px-2 py-0.5 text-xs"
            style={{
              background: 'rgba(255,255,255,0.7)',
              border: '1px solid var(--border-light)',
              color: 'var(--text-main)',
            }}
          >
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

export function EquipmentSlots({ equipment }: { equipment: AgentEquipment }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <SlotCard icon={<Cpu size={14} />} label="模型槽" value={equipment.modelSlot} color="var(--skill-advanced)" />
      <SlotCard icon={<FolderOpen size={14} />} label="Workspace" value={equipment.workspaceSlot} color="var(--skill-basic)" />
      <SlotCard icon={<Wrench size={14} />} label="工具槽" value={equipment.toolSlots} color="var(--skill-tool)" />
      <SlotCard icon={<BookOpen size={14} />} label="知识库槽" value={equipment.knowledgeSlots} color="var(--skill-workflow)" />
      <SlotCard icon={<Shield size={14} />} label="权限槽" value={equipment.permissionSlots} color="var(--skill-permission)" />
      <SlotCard icon={<GitBranch size={14} />} label="工作流槽" value={equipment.workflowSlot} color="var(--skill-advanced)" />
      <SlotCard icon={<BarChart3 size={14} />} label="评估槽" value={equipment.evalSlot} color="var(--skill-quality)" />
    </div>
  );
}
