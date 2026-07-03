export type ComponentStatus = {
  name: string;
  port: number | null;
  port_listening: boolean;
  pid_file: string | null;
  pid: number | null;
  pid_running: boolean;
  process_name: string | null;
};

export type ProviderStatus = {
  model: string;
  provider: string;
  mode: string;
  config: string;
};

export type StackStatus = {
  codex: ProviderStatus;
  openclaw: ComponentStatus;
  moonbridge: ComponentStatus;
  codex_agent: ComponentStatus;
  codex_agent_args: string;
  codex_agent_follows_global_config: boolean;
  codex_desktop_running: boolean;
  codex_desktop: {
    running: boolean;
    pid: number | null;
    process_count: number;
    executable: string | null;
  };
  stack_root: string;
};

export type OperationResult = {
  ok: boolean;
  component: string;
  action: string;
  message: string;
  pid?: number | null;
  port?: number | null;
  duration_ms: number;
};

export type ThreadMigrationResult = OperationResult & {
  source_session_id?: string | null;
  source_title?: string | null;
  target_provider?: string | null;
  target_model?: string | null;
  summary_path?: string | null;
  summary_dir?: string | null;
  launched_command?: string | null;
  launch_mode?: string | null;
};

export type ThreadListItem = {
  session_id: string;
  title: string;
  provider: string;
  model: string;
  updated_at: string;
};

export type OperationRecord = {
  timestamp: string;
  component: string;
  action: string;
  ok: boolean;
  message: string;
  duration_ms: number;
};

export type LogTail = {
  path: string;
  lines: string[];
};

export type CommandDiagnostic = {
  ok: boolean;
  returncode?: number;
  stdout?: string;
  stderr?: string;
  duration_ms: number;
};

export type MoonBridgeDiagnostic = {
  ok: boolean;
  reachable: boolean;
  status: number | null;
  models: string[];
  error: string;
  duration_ms: number;
};

export type Diagnostics = {
  codex_doctor: CommandDiagnostic;
  moonbridge_models: MoonBridgeDiagnostic;
  lark_auth_status: CommandDiagnostic;
};

export type AgentStatus = "running" | "stopped" | "warning" | "error" | "executing" | "unknown";

export type AgentConfig = {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  provider: string;
  model: string;
  pid: number | null;
  port: number | null;
  uptime: string;
  feishuBinding: string;
  triggerMode: string;
  tools: string[];
  permissionLevel: string;
  promptVersion: string;
  configPath: string;
  currentTask: string;
  lastCalledAt: string | null;
  lastLatencyMs: number | null;
  lastError: string;
  todayTaskCount: number | null;
  successRate: number | null;
  controlComponent: string | null;
  logsComponent: string | null;
  backendActions: BackendAction[] | null;
  source: "openclaw" | "codex-agent" | "infrastructure" | "unknown" | string;
  agentId: string | null;
  displayName: string | null;
  bindingStatus: string;
  feishuAccountEnabled: boolean | null;
  workspacePath: string | null;
  backingComponent: string | null;
  sessionCount: number | null;
  lastInteractionAt: string | null;
  a2aPeers: Array<{ name: string; description?: string | null; hasOpenId: boolean }> | null;
  configFacts: Record<string, unknown> | null;
};

export type BackendAction = {
  key: string;
  label: string;
  endpoint: string | null;
  logComponent: string | null;
  kind: "operation" | "log" | "detail" | "open" | "provider" | "info" | string;
  enabled: boolean;
  danger: boolean;
};

export type EditableA2APeer = {
  name: string;
  description: string;
  hasOpenId: boolean;
};

export type EditableAgentConfig = {
  agentId: string;
  source: "openclaw" | "codex-agent" | string;
  configPath: string;
  writableFields: string[];
  values: {
    AGENT_PROVIDER?: string;
    CODEX_AGENT_ARGS?: string;
    CODEX_CLI_TIMEOUT_MS?: string;
    CODEX_PROGRESS_INITIAL_MS?: string;
    CODEX_PROGRESS_INTERVAL_MS?: string;
    A2A_BOTS?: EditableA2APeer[];
    hasBotOpenId?: boolean;
    identityTheme?: string;
    feishuAccountEnabled?: boolean | null;
    hasFeishuAccount?: boolean;
    workspaceFiles?: string[];
  };
  latestBackup: string | null;
};

export type DashboardSummary = {
  systemHealth: "normal" | "warning" | "error" | "unknown";
  provider: string;
  feishuStatus: "connected" | "disconnected" | "error" | "unknown";
  onlineAgents: number;
  totalAgents: number;
  activeTasks: number | null;
  todayMessages: number | null;
  failedRequests: number;
};

export type DiagnosticAction = {
  id: string;
  label: string;
  endpoint: string | null;
  logComponent: string | null;
  danger: boolean;
};

export type ExplainedDiagnosticItem = {
  id: string;
  level: "normal" | "warning" | "error";
  title: string;
  affectedModules: string[];
  status: string;
  rawError: string;
  possibleCauses: string[];
  suggestions: string[];
  actions: DiagnosticAction[];
  relatedLogs: string[];
};

export const componentRows = [
  { key: "openclaw", title: "OpenClaw Gateway", logs: "openclaw" },
  { key: "moonbridge", title: "MoonBridge", logs: "moonbridge" },
  { key: "codex_agent", title: "Feishu Codex Agent", logs: "codex-agent" },
] as const;

export const logOptions = [
  { value: "openclaw", label: "OpenClaw" },
  { value: "moonbridge", label: "MoonBridge" },
  { value: "codex-agent", label: "Codex Agent" },
  { value: "codex-desktop", label: "Codex Desktop" },
  { value: "control-center-api", label: "Control API" },
  { value: "operations", label: "Operations" },
];

/* ===================================================
   Adventure Theme Types
   =================================================== */

export type SkillCategory = 'basic' | 'tool' | 'workflow' | 'permission' | 'advanced' | 'quality';

export type SkillStatus = 'locked' | 'available' | 'enabled' | 'disabled' | 'warning' | 'error';

export interface AgentSkill {
  id: string;
  name: string;
  category: SkillCategory;
  tree: 'common' | 'profession';
  level: number;
  status: SkillStatus;
  description: string;
  dependencies: string[];
  permissions: string[];
  position: { x: number; y: number };
  config: Record<string, unknown>;
  metrics: {
    successRate: number;
    avgLatencyMs: number;
    usageCount: number;
    lastError?: string;
  };
}

export type AdventureAgentStatus = 'online' | 'running' | 'idle' | 'error' | 'offline';

export interface AgentEquipment {
  modelSlot: string;
  workspaceSlot: string;
  toolSlots: string[];
  knowledgeSlots: string[];
  permissionSlots: string[];
  workflowSlot: string;
  evalSlot: string;
}

export interface AgentProfile {
  id: string;
  name: string;
  title: string;
  role: string;
  status: AdventureAgentStatus;
  model: string;
  workspace: string;
  provider: string;
  boundSessions: number;
  enabledSkills: number;
  totalSkills: number;
  successRate: number;
  stability: number;
  avgLatencyMs: number;
  dailyTokenUsed: number;
  dailyTokenBudget: number;
  lastInteraction: string;
  skills: AgentSkill[];
  equipment: AgentEquipment;
  classIcon: string;
  color: string;
  currentTask?: string;
  backendActions?: BackendAction[];
}

export interface TaskTraceNode {
  id: string;
  type: 'user' | 'agent' | 'tool' | 'summary' | 'complete';
  label: string;
  agentId?: string;
  status: 'pending' | 'running' | 'success' | 'error';
  latencyMs?: number;
  children?: TaskTraceNode[];
}

export interface RecentRun {
  id: string;
  taskId: string;
  agentName: string;
  agentRole: string;
  status: 'success' | 'error' | 'running';
  durationMs: number;
  timestamp: string;
  model: string;
  tokensUsed: number;
}
