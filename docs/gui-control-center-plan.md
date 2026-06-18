# Agent Control Center Independence Plan

Last updated: 2026-06-19

## Current State

Agent Control Center is now an independent local desktop control project at:

```text
F:\1AI\Agent control center
```

It owns:

- Python control package and CLI;
- FastAPI local API;
- React/Tailwind GUI;
- diagnostics and log access;
- local control center runtime logs, PID files, and token;
- desktop-friendly PowerShell wrappers.

The Feishu-specific agent repository remains at:

```text
F:\1AI\feishu_agent
```

That repository should focus on Feishu Codex Agent source, OpenClaw/Feishu connection files, compatibility wrappers, and recovery notes.

## Target Architecture

- Agent Control Center is the machine-level operations console.
- Feishu Codex Agent remains a managed component, not the owner of the control console.
- Python remains the source of truth for control behavior.
- PowerShell remains only for double-click usage and legacy wrappers.
- Runtime files live under `F:\1AI\Agent control center\runtime`.
- Feishu agent source remains under `F:\1AI\feishu_agent\agents`.
- Codex home remains `E:\codeX`.
- OpenClaw home remains `E:\openclaw\clawclaw`.

## Migration Phases

### Phase A: Repository Split

- Move the Python/API/GUI control project to `F:\1AI\Agent control center`.
- Create private GitHub repository `czt1055232541-hub/agent-control-center`.
- Keep `czt1055232541-hub/feishu-codex-stack` for Feishu agent configuration and compatibility wrappers.

### Phase B: Path Rebinding

- Update `config\stack.settings.json` so `stackRoot` and runtime paths point to `F:\1AI\Agent control center`.
- Keep managed component paths pointing at their real locations.
- Update control center start/status/shortcut logic to use the new project root.

### Phase C: Compatibility Wrappers

In `F:\1AI\feishu_agent`, keep thin wrappers only:

- `scripts\start-all.ps1`
- `scripts\stop-all.ps1`
- `scripts\status-all.ps1`
- `scripts\start-control-center.ps1`
- `scripts\stop-control-center.ps1`
- `scripts\status-control-center.ps1`
- `scripts\install-control-center-shortcut.ps1`
- `codex\Switch-CodexProvider.ps1`
- `codex\Restore-CodexNative.ps1`
- `codex\Clean-CodexBackups.ps1`
- `codex\Get-CodexProviderStatus.ps1`

These wrappers call:

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m feishu_stack.cli ...
```

### Phase D: Future Cleanup

- Rename the internal Python package from `feishu_stack` to a neutral package name only after wrappers and tests are stable.
- Split GUI `main.tsx` into smaller modules.
- Keep dangerous Codex Desktop stop/restart actions explicit and manually confirmed.

## Compatibility Rules

- Existing Feishu wrapper paths remain callable.
- Agent Control Center does not own or move Feishu agent source.
- `stack stop` does not stop Codex Desktop.
- Codex Desktop stop/restart is isolated and not executed in automated validation.
- Git repositories must not commit runtime logs, PID files, local tokens, SQLite files, secrets, QR codes, or dependency folders.

## Test Plan

Python tests:

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m pytest -q
```

Frontend build:

```powershell
cd "F:\1AI\Agent control center\web"
npm run build
```

CLI smoke:

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli status-control-center
```

Wrapper syntax:

```powershell
[scriptblock]::Create((Get-Content "F:\1AI\Agent control center\scripts\start-control-center.ps1" -Raw))
[scriptblock]::Create((Get-Content "F:\1AI\feishu_agent\scripts\start-all.ps1" -Raw))
[scriptblock]::Create((Get-Content "F:\1AI\feishu_agent\codex\Switch-CodexProvider.ps1" -Raw))
```

GitHub checks:

- `git status --short` is clean in both repositories after commits.
- `gh repo view czt1055232541-hub/agent-control-center` succeeds.
- `gh repo view czt1055232541-hub/feishu-codex-stack` succeeds.

## Operational Usage

Start GUI:

```powershell
F:\1AI\Agent control center\scripts\start-control-center.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Legacy Feishu wrappers still work:

```powershell
F:\1AI\feishu_agent\scripts\start-all.ps1 -CodexMode moonbridge
F:\1AI\feishu_agent\scripts\stop-all.ps1
F:\1AI\feishu_agent\codex\Switch-CodexProvider.ps1 -Mode native
```
