import React from "react";
import { AlertTriangle, CheckCircle2, RefreshCcw, Shield, Users, XCircle } from "lucide-react";
import { readJson } from "../../api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

type ConnectionStatus = {
  authenticated: boolean;
  tenantName: string;
  appName: string;
  appIdMasked: string;
  authDetail: string;
  authError: string;
  durationMs: number;
};

type AccountInfo = {
  name: string;
  openIdMasked: string;
  role: string;
  bindingStatus: string;
  feishuBinding: string;
};

type GroupInfo = {
  chatIdMasked: string;
  groupName: string;
};

type AccountsResponse = {
  accounts: AccountInfo[];
  groups: GroupInfo[];
  total: number;
};

type ScopeItem = {
  scope: string;
  granted: boolean;
};

type PermissionsResponse = {
  authenticated: boolean;
  scopes: ScopeItem[];
  missingScopes: string[];
  authDetail: string;
  authError: string;
  suggestion: string;
  durationMs: number;
};

type RefreshResponse = {
  ok: boolean;
  message: string;
  stdout: string;
  stderr: string;
  durationMs: number;
};

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
        ok
          ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
          : "bg-red-50 text-red-700 ring-1 ring-red-200"
      }`}
    >
      {ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FeishuConnectionPage({ token }: { token: string }) {
  const [status, setStatus] = React.useState<ConnectionStatus | null>(null);
  const [accounts, setAccounts] = React.useState<AccountsResponse | null>(null);
  const [permissions, setPermissions] = React.useState<PermissionsResponse | null>(null);
  const [refreshResult, setRefreshResult] = React.useState<RefreshResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [refreshing, setRefreshing] = React.useState(false);

  /* ---- data loading ---- */

  const refreshAll = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [s, a, p] = await Promise.all([
        readJson<ConnectionStatus>("/api/feishu/connection/status"),
        readJson<AccountsResponse>("/api/feishu/connection/accounts"),
        readJson<PermissionsResponse>("/api/feishu/connection/permissions"),
      ]);
      setStatus(s);
      setAccounts(a);
      setPermissions(p);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refreshAll().catch(() => {});
  }, [refreshAll]);

  /* ---- refresh auth ---- */

  const doRefresh = async () => {
    if (!window.confirm("确定手动触发飞书认证刷新？这将在本地执行 `lark-cli auth login --force`。")) return;
    setRefreshing(true);
    setError("");
    setRefreshResult(null);
    try {
      const result = await readJson<RefreshResponse>("/api/feishu/connection/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      setRefreshResult(result);
      // Re-fetch all data after refresh
      await refreshAll();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setRefreshing(false);
    }
  };

  /* ---- render ---- */

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-slate-500">
        <RefreshCcw size={18} className="mr-2 animate-spin" />
        加载中...
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4">

      {/* Error banner */}
      {error ? (
        <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {/* Refresh result */}
      {refreshResult ? (
        <div
          className={`rounded-md border p-3 text-sm ${
            refreshResult.ok
              ? "border-emerald-300 bg-emerald-50 text-emerald-900"
              : "border-red-300 bg-red-50 text-red-900"
          }`}
        >
          <strong>{refreshResult.message}</strong>
          {refreshResult.stdout ? <pre className="mt-1 whitespace-pre-wrap font-mono text-xs">{refreshResult.stdout}</pre> : null}
          {refreshResult.stderr ? <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-red-600">{refreshResult.stderr}</pre> : null}
          <span className="mt-1 block text-xs opacity-70">{refreshResult.durationMs} ms</span>
        </div>
      ) : null}

      {/* Section 1: Connection Overview Card */}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-950">
              <Shield size={20} className="text-teal-600" />
              连接总览
            </h2>
            <p className="mt-1 text-sm text-slate-600">飞书 Lark 认证与应用信息概览</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {status ? <StatusBadge ok={status.authenticated} label={status.authenticated ? "已认证" : "未认证"} /> : null}
            <button
              type="button"
              onClick={doRefresh}
              disabled={busy || refreshing}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCcw size={15} className={refreshing ? "animate-spin" : ""} />
              刷新认证
            </button>
          </div>
        </div>

        {status ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-500">租户名</div>
              <div className="mt-1 text-sm font-medium text-slate-900">{status.tenantName}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-500">应用名</div>
              <div className="mt-1 text-sm font-medium text-slate-900">{status.appName}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-500">App ID</div>
              <div className="mt-1 text-sm font-mono font-medium text-slate-900">{status.appIdMasked}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-500">响应时长</div>
              <div className="mt-1 text-sm font-medium text-slate-900">{status.durationMs} ms</div>
            </div>
          </div>
        ) : (
          <div className="mt-4 text-sm text-slate-400">无法获取连接状态</div>
        )}

        {status?.authDetail ? (
          <details className="mt-3">
            <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700">查看原始输出</summary>
            <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-100">
              {status.authDetail}
            </pre>
          </details>
        ) : null}
      </section>

      {/* Section 2: Agent Binding List */}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-950">
              <Users size={20} className="text-teal-600" />
              Agent 绑定列表
            </h2>
            <p className="mt-1 text-sm text-slate-600">各 Agent 的飞书绑定与认证状态</p>
          </div>
          {accounts ? (
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">
              共 {accounts.total} 个
            </span>
          ) : null}
        </div>

        {accounts && accounts.accounts.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
                  <th className="px-4 py-3">名称</th>
                  <th className="px-4 py-3">角色</th>
                  <th className="px-4 py-3">Open ID</th>
                  <th className="px-4 py-3">绑定状态</th>
                  <th className="px-4 py-3">飞书绑定</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {accounts.accounts.map((acct) => (
                  <tr key={acct.name} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{acct.name}</td>
                    <td className="px-4 py-3 text-slate-600">{acct.role || "--"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{acct.openIdMasked || "--"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${
                          acct.bindingStatus === "bound"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {acct.bindingStatus === "bound" ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                        {acct.bindingStatus === "bound" ? "已绑定" : "未绑定"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{acct.feishuBinding === "enabled" ? "已启用" : "已禁用"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-4 text-sm text-slate-400">暂无 Agent 绑定数据</div>
        )}

        {/* Group info */}
        {accounts && accounts.groups.length > 0 ? (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <h3 className="mb-2 text-sm font-medium text-slate-700">群聊信息</h3>
            <div className="flex flex-wrap gap-2">
              {accounts.groups.map((g) => (
                <div
                  key={g.chatIdMasked}
                  className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                >
                  <Users size={14} className="text-slate-400" />
                  <span>{g.groupName}</span>
                  <span className="font-mono text-xs text-slate-400">{g.chatIdMasked}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {/* Section 3: Permission Diagnosis */}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-950">
              <Shield size={20} className="text-teal-600" />
              权限诊断
            </h2>
            <p className="mt-1 text-sm text-slate-600">飞书权限 scope 检查与缺失提示</p>
          </div>
          {permissions ? <StatusBadge ok={permissions.authenticated} label={permissions.authenticated ? "已认证" : "未认证"} /> : null}
        </div>

        {permissions ? (
          <>
            {permissions.missingScopes.length > 0 ? (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <strong className="flex items-center gap-1">
                  <AlertTriangle size={14} />
                  缺失 {permissions.missingScopes.length} 个权限
                </strong>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {permissions.missingScopes.map((scope) => (
                    <li key={scope} className="font-mono text-xs">
                      {scope}
                    </li>
                  ))}
                </ul>
                {permissions.suggestion ? (
                  <p className="mt-2 text-xs text-amber-700">{permissions.suggestion}</p>
                ) : null}
              </div>
            ) : (
              <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                <strong className="flex items-center gap-1">
                  <CheckCircle2 size={14} />
                  所有必需权限已授予
                </strong>
              </div>
            )}

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
                    <th className="px-4 py-3">Scope</th>
                    <th className="px-4 py-3">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {permissions.scopes.map((scope) => (
                    <tr key={scope.scope} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs text-slate-700">{scope.scope}</td>
                      <td className="px-4 py-3">
                        <StatusBadge ok={scope.granted} label={scope.granted ? "已授权" : "缺失"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="mt-4 text-sm text-slate-400">无法获取权限信息</div>
        )}

        {permissions?.suggestion ? (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
            <Shield size={16} className="mt-0.5 shrink-0" />
            <span>{permissions.suggestion}</span>
          </div>
        ) : null}
      </section>

    </div>
  );
}
