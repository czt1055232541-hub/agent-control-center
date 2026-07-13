# Recovery

Codex Desktop is not stopped by this stack.

To force Codex back to Native OpenAI mode:

```bash
python scripts/stack.py switch-provider native
```

The provider switch writes `E:\codeX\config.toml`, verifies `model = "gpt-5.5"`, removes MoonBridge provider fields, and keeps only the newest switch backup.

To inspect current provider state:

```bash
python scripts/stack.py status --json
```

To stop managed services without touching Codex Desktop:

```bash
python scripts/stack.py stack stop
```

If OpenClaw does not stop by PID, stop its gateway directly:

```bash
python scripts/stack.py stop openclaw
```
