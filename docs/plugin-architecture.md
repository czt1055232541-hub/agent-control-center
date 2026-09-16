# ACC 插件架构与 DSH 接入方案

## 目标状态

ACC 只保留插件发现、依赖解析、生命周期、配置、安全与 UI 贡献协议。Agent 阵列、任务战场、飞书连接、模型 Provider、本地工具、配置中心、日志诊断和备份迁移均作为功能插件存在。DSH 不修改源码，只安装一个树外 `dsh-plugin-acc` bundle。

```text
ACC feature plugins ─┐
external ACC plugins ├─> ACC plugin runtime ─> HTTP/Remote adapter ─> DSH host plugin
ACC built-ins ───────┘                                      │
                                                           └─> DSH client card
```

## 插件边界

公共 Python 协议位于 `feishu_stack.plugin_sdk`，运行时位于 `feishu_stack.plugin_runtime`。外部发行包通过 `agent_control_center.plugins` entry-point 提供一个 `AccPlugin` 或返回它的无参 factory。插件可以贡献：

- `router_factory`：按需创建 FastAPI `APIRouter`；
- `capabilities`：供 ACC、DSH 与其他宿主发现的稳定能力名；
- `cards`：宿主无关的卡片元数据；
- `requires`：其他 ACC 插件 id，运行时在挂载前校验并拓扑排序。

插件包示例：

```toml
[project.entry-points."agent_control_center.plugins"]
example = "acc_example:create_plugin"
```

```python
from fastapi import APIRouter
from feishu_stack.plugin_sdk import AccPlugin, PluginCard

def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/example", tags=["Example"])
    return router

def create_plugin() -> AccPlugin:
    return AccPlugin(
        id="example.feature",
        name="Example",
        version="1.0.0",
        description="Example feature",
        capabilities=("example.read",),
        cards=(PluginCard("example.overview", "Example", "Open Example", "example"),),
        router_factory=create_router,
    )
```

## 兼容迁移

当前内置功能均已进入插件清单，使 ACC 和 DSH 可以发现它们。配置中心、路由规则和飞书连接已由各自的原生插件挂载路由；其余功能仍标记为 `transitional`，原路由暂时保留在 `api/app.py`，避免一次迁移破坏现有入口。迁移每个剩余功能时执行：

1. 将请求模型和路由移动到所属 `modules/<功能域>/router.py`；
2. 给该功能插件设置惰性 `router_factory` 并把状态改为 `native`；
3. 前端页面导出 `AccClientPlugin`，不再由 `main.tsx` 和 `Sidebar.tsx` 直接导入；
4. 删除原单体路由，仅保留已有公开路径；
5. 运行功能测试、完整 Python 测试和 Web build。

旧的 `feishu_stack/*.py` 导入 wrapper 和现有 CLI 在迁移期间保持可用。

## DSH 适配

`dsh-plugin-acc` 是独立仓库或独立 npm 包，不进入 DSH 源码：

- Host 插件连接 ACC 的 loopback API，注册 `acc_list_plugins`、`acc_get_status` 和按 capability 生成的工具；
- Client 插件为这些 wire 工具名注册 `tool.call.toolview`，使用 DSH 主题变量渲染可点击卡片；
- 卡片点击后打开 DSH 右侧栏的 ACC 详情资源；完整 ACC 控制台仍可独立运行；
- ACC 不可用时插件返回结构化离线状态，不影响 DSH 启动和其他工具；
- bundle 通过 `dsh plugin --profile web add <package>` 安装，通过移除 bundle 完整回退。

DSH 适配器只依赖 `/api/plugins` 与后续稳定的 `/api/integrations/dsh/*`，不得 import ACC 源码或依赖 ACC 私有文件结构。

## 阶段验收

1. 插件内核：依赖顺序、重复 id、缺失依赖、循环依赖、惰性路由和清单 API 均有测试。
2. 内置迁移：所有功能插件状态从 `transitional` 变为 `native`，`api/app.py` 不再导入业务模块。
3. 前端迁移：导航和页面来自插件注册表，禁用某插件会同时移除页面和菜单卡片。
4. DSH：DSH 仓库无源码 diff；ACC 在线、离线、禁用和卸载场景均验证；专属卡片通过 Client 构建和浏览器检查。
