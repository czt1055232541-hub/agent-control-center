# Feishu Codex Agent Stack

This repository now focuses on the Feishu-side agent source and local connection configuration.

The machine-level operations console has been split into a separate project:

```text
F:\1AI\Agent control center
git@github.com:czt1055232541-hub/agent-control-center.git
```

`E:\codeX` remains the real `CODEX_HOME`. `E:\openclaw\clawclaw` remains the real OpenClaw home.

## Common Commands

Compatibility wrappers are still available here:

```powershell
.\scripts\status-all.ps1
.\scripts\start-all.ps1 -CodexMode native
.\scripts\start-all.ps1 -CodexMode moonbridge
.\scripts\stop-all.ps1
.\codex\Switch-CodexProvider.ps1 -Mode native
.\codex\Switch-CodexProvider.ps1 -Mode moonbridge
.\codex\Restore-CodexNative.ps1
```

Those wrappers delegate to the independent Agent Control Center project.

Preferred direct control path:

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli stack start-moonbridge
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
E:\Python\python.exe -m feishu_stack.cli backups clean
```

## Layout

- `agents/`: Feishu Codex Agent and OpenClaw Feishu bot plugin source
- `scripts/`: compatibility wrappers that call Agent Control Center
- `codex/`: compatibility wrappers plus thread migration/test tools
- `config/`: Feishu stack path definitions and local settings
- `docs/`: provider switching and recovery notes
- `runtime/`: ignored local logs and PID files kept for legacy compatibility
- `.npm-global/`: ignored local Lark CLI install used by the agent
- `.home/`: ignored local Lark/OpenClaw auth state

## GitHub

Private repository:

```text
git@github.com:czt1055232541-hub/feishu-codex-stack.git
```
