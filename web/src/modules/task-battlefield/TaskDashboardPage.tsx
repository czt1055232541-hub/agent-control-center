import React from "react";
import { Edit3, Plus, RefreshCcw, Save, Search, Trash2, X } from "lucide-react";
import { readJson } from "../../api";

type TaskEntry = {
  taskId: string;
  title: string;
  parentProjectId: string;
  parentProjectName: string;
  workspacePath: string;
  status: string;
  phase: string;
  assignee: string;
  updatedAt: string;
  tags: string[];
  source: string;
  hidden: boolean;
};

type TaskGroup = {
  projectId: string;
  projectName: string;
  taskCount: number;
};

type TaskDirectoryResponse = {
  version: number;
  directoryFile: string;
  projectsRoot: string;
  updatedAt: string;
  tasks: TaskEntry[];
  groups: TaskGroup[];
  sync: {
    addedFolders: string[];
    missingWorkspaces: string[];
  };
};

type TaskForm = {
  taskId: string;
  title: string;
  parentProjectName: string;
  workspacePath: string;
  status: string;
  phase: string;
  assignee: string;
  tags: string;
};

const EMPTY_FORM: TaskForm = {
  taskId: "",
  title: "",
  parentProjectName: "",
  workspacePath: "",
  status: "进行中",
  phase: "独立任务",
  assignee: "",
  tags: "",
};

const STATUS_OPTIONS = ["进行中", "开发中", "待运维验证", "待质量审计", "已完成", "已归档", "阻塞", "返工中"];

const STATUS_BADGE_CLASSES: Record<string, string> = {
  "进行中": "bg-sky-50 text-sky-700",
  "开发中": "bg-amber-50 text-amber-700",
  "待运维验证": "bg-indigo-50 text-indigo-700",
  "待质量审计": "bg-stone-100 text-stone-700",
  "已完成": "bg-emerald-50 text-emerald-700",
  "已归档": "bg-slate-100 text-slate-600",
  "阻塞": "bg-red-50 text-red-700",
  "返工中": "bg-purple-50 text-purple-700",
};

function formatTime(value: string | null): string {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function taskToForm(task: TaskEntry): TaskForm {
  return {
    taskId: task.taskId,
    title: task.title,
    parentProjectName: task.parentProjectName,
    workspacePath: task.workspacePath,
    status: task.status,
    phase: task.phase,
    assignee: task.assignee,
    tags: task.tags.join(", "),
  };
}

function formToPayload(form: TaskForm) {
  return {
    taskId: form.taskId.trim() || undefined,
    title: form.title.trim() || undefined,
    parentProjectName: form.parentProjectName.trim() || form.title.trim() || undefined,
    workspacePath: form.workspacePath.trim() || undefined,
    status: form.status.trim() || undefined,
    phase: form.phase.trim() || undefined,
    assignee: form.assignee.trim() || undefined,
    tags: form.tags.split(/[,，;\n]/).map((tag) => tag.trim()).filter(Boolean),
  };
}

function statusFilterKey(status: string): string {
  if (status === "已完成" || status === "已归档") return "completed";
  if (status === "阻塞") return "blocked";
  return "active";
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium ${STATUS_BADGE_CLASSES[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status || "--"}
    </span>
  );
}

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
        danger ? "border-red-200 bg-red-50 text-red-700 hover:bg-red-100" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}

export default function TaskDashboardPage({ token }: { token: string }) {
  const [directory, setDirectory] = React.useState<TaskDirectoryResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [searchTerm, setSearchTerm] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("");
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({});
  const [selectedTask, setSelectedTask] = React.useState<TaskEntry | null>(null);
  const [editingTask, setEditingTask] = React.useState<TaskEntry | null>(null);
  const [showAddForm, setShowAddForm] = React.useState(false);
  const [form, setForm] = React.useState<TaskForm>(EMPTY_FORM);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await readJson<TaskDirectoryResponse>("/api/task-battlefield/directory");
      setDirectory(next);
      setSelectedTask((current) => current ? next.tasks.find((task) => task.taskId === current.taskId) ?? null : null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const filteredTasks = React.useMemo(() => {
    const tasks = directory?.tasks ?? [];
    return tasks
      .filter((task) => !statusFilter || statusFilterKey(task.status) === statusFilter)
      .filter((task) => {
        if (!searchTerm.trim()) return true;
        const q = searchTerm.trim().toLowerCase();
        return [
          task.taskId,
          task.title,
          task.parentProjectName,
          task.workspacePath,
          task.status,
          task.phase,
          task.assignee,
          task.tags.join(" "),
        ].join(" ").toLowerCase().includes(q);
      })
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }, [directory, searchTerm, statusFilter]);

  const groups = React.useMemo(() => {
    const map: Record<string, TaskEntry[]> = {};
    const order: string[] = [];
    for (const task of filteredTasks) {
      const key = task.parentProjectName || "未归类任务";
      if (!map[key]) {
        map[key] = [];
        order.push(key);
      }
      map[key].push(task);
    }
    return order.map((name) => ({ name, tasks: map[name] }));
  }, [filteredTasks]);

  React.useEffect(() => {
    setExpandedGroups((current) => {
      const next = { ...current };
      for (const group of groups) {
        if (next[group.name] === undefined) next[group.name] = true;
      }
      return next;
    });
  }, [groups]);

  const stats = React.useMemo(() => {
    const result: Record<string, number> = {};
    for (const task of directory?.tasks ?? []) {
      result[task.status] = (result[task.status] ?? 0) + 1;
    }
    return result;
  }, [directory]);

  const saveTask = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = formToPayload(form);
      const endpoint = editingTask ? `/api/task-battlefield/tasks/${encodeURIComponent(editingTask.taskId)}` : "/api/task-battlefield/tasks";
      const method = editingTask ? "PUT" : "POST";
      const next = await readJson<TaskDirectoryResponse>(endpoint, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Control-Token": token,
        },
        body: JSON.stringify(payload),
      });
      setDirectory(next);
      const savedTask = editingTask
        ? next.tasks.find((task) => task.taskId === (payload.taskId ?? editingTask.taskId))
          ?? next.tasks.find((task) => task.taskId === editingTask.taskId)
          ?? next.tasks.find((task) => task.title === (payload.title ?? editingTask.title))
          ?? null
        : null;
      setSelectedTask(savedTask);
      setEditingTask(null);
      setShowAddForm(false);
      setForm(EMPTY_FORM);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const deleteTask = async (task: TaskEntry) => {
    setBusy(true);
    setError("");
    try {
      const next = await readJson<TaskDirectoryResponse>(`/api/task-battlefield/tasks/${encodeURIComponent(task.taskId)}`, {
        method: "DELETE",
        headers: { "X-Control-Token": token },
      });
      setDirectory(next);
      setSelectedTask(null);
      setEditingTask(null);
      setForm(EMPTY_FORM);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const openAdd = () => {
    setEditingTask(null);
    setSelectedTask(null);
    setForm(EMPTY_FORM);
    setShowAddForm(true);
  };

  const openEdit = (task: TaskEntry) => {
    setEditingTask(task);
    setSelectedTask(task);
    setShowAddForm(true);
    setForm(taskToForm(task));
  };

  const closeForm = () => {
    setEditingTask(null);
    setShowAddForm(false);
    setForm(EMPTY_FORM);
  };

  const total = directory?.tasks.length ?? 0;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-950">任务战场</h2>
            <p className="mt-1 break-all text-sm text-slate-600">
              {directory?.projectsRoot ?? "正在读取项目根目录..."}
            </p>
            {directory ? (
              <p className="mt-1 break-all text-xs text-slate-500">
                目录文件：{directory.directoryFile}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <IconButton title="刷新任务目录" onClick={refresh} disabled={loading || busy}>
              <RefreshCcw size={15} />
            </IconButton>
            <button
              type="button"
              onClick={openAdd}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus size={15} />
              添加任务
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-xl font-semibold text-slate-950">{total}</div>
            <div className="text-xs text-slate-500">任务条目</div>
          </div>
          {STATUS_OPTIONS.filter((status) => stats[status]).slice(0, 3).map((status) => (
            <div key={status} className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <div className="text-xl font-semibold text-slate-950">{stats[status]}</div>
              <div className="text-xs text-slate-500">{status}</div>
            </div>
          ))}
        </div>

        {directory?.sync.addedFolders.length ? (
          <div className="mt-3 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            已同步新增文件夹：{directory.sync.addedFolders.join(", ")}
          </div>
        ) : null}
        {directory?.sync.missingWorkspaces.length ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            有任务目录路径不存在：{directory.sync.missingWorkspaces.join(", ")}
          </div>
        ) : null}
        {error ? (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</div>
        ) : null}
      </section>

      {showAddForm ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-950">{editingTask ? "编辑任务条目" : "添加任务条目"}</h3>
            <IconButton title="关闭表单" onClick={closeForm} disabled={busy}>
              <X size={15} />
            </IconButton>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              TASK-ID
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.taskId} onChange={(e) => setForm({ ...form, taskId: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              任务名称
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              大项目
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.parentProjectName} onChange={(e) => setForm({ ...form, parentProjectName: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              状态
              <select className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              阶段
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.phase} onChange={(e) => setForm({ ...form, phase: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              负责人
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.assignee} onChange={(e) => setForm({ ...form, assignee: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600 md:col-span-2">
              工作区路径
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.workspacePath} onChange={(e) => setForm({ ...form, workspacePath: e.target.value })} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600 md:col-span-2">
              标签
              <input className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-teal-500" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
            </label>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button type="button" onClick={closeForm} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">取消</button>
            <button type="button" onClick={saveTask} disabled={busy || !token} className="inline-flex items-center gap-1.5 rounded-md border border-teal-700 bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50">
              <Save size={15} />
              保存
            </button>
          </div>
        </section>
      ) : null}

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-2 border-b border-slate-200 p-3 sm:flex-row sm:items-center">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-200 bg-slate-50 py-2 pl-8 pr-3 text-sm outline-none focus:border-teal-500"
              placeholder="搜索任务、项目、路径、标签"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal-500" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">全部状态</option>
            <option value="active">进行中</option>
            <option value="completed">已完成/归档</option>
            <option value="blocked">阻塞</option>
          </select>
        </div>

        <div className="divide-y divide-slate-200">
          {loading ? (
            <div className="px-3 py-10 text-center text-sm text-slate-400">正在读取任务目录...</div>
          ) : groups.length === 0 ? (
            <div className="px-3 py-10 text-center text-sm text-slate-400">没有匹配的任务条目</div>
          ) : groups.map((group) => {
            const open = expandedGroups[group.name] !== false;
            return (
              <div key={group.name}>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 bg-slate-100 px-3 py-2 text-left"
                  onClick={() => setExpandedGroups((current) => ({ ...current, [group.name]: !open }))}
                >
                  <span className={`inline-block w-4 shrink-0 text-xs text-slate-500 transition ${open ? "rotate-90" : ""}`}>▶</span>
                  <span className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-900">{group.name}</span>
                  <span className="shrink-0 text-xs text-slate-500">{group.tasks.length} 个任务</span>
                </button>
                {open ? (
                  <div className="divide-y divide-slate-100">
                    {group.tasks.map((task) => (
                      <div
                        key={task.taskId}
                        className="grid cursor-pointer gap-2 px-3 py-3 hover:bg-slate-50 xl:grid-cols-[minmax(90px,0.8fr)_minmax(120px,1.1fr)_minmax(100px,1fr)_84px_104px_minmax(140px,1.4fr)_72px]"
                        onClick={() => setSelectedTask(task)}
                      >
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">TASK-ID</div>
                          <div className="break-all font-mono text-xs text-slate-700">{task.taskId}</div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">任务</div>
                          <div className="break-words text-sm font-medium text-slate-900">{task.title}</div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">阶段</div>
                          <div className="line-clamp-2 break-words text-sm text-slate-600">{task.phase || "--"}</div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">状态</div>
                          <StatusBadge status={task.status} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">更新时间</div>
                          <div className="text-sm tabular-nums text-slate-600">{formatTime(task.updatedAt)}</div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-[10px] font-semibold uppercase text-slate-400 xl:hidden">工作区路径</div>
                          <div className="break-all text-xs text-sky-700" title={task.workspacePath}>{task.workspacePath}</div>
                        </div>
                        <div className="flex items-start justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                          <IconButton title="编辑任务条目" onClick={() => openEdit(task)} disabled={busy}><Edit3 size={14} /></IconButton>
                          <IconButton title="删除记录，不删除文件夹" onClick={() => deleteTask(task)} disabled={busy} danger><Trash2 size={14} /></IconButton>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      {selectedTask ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="min-w-0 truncate text-sm font-semibold text-slate-950">{selectedTask.title}</h3>
            <div className="flex gap-1">
              <IconButton title="编辑任务条目" onClick={() => openEdit(selectedTask)} disabled={busy}><Edit3 size={14} /></IconButton>
              <IconButton title="关闭详情" onClick={() => setSelectedTask(null)}><X size={14} /></IconButton>
            </div>
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-[120px_minmax(0,1fr)]">
            <span className="text-slate-500">TASK-ID</span><span className="font-mono text-slate-900">{selectedTask.taskId}</span>
            <span className="text-slate-500">大项目</span><span>{selectedTask.parentProjectName}</span>
            <span className="text-slate-500">阶段</span><span>{selectedTask.phase || "--"}</span>
            <span className="text-slate-500">负责人</span><span>{selectedTask.assignee || "--"}</span>
            <span className="text-slate-500">状态</span><span><StatusBadge status={selectedTask.status} /></span>
            <span className="text-slate-500">更新时间</span><span>{formatTime(selectedTask.updatedAt)}</span>
            <span className="text-slate-500">工作区路径</span><span className="break-all">{selectedTask.workspacePath}</span>
            <span className="text-slate-500">来源</span><span>{selectedTask.source}</span>
            <span className="text-slate-500">标签</span><span>{selectedTask.tags.length ? selectedTask.tags.join(", ") : "--"}</span>
          </div>
        </section>
      ) : null}
    </div>
  );
}
