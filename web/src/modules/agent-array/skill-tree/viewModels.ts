import type { AgentConfig, AgentProfile, AgentSkill, OperationRecord, RecentRun, TaskTraceNode } from "../../../types";

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
  if (status === "error" || status === "warning") return "error";
  return "offline";
}

function hasAction(agent: AgentConfig, key: string, kind?: string) {
  return Boolean((agent.backendActions ?? []).some((action) => action.enabled && (action.key === key || action.kind === kind)));
}

function skill(
  id: string,
  tree: AgentSkill["tree"],
  name: string,
  category: AgentSkill["category"],
  level: number,
  status: AgentSkill["status"],
  x: number,
  y: number,
  dependencies: string[] = [],
  permissions: string[] = [],
  description?: string,
  config: Record<string, unknown> = {},
): AgentSkill {
  return {
    id,
    tree,
    name,
    category,
    level,
    status,
    description: description ?? (status === "locked" ? "未来规划能力：尚未接入真实后端或配置源。" : "已从当前 Agent 配置、运行状态或后端能力映射点亮。"),
    dependencies,
    permissions,
    position: { x, y },
    config,
    metrics: {
      successRate: status === "enabled" ? 1 : 0,
      avgLatencyMs: 0,
      usageCount: status === "enabled" ? 1 : 0,
    },
  };
}

function commonSkills(agent: AgentConfig): AgentSkill[] {
  const workspace = Boolean(agent.workspacePath || agent.configPath);
  const sessions = (agent.sessionCount ?? 0) > 0 || Boolean(agent.lastInteractionAt);
  const logs = hasAction(agent, "logs", "log");
  const detail = hasAction(agent, "detail", "detail");
  const editable = agent.id === "codex-code-agent" || agent.source === "openclaw";
  return [
    skill("common_config_read", "common", "配置读取", "basic", 3, workspace ? "enabled" : "warning", 18, 12, [], [], "读取 Agent 配置、身份、workspace 和运行基本信息。"),
    skill("common_identity", "common", "身份识别", "basic", 3, agent.name ? "enabled" : "warning", 18, 28, ["common_config_read"], [], "识别 Agent 名称、角色、来源与承载组件。"),
    skill("common_session_state", "common", "会话状态", "workflow", 3, sessions ? "enabled" : "available", 18, 44, ["common_identity"], ["read_sessions"], "读取最近会话、绑定数和最后交互时间。"),
    skill("common_log_access", "common", "日志入口", "tool", 3, logs ? "enabled" : "available", 18, 60, ["common_identity"], ["read_logs"], "连接 Gateway/Codex Agent 日志入口。"),
    skill("common_detail_drawer", "common", "详情抽屉", "tool", 2, detail ? "enabled" : "available", 18, 76, ["common_config_read"], [], "打开只读详情、团队关系和后端功能映射。"),
    skill("common_safe_edit", "common", "安全配置编辑", "permission", 2, editable ? "enabled" : "locked", 18, 92, ["common_config_read"], ["x_control_token"], "仅开放白名单字段，保存前备份并要求本地 token。"),
    skill("common_replay", "common", "任务回放", "advanced", 1, "locked", 34, 84, ["common_session_state", "common_log_access"], ["read_traces"], "规划能力：从 sessions/jsonl 生成完整输入、输出、耗时和日志回放。"),
  ];
}

function coordinatorSkills(): AgentSkill[] {
  return [
    skill("pro_task_understanding", "profession", "任务理解", "basic", 4, "enabled", 58, 10),
    skill("pro_task_decomposition", "profession", "任务拆解", "workflow", 4, "enabled", 50, 26, ["pro_task_understanding"]),
    skill("pro_agent_dispatch", "profession", "Agent 调度", "advanced", 4, "enabled", 66, 42, ["pro_task_decomposition"], ["call_agents", "read_sessions"]),
    skill("pro_result_summary", "profession", "结果汇总", "workflow", 4, "enabled", 58, 60, ["pro_agent_dispatch"]),
    skill("pro_quality_gate", "profession", "交付闸门", "quality", 3, "enabled", 74, 76, ["pro_result_summary"]),
    skill("pro_parallel_planning", "profession", "并行规划", "advanced", 2, "locked", 88, 30, ["pro_task_decomposition"], ["parallel_dispatch"]),
    skill("pro_budget_guard", "profession", "预算守卫", "permission", 1, "locked", 88, 58, ["pro_agent_dispatch"], ["token_budget"]),
    skill("pro_auto_rebalance", "profession", "自动再平衡", "advanced", 1, "locked", 88, 86, ["pro_quality_gate"], ["write_routes"]),
  ];
}

function orchestratorSkills(): AgentSkill[] {
  return [
    skill("pro_environment_check", "profession", "环境检测", "basic", 4, "enabled", 58, 10),
    skill("pro_path_check", "profession", "路径检查", "tool", 3, "enabled", 48, 28, ["pro_environment_check"]),
    skill("pro_port_probe", "profession", "端口检测", "tool", 3, "enabled", 68, 28, ["pro_environment_check"]),
    skill("pro_service_start", "profession", "服务启动", "workflow", 3, "enabled", 58, 48, ["pro_path_check", "pro_port_probe"], ["process_control"]),
    skill("pro_log_diagnosis", "profession", "日志诊断", "quality", 4, "enabled", 58, 68, ["pro_service_start"]),
    skill("pro_regression_verify", "profession", "回归验证", "quality", 3, "enabled", 58, 88, ["pro_log_diagnosis"]),
    skill("pro_health_daemon", "profession", "健康守护", "advanced", 1, "locked", 86, 40, ["pro_port_probe"], ["scheduled_checks"]),
    skill("pro_auto_repair", "profession", "自动修复剧本", "advanced", 1, "locked", 86, 70, ["pro_log_diagnosis"], ["write_config", "restart_services"]),
  ];
}

function auditorSkills(): AgentSkill[] {
  return [
    skill("pro_quality_check", "profession", "质量检查", "quality", 4, "enabled", 58, 10),
    skill("pro_risk_review", "profession", "风险识别", "advanced", 3, "enabled", 48, 32, ["pro_quality_check"]),
    skill("pro_rework_decision", "profession", "返工判断", "workflow", 4, "enabled", 58, 54, ["pro_risk_review"]),
    skill("pro_acceptance_report", "profession", "验收报告", "quality", 4, "enabled", 68, 76, ["pro_rework_decision"]),
    skill("pro_eval_suite", "profession", "评估集管理", "quality", 1, "locked", 86, 30, ["pro_quality_check"], ["read_eval_files"]),
    skill("pro_policy_diff", "profession", "策略差异审计", "advanced", 1, "locked", 86, 58, ["pro_risk_review"], ["compare_versions"]),
    skill("pro_release_signoff", "profession", "发布签核", "permission", 1, "locked", 86, 86, ["pro_acceptance_report"], ["approval_flow"]),
  ];
}

function archivistSkills(): AgentSkill[] {
  return [
    skill("pro_run_record", "profession", "运行记录", "basic", 3, "enabled", 58, 10),
    skill("pro_document_archive", "profession", "文档归档", "tool", 3, "enabled", 50, 34, ["pro_run_record"], ["write_docs"]),
    skill("pro_delivery_summary", "profession", "交付摘要", "workflow", 3, "enabled", 66, 56, ["pro_document_archive"]),
    skill("pro_version_notes", "profession", "版本整理", "quality", 3, "enabled", 58, 82, ["pro_delivery_summary"]),
    skill("pro_knowledge_index", "profession", "知识索引", "advanced", 1, "locked", 86, 28, ["pro_document_archive"], ["index_docs"]),
    skill("pro_artifact_pack", "profession", "交付包生成", "tool", 1, "locked", 86, 56, ["pro_delivery_summary"], ["export_files"]),
    skill("pro_timeline_report", "profession", "时间线报告", "quality", 1, "locked", 86, 84, ["pro_version_notes"], ["read_traces"]),
  ];
}

function codeSkills(agent: AgentConfig): AgentSkill[] {
  const hasA2A = (agent.a2aPeers ?? []).length > 0;
  return [
    skill("pro_codex_cli", "profession", "Codex CLI", "tool", 4, "enabled", 58, 10, [], ["execute_commands"]),
    skill("pro_file_edit", "profession", "文件修改", "tool", 4, "enabled", 48, 32, ["pro_codex_cli"], ["write_files"]),
    skill("pro_test_run", "profession", "测试执行", "quality", 3, "enabled", 58, 54, ["pro_file_edit"], ["execute_tests"]),
    skill("pro_a2a_reply", "profession", "A2A 回复", "workflow", 3, hasA2A ? "enabled" : "warning", 70, 32, ["pro_codex_cli"], ["send_messages"]),
    skill("pro_safe_config", "profession", "安全配置读取", "permission", 3, "enabled", 58, 80, ["pro_test_run", "pro_a2a_reply"]),
    skill("pro_patch_planner", "profession", "补丁规划器", "advanced", 1, "locked", 86, 26, ["pro_file_edit"], ["structured_diff"]),
    skill("pro_ci_triage", "profession", "CI 诊断", "quality", 1, "locked", 86, 54, ["pro_test_run"], ["github_checks"]),
    skill("pro_code_review_bot", "profession", "自动审查", "advanced", 1, "locked", 86, 84, ["pro_safe_config"], ["review_threads"]),
  ];
}

function professionSkills(agent: AgentConfig): AgentSkill[] {
  if (agent.id === "openclaw-coordinator") return coordinatorSkills();
  if (agent.id === "openclaw-orchestrator") return orchestratorSkills();
  if (agent.id === "openclaw-main") return auditorSkills();
  if (agent.id === "openclaw-archivist") return archivistSkills();
  if (agent.id === "codex-code-agent") return codeSkills(agent);
  return [];
}

function skillsFor(agent: AgentConfig): AgentSkill[] {
  return [...commonSkills(agent), ...professionSkills(agent)];
}

export function toAgentProfiles(agents: AgentConfig[]): AgentProfile[] {
  return agents.map((agent) => {
    const meta = roleMeta[agent.id] ?? { title: agent.source, role: agent.role, icon: agent.name.slice(0, 1), color: "#2f80c9" };
    const skills = skillsFor(agent);
    const enabledSkills = skills.filter((item) => item.status === "enabled").length;
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
