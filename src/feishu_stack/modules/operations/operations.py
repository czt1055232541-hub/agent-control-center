"""Compatibility alias preserving the framework operation lock and history."""
import sys
from feishu_stack.core import operations as _operations
sys.modules[__name__] = _operations
