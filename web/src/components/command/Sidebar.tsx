import { Archive, Bot, CalendarClock, FileCog, FileText, LayoutDashboard, Network, Route, Send, ServerCog } from "lucide-react";

export type CommandPage =
  | "dashboard"
  | "agents"
  | "tasks"
  | "feishu"
  | "provider"
  | "routing"
  | "config"
  | "diagnostics"
  | "backup";

const navItems: Array<{
  key: CommandPage;
  label: string;
  icon: typeof LayoutDashboard;
  status: "已实现" | "开发中" | "后续";
}> = [
  { key: "dashboard", label: "Dashboard 总览", icon: LayoutDashboard, status: "已实现" },
  { key: "agents", label: "Agent 管理", icon: Bot, status: "已实现" },
  { key: "tasks", label: "任务监控", icon: CalendarClock, status: "后续" },
  { key: "feishu", label: "飞书连接", icon: Send, status: "后续" },
  { key: "provider", label: "模型与 Provider", icon: ServerCog, status: "已实现" },
  { key: "routing", label: "路由规则", icon: Route, status: "后续" },
  { key: "config", label: "配置中心", icon: FileCog, status: "开发中" },
  { key: "diagnostics", label: "日志与诊断", icon: FileText, status: "已实现" },
  { key: "backup", label: "备份与迁移", icon: Archive, status: "后续" },
];

export function Sidebar({
  activePage,
  onNavigate,
}: {
  activePage: CommandPage;
  onNavigate: (page: CommandPage) => void;
}) {
  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)]">
      <div className="mb-4 px-2">
        <div className="flex items-center gap-2 text-base font-semibold text-slate-950">
          <Network size={18} />
          <span>Command</span>
        </div>
        <p className="mt-1 text-xs text-slate-500">Agent Control Center</p>
      </div>
      <nav className="grid gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = activePage === item.key;
          return (
            <button
              key={item.label}
              className={`flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition ${
                active ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
              }`}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              <Icon size={16} />
              <span className="truncate">{item.label}</span>
              <span className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] ${
                active ? "bg-white/15 text-white" : item.status === "已实现" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
              }`}>
                {item.status}
              </span>
            </button>
          );
        })}
      </nav>
      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
        首轮聚焦真实 Agent、基础设施、Provider 和日志诊断；后续模块展示开发计划与依赖数据源。
      </div>
    </aside>
  );
}
