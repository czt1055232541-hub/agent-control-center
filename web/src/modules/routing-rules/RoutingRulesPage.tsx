import React from "react";
import { Download, FileUp, Plus, RefreshCcw, Save, Trash2, ToggleLeft, ToggleRight, X } from "lucide-react";
import { readJson } from "../../api";
import { SortableGrid, type SortableGridItem } from "../../components/common/SortableGrid";

/* ------------------------------------------------------------------ */
/* Types                                                             */
/* ------------------------------------------------------------------ */

type RoutingRule = {
  rule_id: string;
  name: string;
  pattern: string;
  target: string;
  enabled: boolean;
  description: string;
};

type RuleForm = {
  rule_id: string;
  name: string;
  pattern: string;
  target: string;
  enabled: boolean;
  description: string;
};

const EMPTY_FORM: RuleForm = {
  rule_id: "",
  name: "",
  pattern: "",
  target: "",
  enabled: true,
  description: "",
};

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function IconButton({
  title,
  onClick,
  children,
  disabled,
  danger,
}: {
  title: string;
  onClick: () => void;
  children: React.ReactNode;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md border text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
        danger
          ? "border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                         */
/* ------------------------------------------------------------------ */

export default function RoutingRulesPage({ token }: { token: string }) {
  const [rules, setRules] = React.useState<RoutingRule[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<RuleForm>(EMPTY_FORM);
  const [searchTerm, setSearchTerm] = React.useState("");

  /* ---- data loading ---- */

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await readJson<{ rules: RoutingRule[] }>("/api/routing-rules/list");
      setRules(data.rules ?? []);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  /* ---- filtered list ---- */

  const filtered = React.useMemo(() => {
    if (!searchTerm.trim()) return rules;
    const q = searchTerm.trim().toLowerCase();
    return rules.filter(
      (r) =>
        r.rule_id.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q) ||
        r.pattern.toLowerCase().includes(q) ||
        r.target.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q),
    );
  }, [rules, searchTerm]);

  /* ---- CRUD helpers ---- */

  const openAdd = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  };

  const openEdit = (rule: RoutingRule) => {
    setEditingId(rule.rule_id);
    setForm({
      rule_id: rule.rule_id,
      name: rule.name,
      pattern: rule.pattern,
      target: rule.target,
      enabled: rule.enabled,
      description: rule.description,
    });
    setShowForm(true);
  };

  const closeForm = () => {
    setEditingId(null);
    setShowForm(false);
    setForm(EMPTY_FORM);
  };

  const saveRule = async () => {
    if (!form.name.trim()) return;
    setBusy(true);
    setError("");
    try {
      await readJson("/api/routing-rules/set", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Control-Token": token },
        body: JSON.stringify({
          rule_id: editingId ?? form.rule_id ?? "auto",
          name: form.name.trim(),
          pattern: form.pattern.trim(),
          target: form.target.trim(),
          enabled: form.enabled,
          description: form.description,
        }),
      });
      closeForm();
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const deleteRule = async (ruleId: string) => {
    if (!window.confirm(`确定删除规则 "${ruleId}"？`)) return;
    setBusy(true);
    setError("");
    try {
      await readJson(`/api/routing-rules/delete/${encodeURIComponent(ruleId)}`, {
        method: "DELETE",
        headers: { "X-Control-Token": token },
      });
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const toggleEnabled = async (rule: RoutingRule) => {
    setBusy(true);
    setError("");
    try {
      await readJson("/api/routing-rules/set", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Control-Token": token },
        body: JSON.stringify({
          rule_id: rule.rule_id,
          name: rule.name,
          pattern: rule.pattern,
          target: rule.target,
          enabled: !rule.enabled,
          description: rule.description,
        }),
      });
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const exportRules = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await readJson<{ rules: RoutingRule[] }>("/api/routing-rules/list");
      const blob = new Blob([JSON.stringify(data.rules, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `routing-rules-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const importRules = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      setBusy(true);
      setError("");
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        const rulesArray = Array.isArray(parsed) ? parsed : parsed.rules ?? [];
        await readJson("/api/routing-rules/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Control-Token": token },
          body: JSON.stringify({ rules: rulesArray }),
        });
        await refresh();
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : String(exc));
      } finally {
        setBusy(false);
      }
    };
    input.click();
  };
  const statsItems = React.useMemo<SortableGridItem[]>(() => [
    {
      id: "total",
      node: (
        <div className="h-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="text-xl font-semibold text-slate-950">{rules.length}</div>
          <div className="text-xs text-slate-500">规则总数</div>
        </div>
      ),
    },
    {
      id: "enabled",
      node: (
        <div className="h-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="text-xl font-semibold text-slate-950">{rules.filter((r) => r.enabled).length}</div>
          <div className="text-xs text-slate-500">已启用</div>
        </div>
      ),
    },
    {
      id: "disabled",
      node: (
        <div className="h-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="text-xl font-semibold text-slate-950">{rules.filter((r) => !r.enabled).length}</div>
          <div className="text-xs text-slate-500">已禁用</div>
        </div>
      ),
    },
  ], [rules]);

  /* ---- render ---- */

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4">
      {/* Header */}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-950">路由规则</h2>
            <p className="mt-1 text-sm text-slate-600">
              内存路由规则存储，支持基本 CRUD、启用/禁用开关和 JSON 批量导入/导出。
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <IconButton title="刷新规则列表" onClick={refresh} disabled={loading || busy}>
              <RefreshCcw size={15} />
            </IconButton>
            <button
              type="button"
              onClick={exportRules}
              disabled={busy || rules.length === 0}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download size={14} />
              导出 JSON
            </button>
            <button
              type="button"
              onClick={importRules}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FileUp size={14} />
              批量导入
            </button>
            <button
              type="button"
              onClick={openAdd}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus size={15} />
              新增规则
            </button>
          </div>
        </div>

        {/* Stats */}
        <SortableGrid
          ariaLabel="Routing stats cards"
          className="mt-4 grid gap-2 sm:grid-cols-3"
          items={statsItems}
          maxColSpan={3}
          storageKey="acc.routing.statsLayout"
        />

        {/* Search */}
        <div className="mt-3">
          <input
            className="w-full rounded-md border border-slate-200 bg-slate-50 py-2 pl-3 pr-3 text-sm outline-none focus:border-teal-500"
            placeholder="搜索 rule_id / name / pattern / target / description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
            {error}
          </div>
        ) : null}
      </section>

      {/* Add / Edit form */}
      {showForm ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-950">
              {editingId ? `编辑规则: ${editingId}` : "新增规则"}
            </h3>
            <IconButton title="关闭表单" onClick={closeForm} disabled={busy}>
              <X size={15} />
            </IconButton>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Name
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="规则名称"
              />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Pattern
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.pattern}
                onChange={(e) => setForm({ ...form, pattern: e.target.value })}
                placeholder='如 @项目调度官'
              />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Target
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.target}
                onChange={(e) => setForm({ ...form, target: e.target.value })}
                placeholder="目标模块/agent"
              />
            </label>
            <label className="flex items-center gap-2 self-end pb-2 text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-teal-600"
                checked={form.enabled}
                onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
              />
              启用
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600 md:col-span-2">
              Description
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="可选描述"
              />
            </label>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={closeForm}
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="button"
              onClick={saveRule}
              disabled={busy || !form.name.trim()}
              className="inline-flex items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save size={15} />
              保存
            </button>
          </div>
        </section>
      ) : null}

      {/* Rules table */}
      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
                <th className="px-4 py-3">Rule ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Pattern</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td className="px-4 py-10 text-center text-slate-400" colSpan={7}>
                    正在加载...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td className="px-4 py-10 text-center text-slate-400" colSpan={7}>
                    {searchTerm ? "没有匹配的规则" : "暂无规则，点击「新增规则」添加"}
                  </td>
                </tr>
              ) : (
                filtered.map((rule) => (
                  <tr key={rule.rule_id} className="hover:bg-slate-50">
                    <td className="max-w-[140px] break-all px-4 py-3 font-mono text-xs font-medium text-slate-900">
                      {rule.rule_id}
                    </td>
                    <td className="max-w-[160px] break-all px-4 py-3 text-slate-900">
                      {rule.name}
                    </td>
                    <td className="max-w-[180px] break-all px-4 py-3 font-mono text-xs text-slate-700">
                      {rule.pattern}
                    </td>
                    <td className="max-w-[140px] break-all px-4 py-3 text-slate-700">
                      {rule.target}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        title={rule.enabled ? "点击禁用" : "点击启用"}
                        disabled={busy}
                        onClick={() => toggleEnabled(rule)}
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition ${
                          rule.enabled
                            ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                            : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                        }`}
                      >
                        {rule.enabled ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                        {rule.enabled ? "启用" : "禁用"}
                      </button>
                    </td>
                    <td className="max-w-[200px] break-all px-4 py-3 text-slate-500">
                      {rule.description || "--"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <IconButton title="编辑" onClick={() => openEdit(rule)} disabled={busy}>
                          <Save size={14} />
                        </IconButton>
                        <IconButton
                          title="删除"
                          onClick={() => deleteRule(rule.rule_id)}
                          disabled={busy}
                          danger
                        >
                          <Trash2 size={14} />
                        </IconButton>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
