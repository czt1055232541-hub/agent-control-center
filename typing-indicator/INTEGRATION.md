# Codex Desktop App — Typing Indicator 集成指南

## 文件位置
- 主脚本: `F:\1AI\Agent control center\typing-indicator\typing-indicator.py`
- 启动器: `F:\1AI\Agent control center\typing-indicator\launcher.py`  ← **不改源码用这个**
- 依赖: Python 3.11+, `E:\Python\python.exe`, `psutil`
- lark-cli: `F:\1AI\feishu_agent\.npm-global\node_modules\@larksuite\cli\bin\lark-cli.exe`
- 集成模块: `F:\1AI\Agent control center\src\feishu_stack\typing_indicator.py`

## 方案 A：不改 App 源码 — 用 launcher.py（推荐）

`launcher.py` 独立运行，自动发现 codex bus 进程，然后启动 typing indicator。
bus 死了它也跟着停，typing indicator 崩了它自动重启（最多 5 次）。

```batch
:: 启动（在 codex 栈启动后运行一次即可）
E:\Python\python.exe -m feishu_stack.cli start typing-indicator

:: 或者随整体 stack 启动（start-all.ps1 已内置）
E:\Python\python.exe -m feishu_stack.cli stack start-native
```

已深度集成到 Agent Control Center，随 stack 生命周期自动管理，不需要手动启停。

## 方案 B：集成到 Codex Desktop App 源码

在 Codex Desktop App 启动时，和其他 lark-cli 子进程一起启动 typing-indicator.py。
App 退出时，Kill 整个进程树。

### C# 启动代码

```csharp
using System.Diagnostics;

// 成员变量
private Process _typingIndicator;

// 启动 — 加在现有的 lark-cli bus/consumer 启动代码旁边
private void StartTypingIndicator()
{
    _typingIndicator = new Process
    {
        StartInfo = new ProcessStartInfo
        {
            FileName = @"E:\Python\python.exe",
            Arguments = @"F:\1AI\Agent control center\typing-indicator\launcher.py",
            WorkingDirectory = @"F:\1AI\Agent control center\typing-indicator",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        },
        EnableRaisingEvents = true
    };

    _typingIndicator.Start();
    _typingIndicator.BeginOutputReadLine();
    _typingIndicator.BeginErrorReadLine();
}

// 退出 — 加在 App 退出/Dispose 逻辑里
private void StopTypingIndicator()
{
    try
    {
        if (_typingIndicator != null && !_typingIndicator.HasExited)
        {
            _typingIndicator.Kill(entireProcessTree: true);
            _typingIndicator.Dispose();
        }
    }
    catch { /* already exited */ }
}
### 进程关系（启动后）

```
Agent Control Center (stack_actions.py / CLI)
├── openclaw-gateway
├── moonbridge
├── codex-agent         (lark-cli bus + consumer)
├── codex-desktop       (WPF app)
└── typing-indicator    (typing_indicator.py 集成模块)
    └── launcher.py     (PID 32496)
        └── typing-indicator.py
            └── lark-cli consumer  ← 监听 im.message.receive_v1
```

- stack start-native → 依次启动所有组件 → typing indicator 最后拉起
- bus 崩溃 → launcher 检测到 → kill typing-indicator → launcher 退出
- stack stop → 通过 CLI 统一停止 → launcher → typing-indicator → consumer 全清

### 行为
收到 codex bot 的消息 → POST typing reaction → "正在输入…"显示 → 60s 后自动 DELETE
