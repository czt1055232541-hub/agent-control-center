# Agent Control Center Independence Plan

Last updated: 2026-06-19

## Current State

Agent Control Center is now an independent local desktop control project at:

```text
C:\agent-control-center
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
C:\feishu_agent
```

That repository should focus on Feishu Codex Agent source, OpenClaw/Feishu connection files, compatibility wrappers, and recovery notes.

## Target Architecture

- Agent Control Center is the machine-level operations console.
- Feishu Codex Agent remains a managed component, not the owner of the control console.
- Python remains the source of truth for control behavior.
- PowerShell remains only for double-click usage and legacy wrappers.
- Runtime files live under `C:\agent-control-center\runtime`.
- Thread migration summaries live under `C:\agent-control-center\runtime\summaries`.
- Feishu agent source remains under `C:\feishu_agent\agents`.
- Codex home remains `C:\Users\you\.codex`.
- OpenClaw home remains `C:\openclaw`.

## Migration Phases

### Phase A: Repository Split

- Move the Python/API/GUI control project to `C:\agent-control-center`.
- Create private GitHub repository `czt1055232541-hub/agent-control-center`.
- Keep `czt1055232541-hub/feishu-codex-stack` for Feishu agent configuration and compatibility wrappers.

### Phase B: Path Rebinding

- Update `config\stack.settings.json` so `stackRoot` and runtime paths point to `C:\agent-control-center`.
- Keep managed component paths pointing at their real locations.
- Update control center start/status/shortcut logic to use the new project root.
- Keep generated migration summaries, import prompts, and rollout excerpts in `runtime\summaries`, not `runtime\logs`.

### Phase C: Compatibility Wrappers

In `C:\feishu_agent`, keep thin wrappers only:

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
cd "C:\agent-control-center"
python -m feishu_stack.cli ...
```

### Phase D: Future Cleanup

- Rename the internal Python package from `feishu_stack` to a neutral package name only after wrappers and tests are stable.
- Split GUI `main.tsx` into smaller modules.
- Keep dangerous Codex Desktop stop/restart actions explicit and manually confirmed.

### Phase E: Project Closeout Hygiene

After a feature round is functionally complete:

- run the Python tests and frontend build before deleting anything;
- inspect generated artifacts under `runtime\logs`, `runtime\pids`, `runtime\summaries`, `.pytest_cache`, `web\dist`, and `web\node_modules`;
- keep source tests under `tests\` when they cover active behavior;
- delete only redundant generated test outputs, caches, stale logs, temporary migration summaries, and obsolete manual smoke files;
- do not delete regression tests merely because the feature is complete;
- run `git status --short` after cleanup and verify no runtime or secret files are staged.

## Compatibility Rules

- Existing Feishu wrapper paths remain callable.
- Agent Control Center does not own or move Feishu agent source.
- `stack stop` does not stop Codex Desktop.
- Codex Desktop stop/restart is isolated and not executed in automated validation.
- Git repositories must not commit runtime logs, PID files, local tokens, SQLite files, secrets, QR codes, or dependency folders.
- Runtime summaries are user-facing generated artifacts. They are kept locally under `runtime\summaries` and are excluded from Git except for `.gitkeep`.

## Test Plan

Python tests:

```powershell
cd "C:\agent-control-center"
python -m pytest -q
```

Frontend build:

```powershell
cd "C:\agent-control-center\web"
npm run build
```

CLI smoke:

```powershell
cd "C:\agent-control-center"
python -m feishu_stack.cli status --json
python -m feishu_stack.cli status-control-center
```

Thread migration smoke:

```powershell
cd "C:\agent-control-center"
python -m feishu_stack.cli migrate-thread --session-id <session-id> --target-provider moonbridge --json
```

Expected summary output directory:

```text
C:\agent-control-center\runtime\summaries
```

Wrapper syntax:

```powershell
[scriptblock]::Create((Get-Content "C:\agent-control-center\scripts\start-control-center.ps1" -Raw))
[scriptblock]::Create((Get-Content "C:\feishu_agent\scripts\start-all.ps1" -Raw))
[scriptblock]::Create((Get-Content "C:\feishu_agent\codex\Switch-CodexProvider.ps1" -Raw))
```

GitHub checks:

- `git status --short` is clean in both repositories after commits.
- `gh repo view czt1055232541-hub/agent-control-center` succeeds.
- `gh repo view czt1055232541-hub/feishu-codex-stack` succeeds.

## Operational Usage

Start GUI:

```powershell
C:\agent-control-center\scripts\start-control-center.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Legacy Feishu wrappers still work:

```powershell
C:\feishu_agent\scripts\start-all.ps1 -CodexMode moonbridge
C:\feishu_agent\scripts\stop-all.ps1
C:\feishu_agent\codex\Switch-CodexProvider.ps1 -Mode native
```

