# Feishu Codex Stack

This private stack keeps the local Feishu agents, Codex provider switching tools, and service scripts in one repository.

`E:\codeX` remains the real `CODEX_HOME`. This repository only manages scripts and agent source code.

Python is the source of truth for stack control. PowerShell files are compatibility wrappers for double-click and legacy paths.

## Common Commands

```powershell
.\scripts\status-all.ps1
.\scripts\start-all.ps1 -CodexMode native
.\scripts\start-all.ps1 -CodexMode moonbridge
.\scripts\stop-all.ps1
.\codex\Switch-CodexProvider.ps1 -Mode native
.\codex\Switch-CodexProvider.ps1 -Mode moonbridge
.\codex\Restore-CodexNative.ps1
```

Use the scripts under `scripts/` as the compatibility wrappers. The old root-level wrappers were removed during cleanup.

Preferred Python flow:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli stack start-moonbridge
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
E:\Python\python.exe -m feishu_stack.cli backups clean
```

## Control Center

Install/update the Python control package:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m pip install -e .[dev]
```

Run the local API and production GUI:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m uvicorn feishu_stack.app:app --host 127.0.0.1 --port 8765
```

Or use the desktop-friendly wrapper:

```powershell
.\scripts\start-control-center.ps1
.\scripts\status-control-center.ps1
.\scripts\install-control-center-shortcut.ps1
```

Open:

```text
http://127.0.0.1:8765
```

For frontend development:

```powershell
cd F:\1AI\feishu_agent\control-center\web
npm install
npm run dev
```

## GitHub

Private repository:

```text
git@github.com:czt1055232541-hub/feishu-codex-stack.git
```

Normal update flow:

```powershell
git status
git add -A
git commit -m "Describe the change"
git push
```

## Layout

- `control-center/`: Python control package, FastAPI API, tests, and React/Tailwind GUI source
- `agents/`: Feishu Codex Agent and OpenClaw Feishu bot plugin source
- `scripts/`: compatibility wrappers and desktop entry scripts
- `codex/`: compatibility wrappers plus thread migration/test tools
- `config/`: stack settings and legacy PowerShell path definitions
- `docs/`: architecture, provider switching, and recovery notes
- `runtime/`: ignored local logs, PID files, and local control token
- `.npm-global/`: ignored local Lark CLI install used by the agent
- `.home/`: ignored local Lark/OpenClaw auth state

## Planning Docs

- [Python-first GUI Control Center Plan](docs/gui-control-center-plan.md)
