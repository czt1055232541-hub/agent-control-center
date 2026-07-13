# Recovery

Codex Desktop is not stopped by this stack.

To force Codex back to Native OpenAI mode:

```bash
python F:\1AI\feishu_agent\codex\switch_provider.py native
```

The provider switch writes `E:\codeX\config.toml`, verifies `model = "gpt-5.5"`, removes MoonBridge provider fields, and keeps only the newest switch backup.

To inspect current provider state:

```bash
python F:\1AI\feishu_agent\codex\provider_status.py --json
```

To stop managed services without touching Codex Desktop:

```bash
python F:\1AI\feishu_agent\scripts\stack.py stack stop
```

If OpenClaw does not stop by PID, stop its gateway directly:

```bash
python F:\1AI\feishu_agent\scripts\stack.py stop openclaw
```
