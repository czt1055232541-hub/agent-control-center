import { AlertTriangle, ShieldCheck } from "lucide-react";
import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";
import { clientRegistry } from "../plugins/clientPlugins";
import { StatusPill } from "../components/common/StatusPill";
import { Sidebar, type CommandPage } from "./Sidebar";
import { readJson } from "../api";
import { usePluginInventory } from "../hooks/usePluginInventory";
import { PluginDetailPage } from "../modules/plugin-catalog/PluginDetailPage";
import { AppErrorBoundary } from "../components/common/AppErrorBoundary";
import { PluginSettingsPage } from "./PluginSettingsPage";

function App() {
  const { plugins, pluginsError } = usePluginInventory();
  const [token, setToken] = React.useState("");
  const [sessionError, setSessionError] = React.useState("");
  React.useEffect(() => {
    let active = true;
    readJson<{ token: string }>("/api/session")
      .then(value => { if (active) setToken(value.token); })
      .catch(reason => { if (active) setSessionError(String(reason)); });
    return () => { active = false; };
  }, []);
  const [requestedPage, setActivePage] = React.useState<CommandPage>("dashboard");
  const availableCards = plugins.flatMap(p => p.cards).sort((a,b) => a.order-b.order);
  const activePage = requestedPage === "__settings__" || availableCards.some(c => c.page === requestedPage) ? requestedPage : availableCards[0]?.page ?? "__settings__";
  const PluginPage = clientRegistry.resolve(activePage, plugins);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="grid w-full gap-5 px-5 py-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Sidebar activePage={activePage} onNavigate={setActivePage} plugins={plugins} />
        <div className="flex min-w-0 flex-col gap-5">
          <header className="flex flex-col gap-4 border-b border-slate-300 pb-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-950">ACC 插件工作台</h1>
              <p className="mt-1 text-sm text-slate-600">框架承载功能插件 · 独立管理外部应用</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusPill active={Boolean(token)} label={token ? "框架已连接" : "正在连接框架"} />
              <StatusPill active={!pluginsError} label={`${plugins.filter(p => p.kind !== "framework").length} 个功能插件`} />
            </div>
          </header>

          {sessionError || pluginsError ? (
            <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span>{sessionError || pluginsError}</span>
            </div>
          ) : null}


          {activePage === "__settings__" ? <PluginSettingsPage token={token} /> : PluginPage ? <PluginPage key={activePage} token={token} /> : null}


          {!PluginPage && activePage !== "__settings__" ? (
            <PluginDetailPage plugin={plugins.find((plugin) => plugin.cards.some((card) => card.page === activePage)) ?? null} />
          ) : null}

          <footer className="flex items-center gap-2 pb-2 text-xs text-slate-500">
            <ShieldCheck size={14} />
            <span>Write actions require a local token and run only against 127.0.0.1.</span>
          </footer>
        </div>
      </div>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <React.Suspense fallback={<main className="min-h-screen bg-slate-100 p-6 text-slate-600">正在加载控制中心…</main>}>
        <App />
      </React.Suspense>
    </AppErrorBoundary>
  </React.StrictMode>,
);
