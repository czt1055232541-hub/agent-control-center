import { Archive, Bot, CalendarClock, FileCog, FileText, LayoutDashboard, Network, Route, Send, ServerCog, ScrollText, Swords, Wrench, Shield } from "lucide-react";

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
  { key: "agents", label: "Agent 阵列", icon: Swords, status: "已实现" },
  { key: "tasks", label: "任务战场", icon: CalendarClock, status: "已实现" },
  { key: "feishu", label: "飞书连接", icon: Send, status: "已实现" },
  { key: "provider", label: "模型与 Provider", icon: ServerCog, status: "已实现" },
  { key: "routing", label: "路由规则", icon: Route, status: "已实现" },
  { key: "config", label: "配置中心", icon: FileCog, status: "已实现" },
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
    <aside className="temple-sidebar parchment-panel p-3 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)]"
      style={{
        background: "linear-gradient(180deg, rgba(255,255,255,0.3), rgba(255,255,255,0)), var(--bg-sidebar)",
        borderRight: "2px solid var(--border-stone)"
      }}>
      <div className="mb-4 px-2">
        <div className="flex items-center gap-2 text-base font-semibold" style={{color: "var(--text-main)"}}>
          <ScrollText size={18} style={{color: "var(--accent-teal)"}} />
          <span>探明控制中心</span>
        </div>
        <p className="mt-1 text-xs" style={{color: "var(--text-muted)"}}>Agent Control Center</p>
      </div>
      <nav className="grid gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = activePage === item.key;
          return (
            <button
              key={item.label}
              className={`nav-item flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition ${
                active ? "nav-item-active" : ""
              }`}
              style={{
                color: active ? "#fffaf0" : "var(--text-main)",
                background: active ? "linear-gradient(180deg, #38c3bd, #158f9a)" : "transparent",
                borderColor: active ? "#0d7581" : "transparent",
                border: "1px solid",
                boxShadow: active ? "0 2px 0 rgba(79, 52, 22, 0.28)" : "none"
              }}
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
      <div className="mt-4 rounded-md border p-3 text-xs" style={{borderColor: "var(--border-stone)", background: "rgba(255,247,232,0.7)", color: "var(--text-secondary)"}}>
        Agent 阵列 — 管理你的探明队伍。每个 Agent 都有明确的职业、装备、技能树和任务表现。
      </div>
    </aside>
  );
}
