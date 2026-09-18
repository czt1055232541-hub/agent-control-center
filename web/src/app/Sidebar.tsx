import { Archive, CalendarClock, FileCog, FileText, LayoutDashboard, PackageOpen, Route, Send, ServerCog, ScrollText, Swords, Settings } from "lucide-react";
import type { AccPlugin } from "../plugins/types";

export type CommandPage = string;

const icons = { "layout-dashboard": LayoutDashboard, swords: Swords, "calendar-clock": CalendarClock, send: Send, "server-cog": ServerCog, route: Route, "package-open": PackageOpen, "file-cog": FileCog, "file-text": FileText, archive: Archive };

export function Sidebar({
  activePage,
  onNavigate,
  plugins,
}: {
  activePage: CommandPage;
  onNavigate: (page: CommandPage) => void;
  plugins: AccPlugin[];
}) {
  const navItems = plugins
    .flatMap((plugin) => plugin.cards.map((card) => ({ plugin, card })))
    .sort((left, right) => left.card.order - right.card.order || left.card.id.localeCompare(right.card.id));
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
        <p className="px-3 text-xs text-slate-500">已启用的功能插件</p>
        {navItems.map(({ plugin, card }) => {
          const Icon = icons[card.icon as keyof typeof icons] ?? PackageOpen;
          const active = activePage === card.page;
          return (
            <button
              key={card.id}
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
              onClick={() => onNavigate(card.page)}
              type="button"
            >
              <Icon size={16} />
              <span className="truncate">{card.title}</span>
              <span className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] ${
                active ? "bg-white/15 text-white" : plugin.state === "native" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              }`}>
                {plugin.state === "native" ? "插件" : "迁移中"}
              </span>
            </button>
          );
        })}
      </nav>
      <button type="button" onClick={() => onNavigate("__settings__")}
        aria-current={activePage === "__settings__" ? "page" : undefined}
        className={`mt-4 flex min-h-10 w-full items-center gap-2 rounded-md border px-3 py-2 text-sm ${activePage === "__settings__" ? "bg-teal-700 text-white" : "bg-white/60 text-slate-700"}`}>
        <Settings size={16} />设置 · 功能插件
      </button>
      <div className="mt-4 rounded-md border p-3 text-xs" style={{borderColor: "var(--border-stone)", background: "rgba(255,247,232,0.7)", color: "var(--text-secondary)"}}>
        功能插件由框架统一启停配置。“外部应用”仅管理独立程序的进程与页面，不是第二套插件目录。
      </div>
    </aside>
  );
}
