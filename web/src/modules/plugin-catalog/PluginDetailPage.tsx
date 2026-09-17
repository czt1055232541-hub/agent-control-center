import { Boxes, ExternalLink } from "lucide-react";

import type { AccPlugin } from "../../plugins/types";

export function PluginDetailPage({ plugin }: { plugin: AccPlugin | null }) {
  if (!plugin) {
    return (
      <section className="rounded-lg border border-amber-300 bg-amber-50 p-5 text-amber-950">
        当前页面没有可用的插件贡献。刷新插件清单后重试。
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <div className="rounded-lg bg-cyan-50 p-3 text-cyan-700"><Boxes size={24} /></div>
          <div>
            <h2 className="text-lg font-semibold text-slate-950">{plugin.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{plugin.description}</p>
          </div>
        </div>
        <span className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600">
          {plugin.state} · v{plugin.version}
        </span>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {plugin.cards.map((card) => (
          <article key={card.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
              <ExternalLink size={15} /> {card.title}
            </div>
            <p className="mt-2 text-sm text-slate-600">{card.description}</p>
            {card.href?.startsWith("/") && !card.href.startsWith("//") && !/[\\\s]/.test(card.href) ? (
              <a href={card.href} target="_blank" rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-2 rounded bg-cyan-700 px-3 py-2 text-sm text-white hover:bg-cyan-800">
                打开功能 <ExternalLink size={14} />
              </a>
            ) : null}
          </article>
        ))}
      </div>
      <div className="mt-5">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Capabilities</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {plugin.capabilities.length ? plugin.capabilities.map((capability) => (
            <code key={capability} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{capability}</code>
          )) : <span className="text-sm text-slate-500">未声明能力</span>}
        </div>
      </div>
    </section>
  );
}
