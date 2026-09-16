# ACC 插件架构与 DSH 接入

## 目标

ACC 是轻量宿主：只负责插件发现、依赖排序、生命周期、配置、安全边界和 UI 投影。业务能力全部以插件贡献；DSH 只安装仓库外的 `dsh-plugin-acc`，不修改 DSH 源码。

```text
ACC 内建插件 ─┐
ACC 外部插件 ─┼─> ACC plugin runtime ─> /api/plugins ─> dsh-plugin-acc ─> DSH 原生卡片
未来功能插件 ─┘                              └──────────────> ACC Web 导航
```

## 插件契约

公开 Python 契约位于 `feishu_stack.plugin_sdk`，运行时位于 `feishu_stack.plugin_runtime`。外部发行包通过 `agent_control_center.plugins` entry point 返回 `AccPlugin` 或无参数 factory。

- `router_factory`：延迟创建 FastAPI `APIRouter`；
- `capabilities`：跨 ACC/DSH 使用的稳定能力标识；
- `cards`：与宿主无关的可点击卡片元数据；
- `requires`：依赖的插件 ID，挂载前进行缺失和循环校验。

```toml
[project.entry-points."agent_control_center.plugins"]
example = "acc_example:create_plugin"
```

```python
from fastapi import APIRouter
from feishu_stack.plugin_sdk import AccPlugin, PluginCard

def create_router() -> APIRouter:
    return APIRouter(prefix="/api/example", tags=["Example"])

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

## 内建功能迁移

十个内建功能都有路由贡献。配置中心、路由规则、飞书连接和任务战场在独立模块中直接定义路由，状态为 `native`；其余六个仍为 `transitional`，原有端点通过 `builtin_routers.adopt_builtin_feature_routes` 兼容层转移到插件路由，再由插件注册表统一挂载。旧 API 路径不变。过渡模块只完成路由挂载归属，业务实现仍在核心应用中，不代表插件化验收完成。

兼容层只服务于现有实现的渐进式拆分。新增功能不得在 `api/app.py` 注册业务端点，必须在独立插件包中定义路由、卡片与能力。后续可逐模块把兼容层内的处理函数移动到 `modules/<feature>/plugin.py`，无需再次改变外部 API 或 DSH 适配器。

最终核心宿主应只保留会话、健康检查、框架清单、异常处理、静态页面和宿主关停职责。当前核心仍含业务处理函数和业务 WebSocket，需继续迁移。

## DSH 适配器

`integrations/dsh-plugin-acc` 是独立 npm bundle：

- 通过 `dsh plugin --profile web add <tarball>` 安装；
- Host 注册 `acc_overview`，只读取 ACC 的 loopback `/api/plugins`；
- Client 在 `tool.call.toolview` 插槽渲染 DSH 风格的可点击卡片；
- 在线时点击卡片打开 ACC，离线时返回结构化降级状态，不影响 DSH 主体启动和使用；
- DSH 只依赖公开 HTTP 清单，不 import ACC 源码或私有文件。

未来新增 ACC 插件后，清单、ACC 导航和 DSH 概览卡片会自动出现，无需修改 DSH 或重新编译其源码。只有在需要把某项 ACC 能力直接暴露为 DSH 工具时，才扩展稳定的 capability 调用协议；不能让 DSH 直接依赖业务插件实现。

## 发布与回退

每个阶段执行 Python 全量测试、Web 构建、集成包语法/打包检查、真实 DSH 启动检查及新增行隐私扫描。阶段提交推送到 `develop`，以语义化标签形成回退点；改造前远端备份分支为 `backup/pre-plugin-0.3.0-20260916`。
