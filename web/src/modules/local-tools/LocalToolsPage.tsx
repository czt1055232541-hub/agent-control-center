import React from "react";
import { CheckCircle2, ExternalLink, FileCode2, FilePlus2, Play, RefreshCcw, ScrollText, Search, Square } from "lucide-react";
import { readJson } from "../../api";
import { ActionButton } from "../../components/common/ActionButton";
import { StatusPill } from "../../components/common/StatusPill";

type LocalTool = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  embed: boolean;
  tags: string[];
  url: string;
  open_url: string;
  health_url: string;
  dir: string;
  entry: string;
  command: string[];
  runtime: string;
  source: string;
  manifest_path: string | null;
  stdout_log: string;
  stderr_log: string;
  port: number | null;
  port_listening: boolean;
  pid_running: boolean;
  health_ok: boolean;
  pid?: number | null;
};

type LocalToolCandidate = {
  id: string;
  name: string;
  description: string;
  dir: string;
  manifest: string;
  manifest_path: string | null;
  runtime: string;
  entry: string;
  host: string;
  port: number;
  url: string;
  health_path: string;
  open_path: string;
  embed: boolean;
  enabled: boolean;
  tags: string[];
  registered: boolean;
};

type RegisterDraft = {
  id: string;
  name: string;
  description: string;
  dir: string;
  manifest: string;
  entry: string;
  runtime: string;
  host: string;
  port: number;
  url: string;
  healthPath: string;
  openPath: string;
  enabled: boolean;
  embed: boolean;
  tags: string[];
};

type OperationResult = {
  ok: boolean;
  component: string;
  action: string;
  message: string;
};

type LogTail = {
  path: string;
  exists?: boolean;
  lines: string[];
};

function running(tool: LocalTool): boolean {
  return Boolean(tool.port_listening || tool.pid_running || tool.health_ok);
}

function iframeUrl(tool: LocalTool): string {
  const raw = tool.open_url || tool.url;
  try {
    const url = new URL(raw);
    url.searchParams.set("managed", "1");
    url.searchParams.set("session", `acc-${tool.id}`);
    url.searchParams.set("embed", "acc");
    return url.toString();
  } catch {
    const joiner = raw.includes("?") ? "&" : "?";
    return `${raw}${joiner}managed=1&session=${encodeURIComponent(`acc-${tool.id}`)}&embed=acc`;
  }
}

function draftFromManifest(manifest: Record<string, unknown>, filename: string): RegisterDraft {
  const runtime = String(manifest.runtime ?? manifest.kind ?? "python");
  const host = String(manifest.host ?? "127.0.0.1");
  const port = Number(manifest.port ?? 0);
  const id = String(manifest.id ?? filename.replace(/\.[^.]+$/, "")).trim();
  const tags = Array.isArray(manifest.tags) ? manifest.tags.map(String) : [];
  return {
    id,
    name: String(manifest.name ?? id),
    description: String(manifest.description ?? ""),
    dir: String(manifest.dir ?? ""),
    manifest: filename,
    entry: String(manifest.entry ?? (runtime === "node" ? "index.js" : "app.py")),
    runtime,
    host,
    port,
    url: String(manifest.url ?? (port ? `http://${host}:${port}` : "")),
    healthPath: String(manifest.healthPath ?? manifest.health_path ?? "/api/health"),
    openPath: String(manifest.openPath ?? manifest.open_path ?? "/"),
    enabled: Boolean(manifest.enabled ?? true),
    embed: Boolean(manifest.embed ?? true),
    tags,
  };
}

function draftFromCandidate(candidate: LocalToolCandidate): RegisterDraft {
  return {
    id: candidate.id,
    name: candidate.name,
    description: candidate.description,
    dir: candidate.dir,
    manifest: candidate.manifest,
    entry: candidate.entry,
    runtime: candidate.runtime,
    host: candidate.host,
    port: candidate.port,
    url: candidate.url,
    healthPath: candidate.health_path,
    openPath: candidate.open_path,
    enabled: candidate.enabled,
    embed: candidate.embed,
    tags: candidate.tags,
  };
}

export function LocalToolsPage({ token }: { token: string | null }) {
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const [tools, setTools] = React.useState<LocalTool[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<OperationResult | null>(null);
  const [logs, setLogs] = React.useState<LogTail[]>([]);
  const [logsBusy, setLogsBusy] = React.useState(false);
  const [scanRoot, setScanRoot] = React.useState("");
  const [candidates, setCandidates] = React.useState<LocalToolCandidate[]>([]);
  const [draft, setDraft] = React.useState<RegisterDraft | null>(null);

  const load = React.useCallback(async () => {
    const data = await readJson<{ tools: LocalTool[] }>("/api/local-tools");
    setTools(data.tools);
    setSelectedId((current) => current ?? data.tools[0]?.id ?? null);
  }, []);

  React.useEffect(() => {
    load().catch((exc) => setError(exc instanceof Error ? exc.message : String(exc)));
  }, [load]);

  const requireToken = React.useCallback(() => {
    if (token) {
      return true;
    }
    setError("缺少控制 token，无法执行写操作。");
    return false;
  }, [token]);

  const run = React.useCallback(async (toolId: string, action: "start" | "stop" | "restart") => {
    if (!requireToken()) return;
    setBusy(`${toolId}:${action}`);
    setError(null);
    try {
      const payload = await readJson<OperationResult>(`/api/local-tools/${toolId}/${action}`, {
        method: "POST",
        headers: { "X-Control-Token": token ?? "" },
      });
      setResult(payload);
      await load();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(null);
    }
  }, [load, requireToken, token]);

  const scan = React.useCallback(async () => {
    if (!requireToken()) return;
    setBusy("scan");
    setError(null);
    try {
      const suffix = scanRoot.trim() ? `?root=${encodeURIComponent(scanRoot.trim())}` : "";
      const data = await readJson<{ candidates: LocalToolCandidate[] }>(`/api/local-tools/scan${suffix}`, {
        headers: { "X-Control-Token": token ?? "" },
      });
      setCandidates(data.candidates);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(null);
    }
  }, [requireToken, scanRoot, token]);

  const registerDraft = React.useCallback(async () => {
    if (!draft || !requireToken()) return;
    if (!draft.dir.trim()) {
      setError("注册文档里没有工具目录，请补充 dir 后再注册。");
      return;
    }
    setBusy("register");
    setError(null);
    try {
      const data = await readJson<{ ok: boolean; settings_path: string; registered: RegisterDraft }>("/api/local-tools/register", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Control-Token": token ?? "" },
        body: JSON.stringify({ ...draft, dir: draft.dir.trim(), tags: draft.tags.filter(Boolean) }),
      });
      setResult({ ok: data.ok, component: "local-tools", action: "register", message: `已注册 ${data.registered.name}，配置写入 ${data.settings_path}` });
      setDraft(null);
      await load();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(null);
    }
  }, [draft, load, requireToken, token]);

  const chooseManifest = React.useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    try {
      const text = await file.text();
      const manifest = JSON.parse(text) as Record<string, unknown>;
      const nextDraft = draftFromManifest(manifest, file.name);
      const nativePath = (file as unknown as { path?: string }).path;
      if (!nextDraft.dir && nativePath) {
        const normalized = nativePath.replaceAll("\\", "/");
        nextDraft.dir = normalized.split("/").slice(0, -1).join("/") || "";
        nextDraft.manifest = normalized.split("/").pop() || file.name;
      }
      setDraft(nextDraft);
    } catch (exc) {
      setError(exc instanceof Error ? `注册文档解析失败：${exc.message}` : String(exc));
    }
  }, []);

  const selected = tools.find((tool) => tool.id === selectedId) ?? tools[0] ?? null;

  const loadLogs = React.useCallback(async (toolId: string) => {
    setLogsBusy(true);
    setError(null);
    try {
      const data = await readJson<{ logs: LogTail[] }>(`/api/logs/${encodeURIComponent(`local-tool:${toolId}`)}?lines=80`);
      setLogs(data.logs);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLogsBusy(false);
    }
  }, []);

  React.useEffect(() => {
    setLogs([]);
    if (selected?.id) {
      loadLogs(selected.id).catch((exc) => setError(exc instanceof Error ? exc.message : String(exc)));
    }
  }, [loadLogs, selected?.id]);

  return (
    <section className="flex flex-col gap-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-950">外部应用</h2>
            <p className="mt-1 text-sm text-slate-600">管理独立程序的注册、进程启动与页面嵌入（原“本地工具”）。ACC 功能插件的启用与停用请前往侧边栏“设置”，这里不重复注册功能插件。</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input ref={fileInputRef} className="hidden" type="file" accept=".json,application/json" onChange={chooseManifest} />
            <ActionButton icon={<FilePlus2 size={16} />} label="选择注册文档" disabled={Boolean(busy)} onClick={() => fileInputRef.current?.click()} />
            <ActionButton icon={<Search size={16} />} label="扫描" disabled={busy === "scan"} onClick={scan} />
            <ActionButton icon={<RefreshCcw size={16} />} label="刷新" disabled={Boolean(busy)} onClick={load} />
          </div>
        </div>
        <div className="mt-3 flex flex-col gap-2 lg:flex-row">
          <input
            className="min-h-10 flex-1 rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-teal-500"
            placeholder="可选：输入要扫描的工具根目录，例如 F:\\1AI\\Agent control center\\TOOLS"
            value={scanRoot}
            onChange={(event) => setScanRoot(event.target.value)}
          />
        </div>
        {error ? <div className="mt-3 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</div> : null}
        {result ? <div className={`mt-3 rounded-md border p-3 text-sm ${result.ok ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900"}`}>{result.message}</div> : null}
      </div>

      {draft ? (
        <div className="rounded-lg border border-teal-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">注册预览</h3>
              <p className="mt-1 text-xs text-slate-500">确认注册文档内容，缺少目录时补充工具所在文件夹。</p>
            </div>
            <ActionButton disabled={busy === "register"} icon={<CheckCircle2 size={16} />} label="注册到 ACC" onClick={registerDraft} />
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            <DraftInput label="ID" value={draft.id} onChange={(value) => setDraft({ ...draft, id: value })} />
            <DraftInput label="名称" value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
            <DraftInput label="目录" value={draft.dir} onChange={(value) => setDraft({ ...draft, dir: value })} />
            <DraftInput label="入口" value={draft.entry} onChange={(value) => setDraft({ ...draft, entry: value })} />
            <DraftInput label="运行时" value={draft.runtime} onChange={(value) => setDraft({ ...draft, runtime: value })} />
            <DraftInput label="端口" value={String(draft.port || "")} onChange={(value) => setDraft({ ...draft, port: Number(value || 0) })} />
            <DraftInput label="URL" value={draft.url} onChange={(value) => setDraft({ ...draft, url: value })} />
            <DraftInput label="健康检查" value={draft.healthPath} onChange={(value) => setDraft({ ...draft, healthPath: value })} />
            <DraftInput label="打开路径" value={draft.openPath} onChange={(value) => setDraft({ ...draft, openPath: value })} />
          </div>
        </div>
      ) : null}

      {candidates.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {candidates.map((candidate) => (
            <button
              key={`${candidate.id}:${candidate.dir}`}
              className="rounded-md border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-teal-300"
              onClick={() => setDraft(draftFromCandidate(candidate))}
              type="button"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-950">{candidate.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{candidate.dir}</div>
                </div>
                <StatusPill active={candidate.registered} label={candidate.registered ? "已注册" : "可注册"} />
              </div>
              <div className="mt-3 text-xs text-slate-500">{candidate.manifest_path || "未发现注册文档，将按默认入口推断"}</div>
            </button>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <div className="grid gap-3">
          {tools.length ? tools.map((tool) => {
            const active = selected?.id === tool.id;
            return (
              <button
                key={tool.id}
                className={`rounded-md border bg-white p-4 text-left shadow-sm transition ${active ? "border-teal-500 ring-2 ring-teal-100" : "border-slate-200 hover:border-slate-300"}`}
                onClick={() => setSelectedId(tool.id)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-950">{tool.name}</div>
                    <div className="mt-1 text-xs text-slate-500">{tool.description || tool.id}</div>
                  </div>
                  <StatusPill active={running(tool)} label={running(tool) ? "运行中" : "已停止"} />
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {tool.tags.map((tag) => <span key={tag} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">{tag}</span>)}
                </div>
                <div className="mt-3 text-xs text-slate-500">Port {tool.port || "-"} · PID {tool.pid || "-"}</div>
              </button>
            );
          }) : <div className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500">暂无已注册工具。</div>}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {selected ? (
            <div className="flex h-full min-h-[620px] flex-col gap-3">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-950">{selected.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">{selected.url}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <ActionButton disabled={Boolean(busy) || running(selected)} icon={<Play size={16} />} label="启动" onClick={() => run(selected.id, "start")} />
                  <ActionButton disabled={Boolean(busy) || !running(selected)} icon={<Square size={16} />} label="停止" onClick={() => run(selected.id, "stop")} />
                  <ActionButton disabled={Boolean(busy)} icon={<RefreshCcw size={16} />} label="重启" onClick={() => run(selected.id, "restart")} />
                  <ActionButton disabled={logsBusy} icon={<ScrollText size={16} />} label="日志" onClick={() => loadLogs(selected.id)} />
                  <a className="inline-flex items-center gap-1 rounded border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50" href={selected.open_url || selected.url} target="_blank" rel="noreferrer">
                    <ExternalLink size={16} /> 新窗口
                  </a>
                </div>
              </div>
              <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 lg:grid-cols-2">
                <Meta label="运行时" value={selected.runtime} />
                <Meta label="来源" value={selected.source} />
                <Meta label="目录" value={selected.dir} />
                <Meta label="入口" value={selected.entry} />
                <Meta label="命令" value={selected.command.join(" ")} />
                <Meta label="健康检查" value={selected.health_url} />
                {selected.manifest_path ? <Meta label="Manifest" value={selected.manifest_path} /> : null}
                <Meta label="日志" value={`${selected.stdout_log} | ${selected.stderr_log}`} />
              </div>
              {selected.embed ? (
                <iframe title={selected.name} src={iframeUrl(selected)} className="min-h-[420px] flex-1 rounded-md border border-slate-200" />
              ) : (
                <div className="flex min-h-[420px] items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-sm text-slate-500">该工具未启用内嵌显示。</div>
              )}
              <div className="rounded-md border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100">
                <div className="mb-2 flex items-center gap-2 text-slate-300">
                  <FileCode2 size={14} />
                  <span>最近日志</span>
                </div>
                <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words font-mono leading-relaxed">
                  {logs.length ? logs.map((log) => [
                    `# ${log.path}${log.exists === false ? " (missing)" : ""}`,
                    ...(log.lines.length ? log.lines : [""]),
                  ].join("\n")).join("\n\n") : "暂无日志。"}
                </pre>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[620px] items-center justify-center text-sm text-slate-500">选择一个工具查看详情。</div>
          )}
        </div>
      </div>
    </section>
  );
}

function DraftInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-xs text-slate-500">
      <span>{label}</span>
      <input className="min-h-9 rounded-md border border-slate-200 px-2 text-sm text-slate-800 outline-none focus:border-teal-500" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="truncate font-mono text-[11px] text-slate-800" title={value}>{value || "-"}</div>
    </div>
  );
}
