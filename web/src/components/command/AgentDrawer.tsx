import React from "react";
import { RotateCcw, Save, Shield, X } from "lucide-react";
import { readJson } from "../../api";
import type { AgentConfig, EditableA2APeer, EditableAgentConfig } from "../../types";
import { statusClasses, statusLabel } from "./statusStyles";

const tabs = ["基础配置", "飞书绑定", "运行状态", "团队关系", "可编辑配置", "后端功能"] as const;

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-medium text-slate-900">{value || "--"}</div>
    </div>
  );
}

function TextInput({
  label,
  value,
  onChange,
  placeholder,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {multiline ? (
        <textarea
          className="mt-1 min-h-20 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          value={value}
        />
      ) : (
        <input
          className="mt-1 h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          value={value}
        />
      )}
    </label>
  );
}

function stringifyValue(value: unknown) {
  return JSON.stringify(value ?? "");
}

function buildPayload(config: EditableAgentConfig | null, draft: EditableAgentConfig["values"]) {
  if (!config) return {};
  if (config.source === "codex-agent") {
    return {
      AGENT_PROVIDER: draft.AGENT_PROVIDER,
      CODEX_AGENT_ARGS: draft.CODEX_AGENT_ARGS,
      CODEX_CLI_TIMEOUT_MS: draft.CODEX_CLI_TIMEOUT_MS,
      CODEX_PROGRESS_INITIAL_MS: draft.CODEX_PROGRESS_INITIAL_MS,
      CODEX_PROGRESS_INTERVAL_MS: draft.CODEX_PROGRESS_INTERVAL_MS,
      A2A_BOTS: draft.A2A_BOTS ?? [],
    };
  }
  return {
    identityTheme: draft.identityTheme,
    ...(typeof draft.feishuAccountEnabled === "boolean" ? { feishuAccountEnabled: draft.feishuAccountEnabled } : {}),
  };
}

function changedFields(config: EditableAgentConfig | null, draft: EditableAgentConfig["values"]) {
  if (!config) return [];
  const payload = buildPayload(config, draft);
  return Object.entries(payload)
    .filter(([key, value]) => stringifyValue(value) !== stringifyValue(config.values[key as keyof typeof config.values]))
    .map(([key]) => key);
}

export function AgentDrawer({
  agent,
  token,
  onClose,
  onSaved,
}: {
  agent: AgentConfig | null;
  token: string;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [activeTab, setActiveTab] = React.useState<(typeof tabs)[number]>("基础配置");
  const [editable, setEditable] = React.useState<EditableAgentConfig | null>(null);
  const [draft, setDraft] = React.useState<EditableAgentConfig["values"]>({});
  const [loadingConfig, setLoadingConfig] = React.useState(false);
  const [configError, setConfigError] = React.useState("");
  const [configResult, setConfigResult] = React.useState("");

  const loadEditable = React.useCallback(async () => {
    if (!agent || agent.source === "infrastructure") {
      setEditable(null);
      setDraft({});
      return;
    }
    setLoadingConfig(true);
    setConfigError("");
    try {
      const next = await readJson<EditableAgentConfig>(`/api/agents/${agent.id}/editable-config`);
      setEditable(next);
      setDraft(next.values);
    } catch (exc) {
      setEditable(null);
      setDraft({});
      setConfigError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoadingConfig(false);
    }
  }, [agent]);

  React.useEffect(() => {
    setActiveTab("基础配置");
    setConfigResult("");
    loadEditable().catch(() => {});
  }, [agent?.id, loadEditable]);

  if (!agent) return null;

  const updateDraft = <K extends keyof EditableAgentConfig["values"]>(key: K, value: EditableAgentConfig["values"][K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const changes = changedFields(editable, draft);

  async function saveConfig() {
    if (!editable || !token) {
      setConfigError(token ? "当前 Agent 没有可编辑配置。" : "Control token is not ready.");
      return;
    }
    if (!changes.length) {
      setConfigResult("没有检测到配置变更。");
      return;
    }
    if (!window.confirm(`确认保存 ${changes.join(", ")}？保存前会自动备份当前配置。`)) return;
    setLoadingConfig(true);
    setConfigError("");
    try {
      const result = await readJson<{ ok: boolean; config: EditableAgentConfig }>(`/api/agents/${agent.id}/editable-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Control-Token": token },
        body: JSON.stringify({ values: buildPayload(editable, draft) }),
      });
      setEditable(result.config);
      setDraft(result.config.values);
      setConfigResult("配置已保存，并已生成自动备份。");
      await onSaved();
    } catch (exc) {
      setConfigError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoadingConfig(false);
    }
  }

  async function backupConfig() {
    if (!token) {
      setConfigError("Control token is not ready.");
      return;
    }
    if (!window.confirm("确认立即创建一次配置备份？")) return;
    setLoadingConfig(true);
    setConfigError("");
    try {
      await readJson<{ ok: boolean; backupPath: string }>(`/api/agents/${agent.id}/config-backup`, {
        method: "POST",
        headers: { "X-Control-Token": token },
      });
      await loadEditable();
      setConfigResult("备份已创建。");
    } catch (exc) {
      setConfigError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoadingConfig(false);
    }
  }

  async function rollbackConfig() {
    if (!token) {
      setConfigError("Control token is not ready.");
      return;
    }
    if (!window.confirm("确认回滚到最近一次备份？这会覆盖当前配置。")) return;
    setLoadingConfig(true);
    setConfigError("");
    try {
      await readJson<{ ok: boolean }>(`/api/agents/${agent.id}/config-rollback-latest`, {
        method: "POST",
        headers: { "X-Control-Token": token },
      });
      await loadEditable();
      await onSaved();
      setConfigResult("已回滚到最近一次备份。");
    } catch (exc) {
      setConfigError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoadingConfig(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/30">
      <aside className="h-full w-full max-w-2xl overflow-auto bg-white shadow-xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">{agent.name}</h2>
              <p className="mt-1 text-sm text-slate-600">{agent.role}</p>
            </div>
            <button className="rounded-md p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button">
              <X size={18} />
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className={`rounded-md border px-2 py-1 text-xs font-medium ${statusClasses(agent.status)}`}>{statusLabel(agent.status)}</span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">{agent.provider}</span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">{agent.model}</span>
          </div>
          <div className="mt-4 flex gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab}
                className={`h-9 shrink-0 rounded-md px-3 text-sm font-medium ${activeTab === tab ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
                onClick={() => setActiveTab(tab)}
                type="button"
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4">
          {activeTab === "基础配置" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Agent 名称" value={agent.name} />
              <Field label="Agent ID" value={agent.agentId ?? agent.id} />
              <Field label="来源" value={agent.source} />
              <Field label="角色职责" value={agent.role} />
              <Field label="模型 Provider" value={agent.provider} />
              <Field label="模型名称" value={agent.model} />
              <Field label="承载组件" value={agent.backingComponent} />
              <Field label="Workspace" value={agent.workspacePath} />
              <Field label="配置文件" value={agent.configPath} />
              <Field label="权限等级" value={agent.permissionLevel} />
            </div>
          ) : null}

          {activeTab === "飞书绑定" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="绑定状态" value={agent.bindingStatus} />
              <Field label="Feishu Account Enabled" value={agent.feishuAccountEnabled === null ? "--" : agent.feishuAccountEnabled ? "是" : "否"} />
              <Field label="触发方式" value={agent.triggerMode} />
              <Field label="hasBinding" value={String((agent.configFacts?.binding as Record<string, unknown> | undefined)?.hasBinding ?? "--")} />
              <Field label="hasAccountId / hasOpenId" value={String((agent.configFacts?.binding as Record<string, unknown> | undefined)?.hasAccountId ?? (agent.configFacts?.hasBotOpenId ?? "--"))} />
              <Field label="connectionMode" value={String((agent.configFacts?.binding as Record<string, unknown> | undefined)?.connectionMode ?? "--")} />
            </div>
          ) : null}

          {activeTab === "运行状态" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="当前状态" value={agent.status} />
              <Field label="Session Count" value={agent.sessionCount ?? "--"} />
              <Field label="Last Interaction" value={agent.lastInteractionAt ?? "--"} />
              <Field label="Last Called" value={agent.lastCalledAt ?? "--"} />
              <Field label="Workspace Exists" value={String(agent.configFacts?.workspaceExists ?? agent.configFacts?.envExists ?? "--")} />
              <Field label="Sessions File Exists" value={String(agent.configFacts?.sessionsPathExists ?? "--")} />
              <Field label="工具" value={agent.tools.join(", ")} />
              <Field label="最近错误" value={agent.lastError || "--"} />
            </div>
          ) : null}

          {activeTab === "团队关系" ? (
            <div className="space-y-2">
              {agent.a2aPeers?.length ? agent.a2aPeers.map((peer) => (
                <div key={peer.name} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">
                  {peer.name} | {peer.description ?? "--"} | openId: {peer.hasOpenId ? "已配置" : "缺失"}
                </div>
              )) : (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">
                  OpenClaw 角色由项目调度官按规范 @ 名称进行单 Agent 交接。
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "可编辑配置" ? (
            <div className="space-y-4">
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <div className="flex items-center gap-2 font-medium"><Shield size={16} /> 仅开放低风险字段</div>
                <p className="mt-1">保存会先备份，再写入配置并重新读取确认；secret、open_id、chat_id、app_id、token 不会返回或编辑。</p>
              </div>

              {loadingConfig ? <div className="text-sm text-slate-600">正在读取配置...</div> : null}
              {configError ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{configError}</div> : null}
              {configResult ? <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{configResult}</div> : null}

              {editable ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="配置文件" value={editable.configPath} />
                    <Field label="最近备份" value={editable.latestBackup ?? "--"} />
                  </div>

                  {editable.source === "codex-agent" ? (
                    <div className="space-y-3">
                      <label className="block">
                        <span className="text-xs font-medium text-slate-600">AGENT_PROVIDER</span>
                        <select
                          className="mt-1 h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                          onChange={(event) => updateDraft("AGENT_PROVIDER", event.target.value)}
                          value={draft.AGENT_PROVIDER ?? "codex"}
                        >
                          {["codex", "local", "openai"].map((provider) => <option key={provider} value={provider}>{provider}</option>)}
                        </select>
                      </label>
                      <TextInput label="CODEX_AGENT_ARGS" multiline onChange={(value) => updateDraft("CODEX_AGENT_ARGS", value)} value={draft.CODEX_AGENT_ARGS ?? ""} />
                      <div className="grid gap-3 sm:grid-cols-3">
                        <TextInput label="CODEX_CLI_TIMEOUT_MS" onChange={(value) => updateDraft("CODEX_CLI_TIMEOUT_MS", value)} value={draft.CODEX_CLI_TIMEOUT_MS ?? ""} />
                        <TextInput label="PROGRESS_INITIAL_MS" onChange={(value) => updateDraft("CODEX_PROGRESS_INITIAL_MS", value)} value={draft.CODEX_PROGRESS_INITIAL_MS ?? ""} />
                        <TextInput label="PROGRESS_INTERVAL_MS" onChange={(value) => updateDraft("CODEX_PROGRESS_INTERVAL_MS", value)} value={draft.CODEX_PROGRESS_INTERVAL_MS ?? ""} />
                      </div>
                      <Field label="LARK_BOT_OPEN_ID" value={editable.values.hasBotOpenId ? "已配置" : "缺失"} />
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-slate-600">A2A_BOTS 描述</div>
                        {(draft.A2A_BOTS ?? []).map((peer: EditableA2APeer, index) => (
                          <div key={peer.name} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                            <div className="mb-2 flex items-center justify-between gap-2 text-sm">
                              <span className="font-medium text-slate-900">{peer.name}</span>
                              <span className="text-xs text-slate-500">openId: {peer.hasOpenId ? "已配置" : "缺失"}</span>
                            </div>
                            <TextInput
                              label="description"
                              onChange={(value) => {
                                const next = [...(draft.A2A_BOTS ?? [])];
                                next[index] = { ...peer, description: value };
                                updateDraft("A2A_BOTS", next);
                              }}
                              value={peer.description ?? ""}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <TextInput label="Agent identity theme" onChange={(value) => updateDraft("identityTheme", value)} value={draft.identityTheme ?? ""} />
                      <label className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
                        <input
                          checked={Boolean(draft.feishuAccountEnabled)}
                          disabled={!draft.hasFeishuAccount}
                          onChange={(event) => updateDraft("feishuAccountEnabled", event.target.checked)}
                          type="checkbox"
                        />
                        Feishu account enabled
                        {!draft.hasFeishuAccount ? <span className="text-xs text-slate-500">未找到可编辑 account</span> : null}
                      </label>
                      <Field label="Workspace 文件入口" value={(draft.workspaceFiles ?? []).join(", ")} />
                    </div>
                  )}

                  <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                    <div className="font-medium text-slate-900">Diff 预览</div>
                    <div className="mt-2 text-slate-600">{changes.length ? changes.join(", ") : "无变更"}</div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50" disabled={loadingConfig} onClick={backupConfig} type="button">
                      <Shield size={16} /> 立即备份
                    </button>
                    <button className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-900 bg-slate-900 px-3 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50" disabled={loadingConfig || !changes.length} onClick={saveConfig} type="button">
                      <Save size={16} /> 保存配置
                    </button>
                    <button className="inline-flex h-9 items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 text-sm font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-50" disabled={loadingConfig || !editable.latestBackup} onClick={rollbackConfig} type="button">
                      <RotateCcw size={16} /> 回滚最近备份
                    </button>
                  </div>
                </>
              ) : (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                  该对象没有开放 UI 可编辑配置。基础设施控制仍通过对应操作按钮完成。
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "后端功能" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {(agent.backendActions ?? []).map((action) => (
                <Field
                  key={`${action.kind}-${action.key}`}
                  label={action.label}
                  value={action.endpoint ?? (action.logComponent ? `logs:${action.logComponent}` : `${action.kind}${action.enabled ? "" : " (disabled)"}`)}
                />
              ))}
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
