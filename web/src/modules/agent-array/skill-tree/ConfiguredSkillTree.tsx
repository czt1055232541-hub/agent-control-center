import React from "react";
import { Database, FileText, GitBranch, RefreshCcw } from "lucide-react";
import type { AgentProfile, ConfigSkillTreeConfig, ConfigSkillTreeNode, ConfigSkillTreeResponse } from "../../../types";

const dashboardAgentMap: Record<string, string> = {
  "openclaw-coordinator": "coordinator",
  "openclaw-orchestrator": "ops",
  "openclaw-main": "audit",
  "openclaw-archivist": "archive",
  "codex-code-agent": "codex",
};

const categoryColor: Record<string, string> = {
  basic: "var(--accent-blue)",
  tool: "var(--accent-teal)",
  workflow: "var(--accent-green)",
  permission: "var(--accent-orange)",
  advanced: "var(--accent-purple)",
  quality: "var(--accent-gold)",
};

const nodeTypeLabel: Record<string, string> = {
  model: "模型基座",
  skill: "真实 skill",
  planned: "规划节点",
};

function treeAgentId(profile: AgentProfile | null): string {
  if (!profile) return "coordinator";
  return dashboardAgentMap[profile.id] ?? profile.id;
}

function selectTree(data: ConfigSkillTreeResponse | null, profile: AgentProfile | null): ConfigSkillTreeConfig | null {
  if (!data?.agents.length) return null;
  const target = treeAgentId(profile);
  return data.agents.find((item) => item.agent.id === target) ?? data.agents[0];
}

function branchName(branch: ConfigSkillTreeNode["branch"]) {
  if (branch === "generic") return "通用技能";
  if (branch === "professional") return "专业技能";
  return "基座";
}

function nodeTone(node: ConfigSkillTreeNode) {
  if (node.nodeType === "model") return "var(--accent-blue)";
  if (node.nodeType === "planned") return "#475569";
  return categoryColor[node.category] ?? "var(--accent-teal)";
}

function nodeTop(node: ConfigSkillTreeNode) {
  return node.y * 8;
}

function logicalHeight(nodes: ConfigSkillTreeNode[]) {
  const maxY = Math.max(80, ...nodes.map((node) => node.y));
  return Math.max(680, maxY * 8 + 140);
}

export function ConfiguredSkillTree({
  data,
  loading,
  error,
  selectedAgent,
  onRefresh,
}: {
  data: ConfigSkillTreeResponse | null;
  loading: boolean;
  error: string | null;
  selectedAgent: AgentProfile | null;
  onRefresh: () => void;
}) {
  const tree = React.useMemo(() => selectTree(data, selectedAgent), [data, selectedAgent]);
  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
  const [pan, setPan] = React.useState({ x: 0, y: 0 });
  const [dragging, setDragging] = React.useState(false);
  const dragRef = React.useRef({ pointerId: -1, startX: 0, startY: 0, originX: 0, originY: 0, moved: false });

  React.useEffect(() => {
    setSelectedNodeId(null);
    setPan({ x: 0, y: 0 });
  }, [tree?.agent.id]);

  const selectedNode = React.useMemo(
    () => tree?.nodes.find((node) => node.id === selectedNodeId) ?? tree?.nodes[0] ?? null,
    [tree, selectedNodeId],
  );
  const nodesById = React.useMemo(() => new Map((tree?.nodes ?? []).map((node) => [node.id, node])), [tree]);
  const height = React.useMemo(() => logicalHeight(tree?.nodes ?? []), [tree]);

  const beginPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || (event.target as HTMLElement).closest(".configured-skill-node")) return;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: pan.x,
      originY: pan.y,
      moved: false,
    };
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const updatePan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging || dragRef.current.pointerId !== event.pointerId) return;
    const dx = event.clientX - dragRef.current.startX;
    const dy = event.clientY - dragRef.current.startY;
    if (!dragRef.current.moved && Math.hypot(dx, dy) < 3) return;
    dragRef.current.moved = true;
    setPan({ x: dragRef.current.originX + dx, y: dragRef.current.originY + dy });
  };

  const endPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragRef.current.pointerId !== event.pointerId) return;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current.pointerId = -1;
  };

  if (loading) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">正在加载技能树配置...</div>;
  }
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        <div className="font-semibold">技能树配置加载失败</div>
        <div className="mt-1">{error}</div>
      </div>
    );
  }
  if (!tree) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">暂无技能树配置。</div>;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-950">{tree.agent.name} · 完整技能树</h3>
            <p className="mt-1 text-sm text-slate-600">
              {tree.agent.role} · nodes/edges 来自配置文件，模型基座不对应 SKILL.md。
            </p>
          </div>
          <button
            className="inline-flex items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            type="button"
            onClick={onRefresh}
          >
            <RefreshCcw size={14} />
            刷新配置
          </button>
        </div>

        <div
          className="relative min-h-[620px] overflow-hidden rounded-lg border border-slate-200 bg-slate-50"
          onPointerDown={beginPan}
          onPointerMove={updatePan}
          onPointerUp={endPan}
          onPointerCancel={endPan}
          style={{
            cursor: dragging ? "grabbing" : "grab",
            touchAction: "none",
            backgroundImage:
              "linear-gradient(rgba(15,23,42,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.05) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        >
          <div className="pointer-events-none absolute left-4 top-4 z-20 rounded-md border border-slate-200 bg-white/95 px-3 py-1 text-xs font-semibold text-slate-700">
            通用技能
          </div>
          <div className="pointer-events-none absolute right-4 top-4 z-20 rounded-md border border-slate-200 bg-white/95 px-3 py-1 text-xs font-semibold text-slate-700">
            专业技能
          </div>
          <div className="pointer-events-none absolute left-1/2 top-0 h-full w-px bg-slate-200" />
          <div className="pointer-events-none absolute left-1/2 top-4 z-20 -translate-x-1/2 rounded-md border border-slate-200 bg-white/95 px-3 py-1 text-xs font-medium text-slate-500">
            抓手拖动视图
          </div>

          <div
            className="absolute left-0 top-0 w-full"
            style={{ height, transform: `translate(${pan.x}px, ${pan.y}px)`, willChange: dragging ? "transform" : undefined }}
          >
            <svg className="pointer-events-none absolute left-0 top-0 h-full w-full overflow-visible">
              {tree.edges.map(([fromId, toId]) => {
                const from = nodesById.get(fromId);
                const to = nodesById.get(toId);
                if (!from || !to) return null;
                const planned = to.nodeType === "planned";
                return (
                  <line
                    key={`${fromId}-${toId}`}
                    x1={`${from.x}%`}
                    y1={nodeTop(from)}
                    x2={`${to.x}%`}
                    y2={nodeTop(to)}
                    stroke={planned ? "#64748b" : "var(--accent-teal)"}
                    strokeDasharray={planned ? "5 4" : "none"}
                    strokeWidth={2.5}
                    opacity={planned ? 0.5 : 0.75}
                  />
                );
              })}
            </svg>

            {tree.nodes.map((node) => (
              <button
                key={node.id}
                type="button"
                className="configured-skill-node absolute flex min-w-[154px] max-w-[200px] items-center gap-2 rounded-md border bg-white px-3 py-2 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                style={{
                  left: `${node.x}%`,
                  top: nodeTop(node),
                  transform: "translate(-50%, -50%)",
                  borderColor: selectedNode?.id === node.id ? nodeTone(node) : "#dbe3ee",
                  boxShadow: selectedNode?.id === node.id ? `0 0 0 3px color-mix(in srgb, ${nodeTone(node)} 18%, transparent)` : undefined,
                }}
                onClick={() => setSelectedNodeId(node.id)}
              >
                <span
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-sm font-bold text-white"
                  style={{ background: nodeTone(node) }}
                >
                  {node.nodeType === "model" ? "B" : node.label.slice(0, 1).toUpperCase()}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-950">{node.label}</span>
                  <span className="block truncate text-xs text-slate-500">{nodeTypeLabel[node.nodeType]} · {branchName(node.branch)}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {selectedNode ? (
          <NodeInspector tree={tree} node={selectedNode} />
        ) : (
          <div className="text-sm text-slate-600">选择一个节点查看配置详情。</div>
        )}
      </aside>
    </div>
  );
}

function NodeInspector({ tree, node }: { tree: ConfigSkillTreeConfig; node: ConfigSkillTreeNode }) {
  return (
    <div>
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md text-sm font-bold text-white" style={{ background: nodeTone(node) }}>
          {node.nodeType === "model" ? <Database size={18} /> : <GitBranch size={18} />}
        </span>
        <div className="min-w-0">
          <h4 className="text-base font-semibold text-slate-950">{node.label}</h4>
          <p className="mt-1 text-xs text-slate-500">{nodeTypeLabel[node.nodeType]} · {branchName(node.branch)}</p>
        </div>
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-700">{node.description || "暂无说明。"}</p>

      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <InfoCell label="Agent" value={tree.agent.name} />
        <InfoCell label="模型" value={node.model || tree.agent.model} />
        <InfoCell label="运行时" value={node.skillRuntime || tree.agent.runtime} />
        <InfoCell label="类别" value={node.category} />
      </div>

      {node.skillName || node.skillPath ? (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
            <FileText size={15} />
            真实 Skill
          </div>
          <div className="text-sm text-slate-700">{node.skillName || "--"}</div>
          {node.skillPath ? <div className="mt-2 break-all text-sm text-blue-700">{node.skillPath}</div> : null}
        </div>
      ) : (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          该节点不对应真实 SKILL.md。
        </div>
      )}

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
        <div className="text-xs font-semibold text-slate-500">配置文件</div>
        <div className="mt-1 break-all text-sm text-slate-700">{tree.configPath || "--"}</div>
      </div>
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 truncate text-sm font-medium text-slate-900">{value || "--"}</div>
    </div>
  );
}
