"""Diagnostic explanations owned by the diagnostics feature."""
from typing import Any
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import ComponentStatus, ExplainedDiagnosticItem
from feishu_stack.core.status import get_status
from feishu_stack.modules.agent_array.skill_tree.agent_registry import load_registry
from . import diagnostics as diagnostics_module

def _component_running(component: ComponentStatus) -> bool:
    return bool(component.pid_running or component.port_listening)

def _action(id: str, label: str, endpoint: str | None = None, log_component: str | None = None, danger: bool = False) -> dict[str, Any]:
    return {
        "id": id,
        "label": label,
        "endpoint": endpoint,
        "logComponent": log_component,
        "danger": danger,
    }

def explained_diagnostics(config: StackConfig | None = None, diagnostic_data: dict[str, Any] | None = None) -> list[ExplainedDiagnosticItem]:
    cfg = config or load_config()
    data = diagnostic_data or diagnostics_module.diagnostics(cfg)
    stack = data.get("status") or get_status(cfg)
    if isinstance(stack, dict):
        provider_mode = stack.get("codex", {}).get("mode", "unknown")
        openclaw_running = bool(stack.get("openclaw", {}).get("pid_running") or stack.get("openclaw", {}).get("port_listening"))
        codex_agent_running = bool(stack.get("codex_agent", {}).get("pid_running") or stack.get("codex_agent", {}).get("port_listening"))
    else:
        provider_mode = stack.codex.mode
        openclaw_running = _component_running(stack.openclaw)
        codex_agent_running = _component_running(stack.codex_agent)

    items: list[ExplainedDiagnosticItem] = []
    deepseek_diag = data.get("deepseek_env", {})
    if provider_mode == "deepseek" and not deepseek_diag.get("ok"):
        items.append(
            ExplainedDiagnosticItem(
                id="deepseek-env-missing",
                level="error",
                title="DeepSeek API Key 未就绪",
                affectedModules=["DeepSeek", "Provider", "Codex Runtime"],
                status="需要处理",
                rawError=str(deepseek_diag.get("error") or "DEEPSEEK_API_KEY is missing"),
                possibleCauses=["当前 ACC 进程未读取到 DeepSeek API key 环境变量", "设置环境变量后尚未重启 ACC / Codex Agent"],
                suggestions=["设置 DEEPSEEK_API_KEY 用户环境变量", "重启 ACC 和 Feishu Codex Agent", "临时切换到 Native Provider"],
                actions=[_action("switch-native", "Switch Native", "/api/codex-provider/native")],
                relatedLogs=["operations", "codex-agent"],
            )
        )
    elif provider_mode == "deepseek":
        items.append(
            ExplainedDiagnosticItem(
                id="deepseek-env-ok",
                level="normal",
                title="DeepSeek Provider 就绪",
                affectedModules=["DeepSeek", "Provider"],
                status="正常",
                rawError="",
                possibleCauses=[],
                suggestions=["保持当前 Provider 配置"],
                actions=[],
                relatedLogs=[],
            )
        )

    lark_diag = data.get("lark_auth_status", {})
    if lark_diag and not lark_diag.get("ok"):
        items.append(
            ExplainedDiagnosticItem(
                id="lark-auth-error",
                level="warning",
                title="飞书认证状态异常",
                affectedModules=["Feishu Codex Agent", "lark-cli"],
                status="需要检查",
                rawError=str(lark_diag.get("stderr") or lark_diag.get("stdout") or "lark-cli auth status failed"),
                possibleCauses=["lark-cli 未登录", "认证缓存失效", "当前 profile 与 Agent 配置不一致"],
                suggestions=["重新检查 lark-cli auth status", "查看 Codex Agent 日志", "确认本机飞书 Agent 配置"],
                actions=[_action("view-agent-logs", "View Logs", log_component="codex-agent")],
                relatedLogs=["codex-agent"],
            )
        )

    if not codex_agent_running:
        items.append(
            ExplainedDiagnosticItem(
                id="codex-agent-stopped",
                level="warning",
                title="Feishu Codex Agent 未运行",
                affectedModules=["Feishu Codex Agent"],
                status="已停止",
                rawError="codex-agent pid 或进程未检测到",
                possibleCauses=["Agent 尚未启动", "启动脚本失败", "Codex CLI 或飞书认证异常"],
                suggestions=["启动 Codex Agent", "查看 Agent 日志", "运行全量诊断"],
                actions=[
                    _action("start-codex-agent", "Start Agent", "/api/codex-agent/start"),
                    _action("view-agent-logs", "View Logs", log_component="codex-agent"),
                ],
                relatedLogs=["codex-agent", "operations"],
            )
        )

    if not openclaw_running:
        items.append(
            ExplainedDiagnosticItem(
                id="openclaw-stopped",
                level="warning",
                title="OpenClaw Gateway 未监听",
                affectedModules=["OpenClaw Gateway"],
                status="已停止",
                rawError="OpenClaw Gateway 端口未监听",
                possibleCauses=["OpenClaw 未启动", "gateway 命令路径不可用", "端口被占用或启动失败"],
                suggestions=["启动 OpenClaw Gateway", "查看 OpenClaw 日志", "确认配置中的 gatewayCmd"],
                actions=[
                    _action("start-openclaw", "Start OpenClaw", "/api/openclaw/start"),
                    _action("view-openclaw-logs", "View Logs", log_component="openclaw"),
                ],
                relatedLogs=["openclaw", "operations"],
            )
        )
    else:
        try:
            if isinstance(stack, dict):
                registry_agents = load_registry(cfg)
            else:
                registry_agents = load_registry(cfg, openclaw_status=stack.openclaw, codex_agent_status=stack.codex_agent)
        except Exception:
            registry_agents = []
        for agent in registry_agents:
            if agent.source == "openclaw" and agent.status == "warning":
                items.append(
                    ExplainedDiagnosticItem(
                        id=f"openclaw-agent-{agent.agent_id}-warning",
                        level="warning",
                        title=f"{agent.display_name} 配置不完整",
                        affectedModules=[agent.display_name, "OpenClaw"],
                        status=agent.binding_status,
                        rawError="OpenClaw Agent binding、Feishu account 或 session 文件未完整就绪",
                        possibleCauses=["openclaw.json 中 binding 缺失", "Feishu account 未启用", "sessions.json 缺失或不可读"],
                        suggestions=["检查 OpenClaw 配置", "查看 Gateway 日志", "确认该角色的 Feishu account 已启用"],
                        actions=[
                            _action("view-openclaw-logs", "View Logs", log_component="openclaw"),
                            _action("open-openclaw-ui", "Open UI", "/api/openclaw/open-ui"),
                        ],
                        relatedLogs=["openclaw", "operations"],
                    )
                )
            if agent.source == "codex-agent" and (agent.binding_status != "bound" or len(agent.a2a_peers) < 5):
                items.append(
                    ExplainedDiagnosticItem(
                        id="codex-agent-a2a-warning",
                        level="warning",
                        title="代码执行官 A2A 配置不完整",
                        affectedModules=["Feishu Codex Agent", "A2A_BOTS"],
                        status=agent.binding_status,
                        rawError="Codex Agent .env 中 LARK_BOT_OPEN_ID 或 A2A_BOTS 未完整配置",
                        possibleCauses=[".env 缺失机器人 open_id", "A2A_BOTS 少于 5 个团队机器人", "Agent provider 不是 codex"],
                        suggestions=["检查 Codex Agent .env", "查看 Codex Agent 日志", "确认代码执行官在 A2A_BOTS 中"],
                        actions=[_action("view-agent-logs", "View Logs", log_component="codex-agent")],
                        relatedLogs=["codex-agent"],
                    )
                )

    codex_diag = data.get("codex_doctor", {})
    if codex_diag and not codex_diag.get("ok"):
        items.append(
            ExplainedDiagnosticItem(
                id="codex-doctor-error",
                level="warning",
                title="Codex Runtime 诊断未通过",
                affectedModules=["Codex Runtime"],
                status="需要检查",
                rawError=str(codex_diag.get("stderr") or codex_diag.get("stdout") or "codex doctor failed"),
                possibleCauses=["Codex CLI 配置异常", "Provider 配置不可用", "Codex 登录态或本机路径异常"],
                suggestions=["查看 Codex doctor 输出", "检查 Provider 设置", "查看 Codex Desktop 日志"],
                actions=[_action("view-codex-logs", "View Logs", log_component="codex-desktop")],
                relatedLogs=["codex-desktop", "control-center-api"],
            )
        )

    if not items:
        items.append(
            ExplainedDiagnosticItem(
                id="system-normal",
                level="normal",
                title="核心链路暂无异常",
                affectedModules=["Stack"],
                status="正常",
                rawError="",
                possibleCauses=[],
                suggestions=["继续观察 Operation Log 和组件日志"],
                actions=[_action("view-operations", "View Operations", log_component="operations")],
                relatedLogs=["operations"],
            )
        )
    return items
