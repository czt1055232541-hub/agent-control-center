import React from "react";
import { Download, FileUp, Plus, RefreshCcw, Save, Trash2, X } from "lucide-react";
import { readJson } from "../../api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

type ConfigEntry = {
  key: string;
  value: string;
  description: string;
};

type ConfigForm = {
  key: string;
  value: string;
  description: string;
};

const EMPTY_FORM: ConfigForm = { key: "", value: "", description: "" };

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
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function ConfigCenterPage({ token }: { token: string }) {
  const [configs, setConfigs] = React.useState<ConfigEntry[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);
  const [editingKey, setEditingKey] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<ConfigForm>(EMPTY_FORM);
  const [searchTerm, setSearchTerm] = React.useState("");

  /* ---- data loading ---- */

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await readJson<{ configs: ConfigEntry[] }>("/api/config-center/list");
      setConfigs(data.configs ?? []);
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
    if (!searchTerm.trim()) return configs;
    const q = searchTerm.trim().toLowerCase();
    return configs.filter(
      (c) =>
        c.key.toLowerCase().includes(q) ||
        c.value.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q),
    );
  }, [configs, searchTerm]);

  /* ---- CRUD helpers ---- */

  const openAdd = () => {
    setEditingKey(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  };

  const openEdit = (entry: ConfigEntry) => {
    setEditingKey(entry.key);
    setForm({ key: entry.key, value: entry.value, description: entry.description });
    setShowForm(true);
  };

  const closeForm = () => {
    setEditingKey(null);
    setShowForm(false);
    setForm(EMPTY_FORM);
  };

  const saveConfig = async () => {
    if (!form.key.trim()) return;
    setBusy(true);
    setError("");
    try {
      await readJson("/api/config-center/set", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: form.key.trim(),
          value: form.value,
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

  const deleteConfig = async (key: string) => {
    if (!window.confirm(`确定删除配置 "${key}"？`)) return;
    setBusy(true);
    setError("");
    try {
      await readJson(`/api/config-center/delete/${encodeURIComponent(key)}`, {
        method: "DELETE",
      });
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const exportConfigs = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await readJson<{ configs: Record<string, { value: string; description: string }> }>(
        "/api/config-center/export",
        { method: "POST" },
      );
      const blob = new Blob([JSON.stringify(data.configs, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `config-center-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const importConfigs = async () => {
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
        await readJson("/api/config-center/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ configs: parsed }),
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

  /* ---- render ---- */

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4">
      {/* Header */}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-950">配置中心</h2>
            <p className="mt-1 text-sm text-slate-600">
              内存配置存储，支持基本 CRUD 和 JSON 导入/导出。
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <IconButton title="刷新配置列表" onClick={refresh} disabled={loading || busy}>
              <RefreshCcw size={15} />
            </IconButton>
            <button
              type="button"
              onClick={exportConfigs}
              disabled={busy || configs.length === 0}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download size={14} />
              导出 JSON
            </button>
            <button
              type="button"
              onClick={importConfigs}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FileUp size={14} />
              导入 JSON
            </button>
            <button
              type="button"
              onClick={openAdd}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus size={15} />
              新增配置
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-xl font-semibold text-slate-950">{configs.length}</div>
            <div className="text-xs text-slate-500">配置项总数</div>
          </div>
        </div>

        {/* Search */}
        <div className="mt-3">
          <input
            className="w-full rounded-md border border-slate-200 bg-slate-50 py-2 pl-3 pr-3 text-sm outline-none focus:border-teal-500"
            placeholder="搜索 key / value / description..."
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
              {editingKey ? `编辑配置: ${editingKey}` : "新增配置"}
            </h3>
            <IconButton title="关闭表单" onClick={closeForm} disabled={busy}>
              <X size={15} />
            </IconButton>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Key
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500 disabled:bg-slate-100"
                value={form.key}
                disabled={editingKey !== null}
                onChange={(e) => setForm({ ...form, key: e.target.value })}
              />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Value
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
              />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600 md:col-span-2">
              Description
              <input
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
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
              onClick={saveConfig}
              disabled={busy || !form.key.trim()}
              className="inline-flex items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save size={15} />
              保存
            </button>
          </div>
        </section>
      ) : null}

      {/* Config table */}
      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
                <th className="px-4 py-3">Key</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td className="px-4 py-10 text-center text-slate-400" colSpan={4}>
                    正在加载...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td className="px-4 py-10 text-center text-slate-400" colSpan={4}>
                    {searchTerm ? "没有匹配的配置项" : "暂无配置项，点击「新增配置」添加"}
                  </td>
                </tr>
              ) : (
                filtered.map((entry) => (
                  <tr key={entry.key} className="hover:bg-slate-50">
                    <td className="max-w-[200px] break-all px-4 py-3 font-mono text-xs font-medium text-slate-900">
                      {entry.key}
                    </td>
                    <td className="max-w-[300px] break-all px-4 py-3 text-slate-700">{entry.value}</td>
                    <td className="max-w-[250px] break-all px-4 py-3 text-slate-500">
                      {entry.description || "--"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <IconButton title="编辑" onClick={() => openEdit(entry)} disabled={busy}>
                          <Save size={14} />
                        </IconButton>
                        <IconButton
                          title="删除"
                          onClick={() => deleteConfig(entry.key)}
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
