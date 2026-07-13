"""Compatibility import for the API application.

New code should import :mod:`feishu_stack.api.app`.  This module remains as a
thin forwarding shim while existing launch commands and tests migrate.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "feishu_stack.app is deprecated; import feishu_stack.api.app instead",
    DeprecationWarning,
    stacklevel=2,
)

from feishu_stack.api.app import *  # noqa: F401,F403,E402
