import { useState, useMemo, useCallback, useEffect } from 'react';

// ---------- types ----------
type TaskStatus = '开发中' | '待运维验证' | '待质量审计' | '已完成' | '已归档' | '阻塞' | '返工中';

interface TaskState {
  taskId: string;
  phase: string;
  assignee: string;
  status: TaskStatus;
  updated: string;
  artifactPath: string | null;
  selfTest: string | null;
  auditResult: string | null;
  opsResult: string | null;
  archiveDate: string | null;
  parent_project: string;
}

// ---------- sample data (matches task_state.json schema) ----------
const SAMPLE_TASKS: TaskState[] = [
  { taskId: 'phase1-health-monitor', phase: 'Phase 1', assignee: '代码执行官', status: '已归档', updated: '2026-06-30T12:00:00', artifactPath: 'agent-evolution/phase1-health-monitor/health_check.py', selfTest: '3项检查全部通过', auditResult: '通过 - 已归档', opsResult: '通过', archiveDate: '2026-06-30', parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'phase2-config-conflict-detection', phase: 'Phase 2', assignee: '代码执行官', status: '已归档', updated: '2026-06-30T13:30:00', artifactPath: 'agent-evolution/phase2-config-conflict/config_checker.py', selfTest: '检测到2个端口冲突、5个AppSecret泄漏', auditResult: '通过 - 数据安全边界已定义', opsResult: '复审通过', archiveDate: '2026-06-30', parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'phase3-task-dashboard', phase: 'Phase 3', assignee: '代码执行官', status: '开发中', updated: '2026-07-08T18:55:00', artifactPath: 'agent-evolution/phase3-task-dashboard/dashboard.html', selfTest: '构建中 - HTML独立仪表盘', auditResult: null, opsResult: null, archiveDate: null, parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'phase4-privacy-scan', phase: 'Phase 4', assignee: '代码执行官', status: '已归档', updated: '2026-06-30T15:00:00', artifactPath: 'agent-evolution/phase4-privacy-scan/privacy_scan.py', selfTest: '扫描50+文件，检测15个appSecret', auditResult: '通过 - 补充数据安全规则后通过', opsResult: '复审通过（初检漏5个appSecret）', archiveDate: '2026-06-30', parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'phase5-skill-registry', phase: 'Phase 5', assignee: '代码执行官', status: '已完成', updated: '2026-07-08T18:15:00', artifactPath: 'agent-evolution/phase5-skill-registry/tests/check_registry.py', selfTest: 'skill-registry.json 注册16个skill，sha256漂移检测', auditResult: '通过 - 评分44/50', opsResult: '三目录确认: codeX(11) npm(57) lark-cli(27)', archiveDate: null, parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'phase6-task-calc-regression', phase: 'Phase 6', assignee: '代码执行官', status: '已完成', updated: '2026-07-08T18:55:00', artifactPath: 'agent-evolution/phase6-task-calc-regression/task_calc_regression.py', selfTest: '20/20项通过', auditResult: '通过 - 评分44/50', opsResult: 'JS 15项全通过，浏览器环境已确认', archiveDate: null, parent_project: 'Agent Control Center 发展规划' },
  { taskId: 'TASK-MMI-3D-OPT-20260703-113038', phase: '独立任务', assignee: '代码执行官', status: '待运维验证', updated: '2026-07-04T16:02:00', artifactPath: 'agent-evolution/index/MMI-3D-OPT/src/mmr_2d_optimize.py', selfTest: '2D优化跑通，收敛曲线正常', auditResult: null, opsResult: null, archiveDate: null, parent_project: 'MMI 优化' },
];

// ---------- constants ----------
const STATUS_BADGE_CLASSES: Record<string, string> = {
  '开发中': 'bg-amber-50 text-amber-600',
  '待运维验证': 'bg-indigo-50 text-indigo-600',
  '待质量审计': 'bg-stone-50 text-stone-600',
  '已完成': 'bg-emerald-50 text-emerald-600',
  '已归档': 'bg-gray-100 text-gray-500',
  '阻塞': 'bg-red-50 text-red-600',
  '返工中': 'bg-purple-50 text-purple-600',
};

const FILTER_OPTIONS: { label: string; value: string }[] = [
  { label: '全部状态', value: '' },
  { label: '已完成', value: 'completed' },
  { label: '进行中', value: 'in_progress' },
  { label: '阻塞', value: 'blocked' },
];

const LS_KEY = 'dashboard-project-names';

// ---------- helpers ----------
function formatTime(iso: string | null): string {
  if (!iso) return '--';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}

function loadProjectNames(): Record<string, string> {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveProjectNames(names: Record<string, string>) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(names)); } catch { /* noop */ }
}

function statusToFilterKey(status: TaskStatus): string {
  if (status === '已归档' || status === '已完成') return 'completed';
  if (status === '阻塞') return 'blocked';
  return 'in_progress';
}

// ---------- main component ----------
export default function TaskDashboardPage() {
  const [tasks] = useState<TaskState[]>(SAMPLE_TASKS);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [projectNames, setProjectNames] = useState<Record<string, string>>(loadProjectNames);
  const [editingGroup, setEditingGroup] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'updated' | 'taskId' | 'phase' | 'assignee' | 'status'>('updated');
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskState | null>(null);

  // persist project names
  useEffect(() => { saveProjectNames(projectNames); }, [projectNames]);

  // filtered + sorted tasks
  const filteredTasks = useMemo(() => {
    let result = [...tasks];

    if (statusFilter) {
      result = result.filter(t => statusToFilterKey(t.status) === statusFilter);
    }
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      result = result.filter(t =>
        [t.taskId, t.phase, t.assignee, t.status, t.artifactPath, t.parent_project]
          .filter(Boolean).join(' ').toLowerCase().includes(q)
      );
    }

    result.sort((a, b) => {
      const va = a[sortField] || '';
      const vb = b[sortField] || '';
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
    return result;
  }, [tasks, statusFilter, searchTerm, sortField, sortAsc]);

  // group by parent_project
  const groups = useMemo(() => {
    const map: Record<string, TaskState[]> = {};
    const order: string[] = [];
    for (const t of filteredTasks) {
      const key = t.parent_project || '未归类任务';
      if (!map[key]) { map[key] = []; order.push(key); }
      map[key].push(t);
    }
    return order.map(name => ({ name, tasks: map[name] }));
  }, [filteredTasks]);

  const stats = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of tasks) m[t.status] = (m[t.status] || 0) + 1;
    return m;
  }, [tasks]);

  const toggleGroup = useCallback((name: string) => {
    setExpandedGroups(prev => ({ ...prev, [name]: prev[name] === false ? true : false }));
  }, []);

  const startEdit = useCallback((name: string) => {
    setEditingGroup(name);
    setEditValue(projectNames[name] || name);
  }, [projectNames]);

  const finishEdit = useCallback(() => {
    if (!editingGroup) return;
    const trimmed = editValue.trim();
    setProjectNames(prev => {
      const next = { ...prev };
      if (trimmed && trimmed !== editingGroup) {
        next[editingGroup] = trimmed;
      } else {
        delete next[editingGroup];
      }
      return next;
    });
    setEditingGroup(null);
  }, [editingGroup, editValue]);

  // initialise all groups as expanded
  useEffect(() => {
    const init: Record<string, boolean> = {};
    for (const g of groups) {
      if (expandedGroups[g.name] === undefined) init[g.name] = true;
    }
    if (Object.keys(init).length) setExpandedGroups(prev => ({ ...prev, ...init }));
  }, [groups]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(true); }
  };

  const sortArrow = (field: typeof sortField) => {
    if (sortField !== field) return '';
    return sortAsc ? ' ▲' : ' ▼';
  };

  const getDisplayName = (key: string) => projectNames[key] || key;

  // ---------- render ----------
  return (
    <div className='max-w-7xl mx-auto px-5 py-6'>
      {/* header */}
      <div className='flex items-center justify-between mb-5 flex-wrap gap-3'>
        <div>
          <h1 className='text-[22px] font-semibold text-gray-900'>任务状态仪表盘</h1>
          <div className='text-xs text-gray-500 mt-0.5'>Phase 3 &middot; Agent Evolution &middot; {filteredTasks.length} 个任务</div>
        </div>
      </div>

      {/* stats row */}
      <div className='flex gap-2.5 mb-5 flex-wrap'>
        {(['开发中', '待运维验证', '待质量审计', '已完成', '已归档', '阻塞', '返工中'] as TaskStatus[]).map(s => (
          stats[s] !== undefined && (
            <div key={s} className='bg-white border border-gray-200 rounded-lg px-4 py-3 min-w-[90px] text-center flex-1'>
              <div className='text-[26px] font-semibold text-gray-900'>{stats[s]}</div>
              <div className='text-[11px] text-gray-500 mt-0.5'>{s}</div>
            </div>
          )
        ))}
      </div>

      {/* toolbar */}
      <div className='flex items-center gap-2.5 mb-3 bg-white border border-gray-200 rounded-lg px-3.5 py-2 flex-wrap'>
        <div className='relative flex-1 min-w-[200px]'>
          <svg className='absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none' fill='none' viewBox='0 0 24 24' stroke='currentColor' strokeWidth={2}>
            <path strokeLinecap='round' strokeLinejoin='round' d='M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z' />
          </svg>
          <input
            className='w-full pl-8 pr-2.5 py-1.5 border border-gray-200 rounded-md text-[13px] bg-gray-50 outline-none focus:border-blue-500'
            placeholder='搜索 TASK-ID / 阶段 / 负责人...'
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
        <select
          className='px-2.5 py-1.5 border border-gray-200 rounded-md text-[13px] bg-gray-50 cursor-pointer text-gray-700'
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          {FILTER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* table */}
      <div className='bg-white border border-gray-200 rounded-lg overflow-x-auto'>
        <table className='w-full border-collapse'>
          <thead>
            <tr>
              {([
                ['taskId', 'TASK-ID'],
                ['phase', '阶段'],
                ['assignee', '负责人'],
                ['status', '状态'],
                ['updated', '更新时间'],
              ] as const).map(([f, label]) => (
                <th
                  key={f}
                  className='text-left px-3.5 py-2.5 text-xs font-semibold text-gray-500 border-b border-gray-200 cursor-pointer select-none whitespace-nowrap hover:text-blue-500'
                  onClick={() => handleSort(f)}
                >
                  {label}<span className='ml-1 text-[10px]'>{sortArrow(f)}</span>
                </th>
              ))}
              <th className='text-left px-3.5 py-2.5 text-xs font-semibold text-gray-500 border-b border-gray-200 whitespace-nowrap'>产物路径</th>
            </tr>
          </thead>
          <tbody>
            {filteredTasks.length === 0 ? (
              <tr><td colSpan={6} className='text-center py-10 text-gray-400'>无匹配任务</td></tr>
            ) : (
              groups.flatMap(g => {
                const isOpen = expandedGroups[g.name] !== false;
                const rows: React.ReactNode[] = [];
                // group header row
                rows.push(
                  <tr key={'g-' + g.name} className='cursor-pointer bg-gray-100 border-b-2 border-gray-300'>
                    <td colSpan={6} className='p-0'>
                      <div
                        className='flex items-center gap-1.5 px-3.5 py-2.5'
                        onClick={() => toggleGroup(g.name)}
                      >
                        <span className='text-[11px] text-gray-500 w-4 text-center inline-block transition-transform' style={isOpen ? {transform:'rotate(90deg)'} : {}}>
                          {'▶'}
                        </span>
                        {editingGroup === g.name ? (
                          <input
                            className='border border-blue-400 rounded px-1.5 py-0.5 text-[13px] font-semibold outline-none bg-white w-[260px] text-gray-900'
                            value={editValue}
                            onChange={e => setEditValue(e.target.value)}
                            onBlur={finishEdit}
                            onKeyDown={e => { if (e.key === 'Enter') finishEdit(); if (e.key === 'Escape') { setEditValue(projectNames[g.name] || g.name); finishEdit(); } }}
                            autoFocus
                            onClick={e => e.stopPropagation()}
                          />
                        ) : (
                          <span
                            className='font-semibold text-[13px] text-gray-900 group'
                            onClick={e => { e.stopPropagation(); startEdit(g.name); }}
                          >
                            {getDisplayName(g.name)}
                            <span className='text-[10px] text-gray-400 ml-1.5 opacity-0 group-hover:opacity-100 transition-opacity'>{'✎'}</span>
                          </span>
                        )}
                        <span className='text-xs text-gray-500 ml-2'>{g.tasks.length} 个任务</span>
                      </div>
                    </td>
                  </tr>
                );
                // task rows
                if (isOpen) {
                  for (const t of g.tasks) {
                    rows.push(
                      <tr key={t.taskId} className='hover:bg-gray-50 cursor-pointer border-b border-gray-100' onClick={() => setSelectedTask(t)}>
                        <td className='px-3.5 py-2.5 text-xs font-mono pl-7'>{t.taskId}</td>
                        <td className='px-3.5 py-2.5 text-[13px] whitespace-nowrap'>{t.phase}</td>
                        <td className='px-3.5 py-2.5 text-[13px] whitespace-nowrap'>{t.assignee}</td>
                        <td className='px-3.5 py-2.5 whitespace-nowrap'>
                          <span className={'inline-block px-2.5 py-1 rounded-full text-[11px] font-medium ' + (STATUS_BADGE_CLASSES[t.status] || 'bg-gray-100 text-gray-500')}>
                            {t.status}
                          </span>
                        </td>
                        <td className='px-3.5 py-2.5 text-[13px] whitespace-nowrap tabular-nums'>{formatTime(t.updated)}</td>
                        <td className='px-3.5 py-2.5 text-[11px] whitespace-nowrap'>
                          {t.artifactPath ? (
                            <span className='text-blue-500 cursor-pointer hover:underline' onClick={e => { e.stopPropagation(); setSelectedTask(t); }}>
                              {t.artifactPath}
                            </span>
                          ) : <span className='text-gray-400'>--</span>}
                        </td>
                      </tr>
                    );
                  }
                }
                return rows;
              })
            )}
          </tbody>
        </table>
      </div>

      {/* detail panel */}
      {selectedTask && (
        <div className='bg-white border border-gray-200 rounded-lg p-4 mt-3'>
          <div className='flex items-center justify-between mb-2.5'>
            <h3 className='text-[15px] font-semibold text-gray-900'>{selectedTask.taskId}</h3>
            <button className='px-3 py-1.5 border border-gray-200 rounded-md text-xs text-gray-500 hover:bg-gray-50' onClick={() => setSelectedTask(null)}>关闭</button>
          </div>
          <div className='grid grid-cols-[120px_1fr] gap-1.5 text-[13px]'>
            <span className='text-gray-500'>阶段</span><span>{selectedTask.phase}</span>
            <span className='text-gray-500'>负责人</span><span>{selectedTask.assignee}</span>
            <span className='text-gray-500'>状态</span>
            <span><span className={'inline-block px-2.5 py-1 rounded-full text-[11px] font-medium ' + (STATUS_BADGE_CLASSES[selectedTask.status] || 'bg-gray-100 text-gray-500')}>{selectedTask.status}</span></span>
            <span className='text-gray-500'>更新时间</span><span>{formatTime(selectedTask.updated)}</span>
            <span className='text-gray-500'>产物路径</span><span>{selectedTask.artifactPath || '--'}</span>
            <span className='text-gray-500'>自测结果</span><span>{selectedTask.selfTest || '--'}</span>
            <span className='text-gray-500'>运维验证</span><span>{selectedTask.opsResult || '--'}</span>
            <span className='text-gray-500'>质量审计</span><span>{selectedTask.auditResult || '--'}</span>
            <span className='text-gray-500'>归档日期</span><span>{selectedTask.archiveDate || '--'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
