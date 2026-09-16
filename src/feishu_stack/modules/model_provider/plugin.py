from __future__ import annotations

from fastapi import APIRouter
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from feishu_stack.api.operations import OperationRunner, operation_runner
from fastapi import Body, Depends
from pydantic import BaseModel
from feishu_stack.modules.model_provider import codex_agent, codex_desktop, provider_switch
from feishu_stack.modules.model_provider import openclaw_gateway as openclaw
from feishu_stack.modules.operations import stack_actions
from feishu_stack.core.settings import load_config
from feishu_stack.api.security import require_control_token

OPERATIONS_TAG = "Operations"
router = APIRouter()

class ProviderModelSwitchRequest(BaseModel):
    model: str
    reasoning_effort: str | None = None


@router.post("/api/openclaw/start", summary="Start OpenClaw", description="Start the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_openclaw(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("openclaw", "start", openclaw.start)


@router.post("/api/openclaw/stop", summary="Stop OpenClaw", description="Stop the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_openclaw(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("openclaw", "stop", openclaw.stop)


@router.post("/api/openclaw/restart", summary="Restart OpenClaw", description="Restart the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_openclaw(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("openclaw", "restart", openclaw.restart)


@router.post("/api/openclaw/open-ui", summary="Open OpenClaw UI", description="Open the OpenClaw web UI in the default browser.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def open_openclaw_ui(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("openclaw", "open-ui", openclaw.open_ui)


@router.get("/api/deepseek/available-models", summary="Available DeepSeek models", description="Return the configured direct DeepSeek models.", tags=[OPERATIONS_TAG])
def available_deepseek_models() -> dict:
    cfg = load_config()
    return {"models": cfg.deepseek.models}


@router.post("/api/codex-agent/start", summary="Start Codex Agent", description="Start the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_codex_agent(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-agent", "start", codex_agent.start)


@router.post("/api/codex-agent/stop", summary="Stop Codex Agent", description="Stop the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_codex_agent(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-agent", "stop", codex_agent.stop)


@router.post("/api/codex-agent/restart", summary="Restart Codex Agent", description="Restart the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_codex_agent(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-agent", "restart", codex_agent.restart)


@router.post("/api/codex-desktop/start", summary="Start Codex Desktop", description="Start the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_codex_desktop(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-desktop", "start", codex_desktop.start)


@router.post("/api/codex-desktop/stop", summary="Stop Codex Desktop", description="Stop the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_codex_desktop(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-desktop", "stop", codex_desktop.stop)


@router.post("/api/codex-desktop/restart", summary="Restart Codex Desktop", description="Restart the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_codex_desktop(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-desktop", "restart", codex_desktop.restart)


@router.post("/api/codex-provider/native", summary="Switch to native provider", description="Switch the codex provider to the native OpenAI backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_native(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-provider", "switch-native", lambda cfg: provider_switch.switch_provider("native", cfg, target="app"))


@router.post("/api/codex-provider/deepseek", summary="Switch to DeepSeek provider", description="Switch the codex provider to the direct DeepSeek Responses API backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_deepseek(request: ProviderModelSwitchRequest | None = Body(default=None), runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner(
        "codex-provider",
        "switch-deepseek",
        lambda cfg: provider_switch.switch_provider(
            "deepseek",
            cfg,
            deepseek_model=request.model if request else None,
            reasoning_effort=request.reasoning_effort if request else None,
            target="app",
        ),
    )


@router.post("/api/codex-provider/app/native", summary="Switch App to native provider", description="Switch the ChatGPT/Codex App provider to the native OpenAI backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_app_native(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-provider-app", "switch-native", lambda cfg: provider_switch.switch_provider("native", cfg, target="app"))


@router.post("/api/codex-provider/app/deepseek", summary="Switch App to DeepSeek provider", description="Switch the ChatGPT/Codex App provider to the direct DeepSeek Responses API backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_app_deepseek(request: ProviderModelSwitchRequest | None = Body(default=None), runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner(
        "codex-provider-app",
        "switch-deepseek",
        lambda cfg: provider_switch.switch_provider(
            "deepseek",
            cfg,
            deepseek_model=request.model if request else None,
            reasoning_effort=request.reasoning_effort if request else None,
            target="app",
        ),
    )


@router.post("/api/codex-provider/agent/native", summary="Switch Agent to native provider", description="Switch the Feishu Codex Agent provider to the native OpenAI backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_agent_native(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("codex-provider-agent", "switch-native", lambda cfg: stack_actions.switch_agent_provider("native", cfg))


@router.post("/api/codex-provider/agent/deepseek", summary="Switch Agent to DeepSeek provider", description="Switch the Feishu Codex Agent provider to the direct DeepSeek Responses API backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_agent_deepseek(request: ProviderModelSwitchRequest | None = Body(default=None), runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner(
        "codex-provider-agent",
        "switch-deepseek",
        lambda cfg: stack_actions.switch_agent_provider(
            "deepseek",
            cfg,
            deepseek_model=request.model if request else None,
            reasoning_effort=request.reasoning_effort if request else None,
        ),
    )


@router.post("/api/stack/start-native", summary="Start stack (native)", description="Start the full stack using the native OpenAI provider.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_start_native(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("stack", "start-native", stack_actions.start_native)


@router.post("/api/stack/start-deepseek", summary="Start stack (DeepSeek)", description="Start the full stack using the direct DeepSeek provider.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_start_deepseek(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("stack", "start-deepseek", stack_actions.start_deepseek)


@router.post("/api/stack/stop", summary="Stop stack", description="Stop all stack components (openclaw, codex-agent).", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_stop(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("stack", "stop", stack_actions.stop)

def create_plugin() -> AccPlugin:
    return AccPlugin(id='acc.model-provider', name='模型与 Provider', version='1.0.0', description='模型与 Provider', requires=('acc.framework',), capabilities=('providers.manage',), cards=(PluginCard('acc.model-provider.overview', '模型与 Provider', '模型与 Provider', 'provider', icon='server-cog', order=50),), router_factory=lambda: router)
