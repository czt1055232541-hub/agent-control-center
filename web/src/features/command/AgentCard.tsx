import { Eye, FolderOpen, Info, Play, RefreshCcw, Square, Terminal } from "lucide-react";
import type { AgentConfig, BackendAction } from "../../types";
import { ActionButton } from "../../components/common/ActionButton";
import { statusClasses, statusLabel } from "./statusStyles";

function actionIcon(action: BackendAction) {
  if (action.kind === "log") return <Terminal size={16} />;
  if (action.kind === "detail") return <Eye size={16} />;
  if (action.kind === "open") return <FolderOpen size={16} />;
  if (action.kind === "provider") return <RefreshCcw size={16} />;
  if (action.kind === "info") return <Info size={16} />;
  if (action.key === "start") return <Play size={16} />;
  if (action.key === "stop") return <Square size={16} />;
  if (action.key === "restart") return <RefreshCcw size={16} />;
  return <Play size={16} />;
}

export function AgentCard({
  agent,
  busy,
  onRun,
  onLogs,
  onSelect,
}: {
  agent: AgentConfig;
  busy: boolean;
  onRun: (path: string) => void;
  onLogs: (component?: string) => void;
  onSelect: (agent: AgentConfig) => void;
}) {
  const backendActions = agent.backendActions ?? [];
  const primaryActions = backendActions.filter((action) => action.enabled && ["operation", "log", "detail", "open", "provider"].includes(action.kind));
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{agent.name}</h3>
          <p className="mt-1 line-clamp-2 min-h-10 text-sm text-slate-600">{agent.role}</p>
        </div>
        <span className={`shrink-0 rounded-md border px-2 py-1 text-xs font-medium ${statusClasses(agent.status)}`}>
          {statusLabel(agent.status)}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
        <div>
          <div className="text-xs text-slate-500">来源</div>
          <div className="truncate font-medium text-slate-900">{agent.source || "--"}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">承载组件</div>
          <div className="truncate font-medium text-slate-900">{agent.backingComponent || "--"}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">Provider / Model</div>
          <div className="truncate font-medium text-slate-900">{agent.provider || "--"} / {agent.model || "--"}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">会话 / 绑定</div>
          <div className="truncate font-medium text-slate-900">{agent.sessionCount ?? "--"} / {agent.bindingStatus || "--"}</div>
        </div>
      </div>

      <div className="mt-4 rounded-md bg-slate-50 p-3 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="text-slate-500">权限</span>
          <span className="font-medium text-slate-900">{agent.permissionLevel || "--"}</span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-slate-500">Workspace</span>
          <span className="truncate font-medium text-slate-900">{agent.workspacePath || agent.configPath || "--"}</span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-slate-500">最近交互</span>
          <span className="truncate font-medium text-slate-900">{agent.lastInteractionAt ?? agent.lastCalledAt ?? "--"}</span>
        </div>
        {agent.lastError ? <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800">{agent.lastError}</div> : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {primaryActions.map((action) => (
          <ActionButton
            key={`${action.kind}-${action.key}`}
            disabled={busy || !action.enabled}
            danger={action.danger}
            icon={actionIcon(action)}
            label={action.label}
            onClick={() => {
              if (action.kind === "detail") onSelect(agent);
              else if (action.logComponent) onLogs(action.logComponent);
              else if (action.endpoint) onRun(action.endpoint);
            }}
          />
        ))}
      </div>

      <div className="mt-3 rounded-md border border-slate-200 bg-white p-3">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">后端功能映射</div>
        <div className="space-y-1">
          {backendActions.length ? backendActions.map((action) => (
            <div key={`${action.kind}-${action.key}-route`} className="flex items-center justify-between gap-3 text-xs">
              <span className={action.enabled ? "text-slate-700" : "text-slate-400"}>{action.label}</span>
              <code className="truncate rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                {action.endpoint ?? (action.logComponent ? `logs:${action.logComponent}` : action.kind)}
              </code>
            </div>
          )) : <div className="text-xs text-slate-500">未声明可用后端功能</div>}
        </div>
      </div>
    </article>
  );
}
