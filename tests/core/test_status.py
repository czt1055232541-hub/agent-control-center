from __future__ import annotations

from unittest.mock import patch

from feishu_stack.status import codex_desktop_status


def test_codex_desktop_status_degrades_when_powershell_cannot_start() -> None:
    with patch("subprocess.run", side_effect=PermissionError("denied")):
        status = codex_desktop_status()

    assert status.running is False
    assert status.pid is None
    assert status.process_count == 0
    assert status.executable is None
