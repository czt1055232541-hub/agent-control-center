"""Host-neutral operation execution dependency for feature routers."""

from typing import Callable

from fastapi import Request

from feishu_stack.core.models import OperationResult, to_dict
from feishu_stack.core.settings import StackConfig
from feishu_stack.core.operations import run_exclusive


OperationRunner = Callable[[str, str, Callable[[StackConfig], OperationResult]], dict]


def run_operation(component: str, action: str, fn: Callable[[StackConfig], OperationResult]) -> dict:
    """Use the same operation lock and audit trail in standalone plugin hosts."""
    return to_dict(run_exclusive(component, action, fn))


def operation_runner(request: Request) -> OperationRunner:
    """Allow the host to add notifications without importing it from a plugin."""
    return getattr(request.app.state, "operation_runner", run_operation)
