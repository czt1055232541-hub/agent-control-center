import { AlertTriangle, ShieldCheck } from "lucide-react";
import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";
import { clientRegistry } from "../plugins/clientPlugins";
import { StatusPill } from "../components/common/StatusPill";
import { Sidebar, type CommandPage } from "./Sidebar";
import { useStatus } from "../hooks/useStatus";
import { usePluginInventory } from "../hooks/usePluginInventory";
import { PluginDetailPage } from "../modules/plugin-catalog/PluginDetailPage";
import { AppErrorBoundary } from "../components/common/AppErrorBoundary";

function App() {
  const { plugins, pluginsError } = usePluginInventory();
  const { token, status, error: statusError } = useStatus(plugins.some(p => p.id === "acc.dashboard"), false);
  const [requestedPage, setActivePage] = React.useState<CommandPage>("dashboard");
  const availableCards = plugins.flatMap(p => p.cards).sort((a,b) => a.order-b.order);
  const activePage = availableCards.some(c => c.page === requestedPage) ? requestedPage : availableCards[0]?.page ?? "__no_plugins__";
  const PluginPage = clientRegistry.resolve(activePage, plugins);
  const appProviderMode = status?.codex_app?.mode ?? status?.codex.mode ?? "unknown";
  const agentProviderMode = status?.codex_agent_provider?.mode ?? status?.codex.mode ?? "unknown";

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="grid w-full gap-5 px-5 py-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Sidebar activePage={activePage} onNavigate={setActivePage} plugins={plugins} />
        <div className="flex min-w-0 flex-col gap-5">
          <header className="flex flex-col gap-4 border-b border-slate-300 pb-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-950">多 Agent 作战指挥台</h1>
              <p className="mt-1 text-sm text-slate-600">{status?.stack_root ?? "Loading stack status..."}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusPill active={appProviderMode === "deepseek"} label={`App: ${appProviderMode}`} />
              <StatusPill active={agentProviderMode === "deepseek"} label={`Agent: ${agentProviderMode}`} />
              <StatusPill active={Boolean(status?.codex_desktop_running)} label="Codex Desktop" />
            </div>
          </header>

          {statusError || pluginsError ? (
            <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span>{statusError || pluginsError}</span>
            </div>
          ) : null}


          {PluginPage ? <PluginPage key={activePage} token={token} /> : null}


          {!PluginPage ? (
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
