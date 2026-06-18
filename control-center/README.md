# Feishu Stack Control

Python-first control package for the local Feishu/Codex stack.

Install locally from this directory with:

```powershell
python -m pip install -e .[dev]
```

Run with:

```powershell
python -m feishu_stack.cli status --json
```

Run tests with:

```powershell
python -m pytest -q
```

Run the local FastAPI server and production GUI:

```powershell
E:\Python\python.exe -m uvicorn feishu_stack.app:app --host 127.0.0.1 --port 8765
```

Build the React/Tailwind GUI:

```powershell
cd web
npm install
npm run build
```

The GUI is served from `http://127.0.0.1:8765` after `web\dist` exists.

Local diagnostics include Codex doctor, MoonBridge models, Lark auth status, logs, and backup cleanup.

Desktop-friendly scripts:

```powershell
F:\1AI\feishu_agent\scripts\start-control-center.ps1
F:\1AI\feishu_agent\scripts\status-control-center.ps1
F:\1AI\feishu_agent\scripts\install-control-center-shortcut.ps1
```
