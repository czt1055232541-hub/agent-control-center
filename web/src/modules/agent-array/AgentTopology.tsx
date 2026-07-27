import { ArrowRight, Bot, MessageSquare } from "lucide-react";
import type { AgentConfig, AgentStatus } from "../../types";
import { SortableGrid, type SortableGridItem } from "../../components/common/SortableGrid";

function availabilityClasses(status: AgentStatus | "normal" | "unknown") {
  const classes: Record<string, string> = {
    running: "border-emerald-300 bg-emerald-50 text-emerald-950",
    normal: "border-emerald-300 bg-emerald-50 text-emerald-950",
    executing: "border-emerald-300 bg-emerald-50 text-emerald-950",
    warning: "border-amber-300 bg-amber-50 text-amber-950",
    stopped: "border-stone-300 bg-stone-100 text-stone-800",
    unknown: "border-stone-300 bg-stone-100 text-stone-800",
    error: "border-red-300 bg-red-50 text-red-950",
  };
  return classes[status] ?? classes.unknown;
}

function availabilityLabel(status: AgentStatus | "normal" | "unknown") {
  const labels: Record<string, string> = {
    running: "后端已启动",
    normal: "链路正常",
    executing: "后端已启动",
    warning: "部分异常",
    stopped: "未启动",
    unknown: "未知",
    error: "异常",
  };
  return labels[status] ?? status;
}

function isGenerating(status: AgentStatus | "normal" | "unknown", currentTask?: string | null) {
  const task = (currentTask ?? "").trim();
  return status === "executing" || Boolean(task && task !== "--");
}

function Node({
  label,
  status,
  currentTask,
  icon,
  onClick,
}: {
  label: string;
  status: AgentStatus | "normal" | "unknown";
  currentTask?: string | null;
  icon: React.ReactNode;
  onClick?: () => void;
}) {
  const generating = isGenerating(status, currentTask);
  return (
    <button
      className={`flex min-h-16 items-center gap-3 rounded-lg border px-3 py-2 text-left shadow-sm transition hover:shadow ${availabilityClasses(status)}`}
      onClick={onClick}
      type="button"
    >
      <span className="shrink-0">{icon}</span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-slate-950">{label}</span>
        <span className="mt-1 flex items-center gap-1 text-xs opacity-80">
          <span className={`h-2 w-2 rounded-full ${generating ? "bg-sky-500 shadow-[0_0_0_3px_rgba(14,165,233,0.18)]" : "bg-slate-300"}`} />
          {generating ? "生成中" : `闲置 · ${availabilityLabel(status)}`}
        </span>
      </span>
    </button>
  );
}

function Connector() {
  return (
    <div className="flex items-center justify-center text-slate-400">
      <ArrowRight size={18} />
    </div>
  );
}

export function AgentTopology({
  agents,
  onSelect,
}: {
  agents: AgentConfig[];
  onSelect: (agent: AgentConfig) => void;
}) {
  const byId = new Map(agents.map((agent) => [agent.id, agent]));
  const coordinator = byId.get("openclaw-coordinator");
  const downstream = ["codex-code-agent", "openclaw-orchestrator", "openclaw-main", "openclaw-archivist"]
    .map((id) => byId.get(id))
    .filter((agent): agent is AgentConfig => Boolean(agent));
  const downstreamItems: SortableGridItem[] = downstream.map((agent) => ({
    id: agent.id,
    node: (
      <Node
        label={agent.name}
        status={agent.status}
        currentTask={agent.currentTask}
        icon={<Bot size={18} />}
        onClick={() => onSelect(agent)}
      />
    ),
  }));

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Agent 拓扑图 / 调用链路</h2>
          <p className="mt-1 text-sm text-slate-600">真实团队链路：飞书群聊由项目调度官分派到代码、运维、审计和档案角色。</p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1.2fr)]">
        <Node label="飞书群聊" status={coordinator?.status ?? "unknown"} icon={<MessageSquare size={18} />} />
        <Connector />
        <Node
          label={coordinator?.name ?? "项目调度官"}
          status={coordinator?.status ?? "unknown"}
          currentTask={coordinator?.currentTask}
          icon={<Bot size={18} />}
          onClick={() => coordinator && onSelect(coordinator)}
        />
      </div>

      <SortableGrid
        ariaLabel="Agent topology cards"
        className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        items={downstreamItems}
        maxColSpan={3}
        storageKey="acc.dashboard.agentTopologyLayout"
      />
    </section>
  );
}
