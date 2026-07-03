import type { AgentConfig, AgentProfile, AgentSkill, OperationRecord, RecentRun, TaskTraceNode } from "../../types";

const roleMeta: Record<string, { title: string; role: string; icon: string; color: string }> = {
  "openclaw-coordinator": { title: "Commander Agent", role: "Commander", icon: "C", color: "#2f80c9" },
  "openclaw-orchestrator": { title: "SRE Guardian", role: "Operations", icon: "O", color: "#18a6a6" },
  "openclaw-main": { title: "Quality Auditor", role: "Reviewer", icon: "Q", color: "#d8a72e" },
  "openclaw-archivist": { title: "Project Archivist", role: "Archivist", icon: "A", color: "#8e5bbf" },
  "codex-code-agent": { title: "Code Executor", role: "Developer", icon: "D", color: "#3ba85a" },
};

function adventureStatus(status: AgentConfig["status"]): AgentProfile["status"] {
  if (status === "executing") return "running";
  if (status === "running") return "online";
  if (status === "error") return "error";
  if (status === "warning") return "error";
  return "offline";
}

function baseSkill(id: string, name: string, category: AgentSkill["category"], level: number, x: number, y: number, dependencies: string[] = [], permissions: string[] = []): AgentSkill {
  return {
    id,
    name,
    category,
    level,
    status: "enabled",
    description: "来自当前 Agent 角色、配置和运行状态的只读能力映射。",
    dependencies,
    permissions,
    position: { x, y },
    config: {},
    metrics: { successRate: 0, avgLatencyMs: 0, usageCount: 0 },
  };
}

function skillsFor(agent: AgentConfig): AgentSkill[] {
  const common = [
    baseSkill("config_read", "配置读取", "basic", 3, 50, 10),
    baseSkill("session_state", "会话状态", "workflow", 3, 25, 28, ["config_read"]),
    baseSkill("log_access", "日志入口", "tool", 3, 75, 28, ["config_read"], ["read_logs"]),
  ];
  if (agent.id === "openclaw-coordinator") {
    return [
      baseSkill("task_understanding", "任务理解", "basic", 3, 50, 8),
      baseSkill("task_decomposition", "任务拆解", "workflow", 4, 28, 28, ["task_understanding"]),
      baseSkill("agent_dispatch", "Agent 调度", "advanced", 4, 50, 50, ["task_decomposition"], ["call_agents", "read_sessions"]),
      baseSkill("result_summary", "结果汇总", "workflow", 4, 72, 66, ["agent_dispatch"]),
      baseSkill("quality_review", "质量验收", "quality", 4, 50, 86, ["result_summary"]),
      baseSkill("feishu_route", "飞书路由", "tool", 3, 78, 30, ["task_understanding"], ["send_messages"]),
    ];
  }
  if (agent.id === "openclaw-orchestrator") {
    return [
      baseSkill("environment_check", "环境检测", "basic", 3, 50, 8),
      baseSkill("path_check", "路径检查", "tool", 3, 25, 28, ["environment_check"]),
      baseSkill("service_start", "服务启动", "workflow", 3, 50, 46, ["path_check"], ["process_control"]),
      baseSkill("port_probe", "端口检测", "tool", 3, 75, 28, ["environment_check"]),
      baseSkill("log_diagnosis", "日志诊断", "quality", 4, 50, 68, ["service_start", "port_probe"]),
      baseSkill("regression_verify", "回归验证", "quality", 3, 50, 88, ["log_diagnosis"]),
    ];
  }
  if (agent.id === "openclaw-main") {
    return [
      baseSkill("quality_check", "质量检查", "quality", 4, 50, 10),
      baseSkill("risk_review", "风险识别", "advanced", 3, 28, 32, ["quality_check"]),
      baseSkill("rework_decision", "返工判断", "workflow", 4, 50, 54, ["risk_review"]),
      baseSkill("acceptance_report", "验收报告", "quality", 4, 72, 76, ["rework_decision"]),
    ];
  }
  if (agent.id === "openclaw-archivist") {
    return [
      baseSkill("run_record", "运行记录", "basic", 3, 50, 10),
      baseSkill("document_archive", "文档归档", "tool", 3, 30, 36, ["run_record"], ["write_docs"]),
      baseSkill("delivery_summary", "交付摘要", "workflow", 3, 70, 56, ["document_archive"]),
      baseSkill("version_notes", "版本整理", "quality", 3, 50, 82, ["delivery_summary"]),
    ];
  }
  if (agent.id === "codex-code-agent") {
    return [
      baseSkill("codex_cli", "Codex CLI", "tool", 4, 50, 8, [], ["execute_commands"]),
      baseSkill("file_edit", "文件修改", "tool", 4, 28, 32, ["codex_cli"], ["write_files"]),
      baseSkill("test_run", "测试执行", "quality", 3, 50, 56, ["file_edit"], ["execute_tests"]),
      baseSkill("a2a_reply", "A2A 回复", "workflow", 3, 72, 32, ["codex_cli"], ["send_messages"]),
      baseSkill("safe_config", "配置读取", "permission", 3, 50, 84, ["test_run", "a2a_reply"]),
    ];
  }
  return common;
}

export function toAgentProfiles(agents: AgentConfig[]): AgentProfile[] {
  return agents.map((agent) => {
    const meta = roleMeta[agent.id] ?? { title: agent.source, role: agent.role, icon: agent.name.slice(0, 1), color: "#2f80c9" };
    const skills = skillsFor(agent);
    const enabledSkills = skills.filter((skill) => skill.status === "enabled").length;
    return {
      id: agent.id,
      name: agent.name,
      title: meta.title,
      role: meta.role,
      status: adventureStatus(agent.status),
      model: agent.model || "--",
      workspace: agent.workspacePath || agent.configPath || "--",
      provider: agent.provider || "--",
      boundSessions: agent.sessionCount ?? 0,
      enabledSkills,
      totalSkills: skills.length,
      successRate: agent.successRate ?? 0,
      stability: agent.status === "error" ? 0 : agent.status === "warning" ? 0.6 : 0,
      avgLatencyMs: agent.lastLatencyMs ?? 0,
      dailyTokenUsed: 0,
      dailyTokenBudget: 0,
      lastInteraction: agent.lastInteractionAt || agent.lastCalledAt || "--",
      skills,
      equipment: {
        modelSlot: agent.model || "--",
        workspaceSlot: agent.workspacePath || agent.configPath || "--",
        toolSlots: agent.tools.length ? agent.tools : ["待接入"],
        knowledgeSlots: [agent.source],
        permissionSlots: [agent.permissionLevel || "--"],
        workflowSlot: agent.triggerMode || "--",
        evalSlot: "待接入",
      },
      classIcon: meta.icon,
      color: meta.color,
      currentTask: agent.currentTask,
      backendActions: agent.backendActions ?? [],
    };
  });
}

export function recentRunsFromOperations(operations: OperationRecord[]): RecentRun[] {
  return operations.slice(0, 8).map((operation, index) => ({
    id: `${operation.timestamp}-${index}`,
    taskId: `${operation.component}:${operation.action}`,
    agentName: operation.component,
    agentRole: "backend-operation",
    status: operation.ok ? "success" : "error",
    durationMs: operation.duration_ms,
    timestamp: operation.timestamp,
    model: "--",
    tokensUsed: 0,
  }));
}

export function taskTraceFromAgents(agents: AgentConfig[]): TaskTraceNode | null {
  const executing = agents.find((agent) => agent.status === "executing");
  if (!executing) return null;
  return {
    id: "current-task",
    type: "user",
    label: executing.currentTask && executing.currentTask !== "--" ? executing.currentTask : "当前任务",
    status: "running",
    children: [
      {
        id: executing.id,
        type: "agent",
        label: executing.name,
        agentId: executing.id,
        status: "running",
      },
    ],
  };
}
