import React from "react";
import { readJson } from "../api";

export type PluginSetting = {
  id: string; name: string; description: string; kind: string; requires: string[];
  configured_enabled: boolean; next_start_enabled: boolean; running_enabled: boolean;
};
export type PluginSettings = {
  plugins: PluginSetting[]; disabled: string[]; environment_override: boolean; restart_required: boolean;
};

export function PluginSettingsForm({ settings, disabled, onToggle, onSave, busy, canSave }: {
  settings: PluginSettings; disabled: string[]; onToggle: (id: string) => void;
  onSave: () => void; busy: boolean; canSave: boolean;
}) {
  return <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <h2 className="text-lg font-semibold">设置 · 功能插件</h2>
    <p className="mt-2 text-sm text-slate-600">侧边栏的每项功能对应一个已启用插件。设置属于框架，即使关闭全部功能仍可进入。</p>
    <p className="mt-2 text-sm text-slate-600">保存后需重启 ACC 才会生效；不会自动中断任务、停止外部应用或删除数据。依赖校验失败时整次保存会被拒绝。</p>
    <details className="mt-2 text-sm text-slate-600"><summary className="cursor-pointer">如何应用与回退设置</summary>
      <p className="mt-2">确认 ACC 当前无操作执行后，在项目目录依次运行以下命令。仅重启 ACC，不重启 DSH 或外部应用。</p>
      <pre className="mt-2 overflow-x-auto rounded bg-slate-100 p-3">{"python scripts/stack.py stop-control-center\npython scripts/stack.py serve-control-center --no-build --open"}</pre>
      <p className="mt-2">需要撤销时，重新勾选原插件并保存；若无法启动，可将 plugin-settings.local.json.bak 恢复为同目录下的 plugin-settings.local.json。</p>
    </details>
    {settings.environment_override && <p role="status" className="mt-3 rounded bg-amber-50 p-3 text-sm text-amber-900">ACC_DISABLED_PLUGINS 环境变量正在覆盖本地配置（空值也算覆盖）。请移除该变量并重启 ACC 后再修改设置。</p>}
    {settings.restart_required && <p role="status" className="mt-3 rounded bg-amber-50 p-3 text-sm text-amber-900">配置已更改，等待重启 ACC。侧边栏仍反映当前进程已加载的插件。</p>}
    <div className="mt-4 grid gap-3">
      {settings.plugins.map(plugin => <div key={plugin.id} className="rounded-md border border-slate-200 p-3">
        <label className="flex items-start gap-3">
          <input type="checkbox" className="mt-1" checked={!disabled.includes(plugin.id)}
            disabled={plugin.kind === "framework" || settings.environment_override || busy}
            onChange={() => onToggle(plugin.id)} />
          <span className="min-w-0">
            <span className="font-medium">{plugin.name}</span>
            <span className="ml-2 text-xs text-slate-500">{plugin.kind === "framework" ? "框架 · 不可关闭" : plugin.id}</span>
            <span className="mt-1 block text-sm text-slate-600">{plugin.description}</span>
            <span className="mt-1 block text-xs text-slate-500">当前运行：{plugin.running_enabled ? "已启用" : "已停用"} · 已保存配置：{plugin.configured_enabled ? "启用" : "停用"} · 下次启动：{plugin.next_start_enabled ? "启用" : "停用"}</span>
            {plugin.requires.length > 0 && <span className="mt-1 block text-xs text-slate-500">依赖：{plugin.requires.join("、")}</span>}
          </span>
        </label>
      </div>)}
    </div>
    <button type="button" className="mt-4 rounded bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-50"
      disabled={!canSave || busy || settings.environment_override} onClick={onSave}>{busy ? "保存中…" : "保存插件设置"}</button>
  </section>;
}

export function PluginSettingsPage({ token }: { token: string }) {
  const [settings, setSettings] = React.useState<PluginSettings | null>(null);
  const [disabled, setDisabled] = React.useState<string[]>([]);
  const [error, setError] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const load = React.useCallback(async () => {
    try {
      const next = await readJson<PluginSettings>("/api/plugins/settings");
      setSettings(next); setDisabled(next.disabled); setError("");
    } catch (reason) { setError(String(reason)); }
  }, []);
  React.useEffect(() => { void load(); }, [load]);
  async function save() {
    setBusy(true); setError(""); setMessage("");
    try {
      const next = await readJson<PluginSettings>("/api/plugins/settings", {
        method: "PUT", headers: { "Content-Type": "application/json", "X-Control-Token": token },
        body: JSON.stringify({ disabled }),
      });
      setSettings(next); setDisabled(next.disabled);
      setMessage(next.restart_required ? "已保存，请重启 ACC 后生效。DSH 无需重启。" : "已保存，配置与当前运行状态一致。");
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  }
  return <div className="grid gap-3">
    {error && <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
    {message && <div role="status" className="rounded bg-emerald-50 p-3 text-sm text-emerald-900">{message}</div>}
    {settings ? <PluginSettingsForm settings={settings} disabled={disabled} busy={busy} canSave={Boolean(token)}
      onToggle={id => setDisabled(current => current.includes(id) ? current.filter(value => value !== id) : [...current, id])}
      onSave={() => void save()} /> : <button type="button" onClick={() => void load()}>加载插件设置（点击重试）</button>}
  </div>;
}
