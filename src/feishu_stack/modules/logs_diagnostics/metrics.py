"""Compatibility alias for framework-owned metrics; preserves one registry."""
import sys
from feishu_stack.core import metrics as _metrics
sys.modules[__name__] = _metrics
