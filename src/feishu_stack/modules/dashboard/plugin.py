from __future__ import annotations

from fastapi import APIRouter
from feishu_stack.core.models import to_dict
from feishu_stack.core.status import get_status
from feishu_stack.modules.operations.operations import recent_operations
from feishu_stack.modules.agent_array.skill_tree import agent_dashboard
from feishu_stack.plugin_sdk import AccPlugin, PluginCard

STATUS_TAG = DASHBOARD_TAG = 'Dashboard'
router = APIRouter()

@router.get(
    "/api/status",
    summary="Stack status",
    description="Return the full stack status: openclaw, codex-agent, "
    "codex-desktop, and provider info.",
    tags=[STATUS_TAG],
)
def status() -> dict:
    return to_dict(get_status())


@router.get(
    "/api/operations",
    summary="Recent operations",
    description="Return the most recent control operations and their outcomes.",
    tags=[STATUS_TAG],
)
def operations() -> dict:
    return {"operations": to_dict(recent_operations())}


@router.get(
    "/api/dashboard/summary",
    summary="Dashboard summary",
    description="Return the command dashboard top-level health and activity counters.",
    tags=[DASHBOARD_TAG],
)
def dashboard_summary() -> dict:
    return to_dict(agent_dashboard.dashboard_summary())


@router.get(
    "/api/infrastructure",
    summary="Infrastructure inventory",
    description="Return the real backend services that carry the agent roles.",
    tags=[DASHBOARD_TAG],
)
def infrastructure() -> dict:
    return {"agents": to_dict(agent_dashboard.list_infrastructure())}

def create_plugin() -> AccPlugin:
    return AccPlugin(id='acc.dashboard', name='Dashboard 总览', version='1.0.0', description='运行状态与关键指标总览。', requires=('acc.framework',), capabilities=('dashboard.read',), cards=(PluginCard('acc.dashboard.overview', 'Dashboard 总览', '运行状态与关键指标总览。', 'dashboard', icon='layout-dashboard', order=10),), router_factory=lambda: router)
