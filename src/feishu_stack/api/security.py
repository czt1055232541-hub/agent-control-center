from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Header, HTTPException

from feishu_stack.core.settings import StackConfig, load_config


def token_path(config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    return cfg.runtime_dir / "control-token.txt"


def get_or_create_token(config: StackConfig | None = None) -> str:
    path = token_path(config)
    if path.exists():
        token = path.read_text(encoding="ascii").strip()
        if token:
            return token
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    path.write_text(token, encoding="ascii")
    return token


def require_control_token(x_control_token: str | None = Header(default=None)) -> None:
    expected = get_or_create_token()
    if not x_control_token:
        raise HTTPException(status_code=401, detail="Missing X-Control-Token header.")
    if not secrets.compare_digest(x_control_token, expected):
        raise HTTPException(status_code=403, detail="Invalid X-Control-Token header.")
