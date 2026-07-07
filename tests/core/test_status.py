from __future__ import annotations

from unittest.mock import patch

from feishu_stack.status import codex_desktop_status
from feishu_stack.core.status import _codex_desktop_status_from_process_rows


def test_codex_desktop_status_degrades_when_powershell_cannot_start() -> None:
    with patch("subprocess.run", side_effect=PermissionError("denied")):
        status = codex_desktop_status()

    assert status.running is False
    assert status.pid is None
    assert status.process_count == 0
    assert status.executable is None


def test_codex_desktop_status_detects_desktop_and_ignores_cli() -> None:
    status = _codex_desktop_status_from_process_rows(
        [
            {
                "Name": "codex.exe",
                "ProcessId": "10",
                "ExecutablePath": r"C:\Program Files\WindowsApps\OpenAI.Codex_1.0_x64__abc\app\resources\codex.exe",
            },
            {
                "Name": "Codex.exe",
                "ProcessId": "20",
                "ExecutablePath": r"C:\Program Files\WindowsApps\OpenAI.Codex_1.0_x64__abc\app\Codex.exe",
            },
            {
                "Name": "Codex.exe",
                "ProcessId": "21",
                "ExecutablePath": r"C:\Program Files\WindowsApps\OpenAI.Codex_1.0_x64__abc\app\Codex.exe",
            },
        ]
    )

    assert status.running is True
    assert status.pid == 20
    assert status.process_count == 2
    assert status.executable.endswith(r"\app\Codex.exe")
