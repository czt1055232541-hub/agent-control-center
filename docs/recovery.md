# Recovery

Codex Desktop is not stopped by this stack.

To force Codex back to Native OpenAI mode:

```powershell
powershell -ExecutionPolicy Bypass -File F:\1AI\feishu_agent\codex\Restore-CodexNative.ps1
```

The restore script writes `E:\codeX\config.toml`, verifies `model = "gpt-5.5"`, removes MoonBridge provider fields, and keeps only the newest `config.toml.bak-restore-native-*` backup.

To inspect current provider state:

```powershell
powershell -ExecutionPolicy Bypass -File F:\1AI\feishu_agent\codex\Get-CodexProviderStatus.ps1
```

To stop managed services without touching Codex Desktop:

```powershell
powershell -ExecutionPolicy Bypass -File F:\1AI\feishu_agent\scripts\stop-all.ps1
```

If OpenClaw does not stop by PID, stop its gateway directly:

```powershell
$env:OPENCLAW_HOME="E:\openclaw\clawclaw"
openclaw.cmd gateway stop
```
