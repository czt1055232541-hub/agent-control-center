import React from "react";
import { readJson } from "../../api";
import type { OperationResult, ThreadListItem } from "../../types";

export function BackupPage({ token }: { token: string }) {
  const [threads, setThreads] = React.useState<ThreadListItem[]>([]);
  const [sessionId, setSessionId] = React.useState("");
  const [provider, setProvider] = React.useState("native");
  const [confirmed, setConfirmed] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [result, setResult] = React.useState<OperationResult | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      const data = await readJson<{ threads: ThreadListItem[] }>("/api/thread-migration/threads?limit=20");
      setThreads(data.threads);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, []);
  React.useEffect(() => { void refresh(); }, [refresh]);

  async function run(path: string, body?: unknown) {
    if (!token || busy) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await readJson<OperationResult>(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Control-Token": token },
        body: body === undefined ? undefined : JSON.stringify(body),
      }));
      setConfirmed(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  return <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5">
    <h2 className="text-lg font-semibold">备份与迁移</h2>
    <p className="text-sm text-slate-600">将已有线程交接到目标 Provider，或按已配置的保留策略清理旧备份。</p>
    {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
    {result ? <p role="status" className="text-sm">{result.ok ? "完成" : "未完成"}：{result.message}</p> : null}
    <div className="space-y-3 rounded-lg border border-slate-200 p-4">
      <h3 className="font-medium">线程迁移</h3>
      <label className="block text-sm">源线程
        <select className="mt-1 block w-full rounded border p-2" value={sessionId} onChange={e => setSessionId(e.target.value)} disabled={busy}>
          <option value="">请选择线程</option>
          {threads.map(thread => <option key={thread.session_id} value={thread.session_id}>{thread.title || thread.session_id} · {thread.provider}</option>)}
        </select>
      </label>
      <label className="block text-sm">目标 Provider
        <select className="ml-2 rounded border p-2" value={provider} onChange={e => setProvider(e.target.value)} disabled={busy}>
          <option value="native">Native</option><option value="deepseek">DeepSeek</option>
        </select>
      </label>
      <div className="flex gap-3">
        <button className="rounded bg-cyan-700 px-3 py-2 text-sm text-white disabled:opacity-50" disabled={busy || !token || !sessionId}
          onClick={() => void run("/api/thread-migration/migrate", { session_id: sessionId, target_provider: provider })}>开始迁移</button>
        <button className="rounded border px-3 py-2 text-sm" disabled={busy} onClick={() => void refresh()}>刷新线程</button>
      </div>
    </div>
    <div className="space-y-3 rounded-lg border border-slate-200 p-4">
      <h3 className="font-medium">旧备份清理</h3>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} />确认按保留策略删除过期备份</label>
      <button className="rounded bg-red-700 px-3 py-2 text-sm text-white disabled:opacity-50" disabled={busy || !token || !confirmed}
        onClick={() => void run("/api/backups/clean")}>清理旧备份</button>
    </div>
  </section>;
}
