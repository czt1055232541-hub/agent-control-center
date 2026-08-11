# ACC 本地工具接入约定

ACC 通过 `localTools.tools` 注册本机小工具，统一提供状态查看、启动、停止、重启、日志读取和 iframe 内嵌。日历工具可以作为标准样例放在 `TOOLS/calendar-tool`。

## 工具端 manifest

工具目录可放置 `acc.local-tool.json`，ACC 会先读取 manifest，再用 `config/stack.settings.local.json` 中的同名字段覆盖。推荐日历工具 manifest：

```json
{
  "id": "calendar-tool",
  "name": "日历工具",
  "description": "本地日历、待办、倒计时和甘特图工具。",
  "runtime": "python",
  "entry": "app.py",
  "host": "127.0.0.1",
  "port": 8010,
  "healthPath": "/api/health",
  "openPath": "/",
  "embed": true,
  "tags": ["calendar", "planning", "local"],
  "env": {
    "CALENDAR_DATA_DIR": "data"
  }
}
```

## ACC 侧配置

真实路径写入 `config/stack.settings.local.json`：

```json
{
  "localTools": {
    "tools": [
      {
        "dir": "C:\\path\\to\\agent-control-center\\TOOLS\\calendar-tool",
        "manifest": "acc.local-tool.json",
        "port": 8010
      }
    ]
  }
}
```

配置文件中的字段优先级高于 manifest，适合在不同电脑上覆盖端口、路径、URL 或是否启用。

也可以直接在 ACC 前端完成注册：

1. 打开“本地工具中心”。
2. 点击“选择注册文档”，选择工具目录中的 `acc.local-tool.json` 或 `local-tool.json`。
3. ACC 会解析注册预览；如果注册文档没有 `dir`，补充工具所在文件夹路径。
4. 点击“注册到 ACC”，工具会写入本机 `stack.settings.local.json` 并出现在工具列表。

“扫描”按钮会查找 `{ACC_ROOT}/TOOLS`、`{ACC_ROOT}/tools`、`{ACC_ROOT}/projects` 和配置中的 `projectsRoot`，发现带注册文档或默认入口的候选工具。

## 工具代码适配

工具启动后可读取 ACC 注入的环境变量：

| 变量 | 含义 |
|---|---|
| `ACC_TOOL_ID` | 工具 ID，例如 `calendar-tool` |
| `ACC_TOOL_NAME` | 工具显示名 |
| `ACC_TOOL_HOST` | 监听 host |
| `ACC_TOOL_PORT` | 监听端口 |
| `ACC_TOOL_URL` | ACC 认为的访问基址 |
| `ACC_TOOL_DIR` | 工具目录 |
| `ACC_TOOL_ENTRY` | 工具入口文件 |

日历工具应监听 `ACC_TOOL_HOST` / `ACC_TOOL_PORT`，并提供 `healthPath` 指定的健康检查端点。网页若需要被 ACC 内嵌，应允许来自 `127.0.0.1` 的 iframe 访问。
