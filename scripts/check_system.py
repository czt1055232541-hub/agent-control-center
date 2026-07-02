from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


def run(command: list[str], timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    payload = result.stdout or result.stderr or b""
    for encoding in ("utf-8", "gb18030", "mbcs"):
        try:
            return payload.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
        except LookupError:
            continue
    return payload.decode("utf-8", errors="replace").strip()


def wmic_value(alias: str, fields: list[str]) -> dict[str, str]:
    output = run(["wmic", alias, "get", ",".join(fields), "/format:csv"])
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        return {}
    header = [item.strip() for item in lines[0].split(",")]
    values = [item.strip() for item in lines[1].split(",")]
    return {key: values[index] if index < len(values) else "" for index, key in enumerate(header) if key != "Node"}


def free_space(path: str) -> int | None:
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def main() -> int:
    os_info = wmic_value("os", ["Caption", "BuildNumber", "OSArchitecture"])
    cpu_info = wmic_value(
        "cpu",
        ["VirtualizationFirmwareEnabled", "SecondLevelAddressTranslationExtensions"],
    )
    computer_info = wmic_value("computersystem", ["HypervisorPresent"])
    info = {
        "OS": os_info.get("Caption") or platform.platform(),
        "Build": os_info.get("BuildNumber") or platform.version(),
        "OSArch": os_info.get("OSArchitecture") or platform.machine(),
        "HyperV": computer_info.get("HypervisorPresent", ""),
        "VirtFW": cpu_info.get("VirtualizationFirmwareEnabled", ""),
        "SLAT": cpu_info.get("SecondLevelAddressTranslationExtensions", ""),
        "BuildOK": str(int(os_info.get("BuildNumber") or "0") >= 19041),
        "WSL_Status": run(["wsl", "--status"]),
        "Docker_Exists": str(Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe").exists()),
        "FreeSpace_E": free_space("E:\\"),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
