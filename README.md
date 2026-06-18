# Feishu Codex Stack

This private stack keeps the local Feishu agents, Codex provider switching tools, and service scripts in one repository.

`E:\codeX` remains the real `CODEX_HOME`. This repository only manages scripts and agent source code.

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

Root `start-all.ps1` and `stop-all.ps1` are compatibility wrappers.

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

- `config/`: shared paths and stack settings
- `scripts/`: start, stop, and status scripts
- `codex/`: provider switching, backup cleanup, and thread migration tools
- `agents/`: Feishu Codex agent and OpenClaw Feishu bot plugin source
- `docs/`: provider switching and recovery notes

## Planning Docs

- [Python-first GUI Control Center Plan](docs/gui-control-center-plan.md)
