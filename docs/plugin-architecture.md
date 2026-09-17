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

十个内建功能均在独立模块中直接定义请求模型和路由，状态为 `native`，由插件注册表统一挂载。Agent 技能辅助函数随 Agent 插件迁移；Codex 流 WebSocket 随日志诊断插件迁移。旧 API 路径不变，临时 `builtin_routers` 转交层已删除。原生路由状态证明路由归属已拆分，不代表前端注册和生命周期验收完成。

需要执行受控操作的插件通过 `api.operations.operation_runner` 请求宿主提供的执行器。ACC 注入现有执行入口以保留状态通知；独立宿主默认通过同一套操作锁和审计记录执行。插件本身无需导入 `api.app`。鉴权仍在路由依赖中执行，拒绝未授权请求后不会调用执行器。

新增功能必须在独立插件包中定义路由、卡片与能力。现有功能的入口位于 `modules/<feature>/plugin.py`，修改这些实现无需改变 DSH 适配器。

当前宿主保留会话、健康检查、框架清单、异常处理、静态页面、宿主关停以及共享状态通知、指标和操作执行器。模块间的业务服务调用仍存在；独立启停与前端页面注册需要继续验收。

## ACC Web 页面注册

内建 React 页面可在自己的模块目录提供 `client-plugin.ts`，默认导出 `{ id, pages }`；页面接收 `{ token }`。`clientPlugins.ts` 通过 Vite glob 自动发现这些入口，主应用使用注册器按页面和启用清单解析组件。插件 ID 与后端清单一致，且后端卡片必须声明对应页面。重复插件 ID 或页面名会报错。

十个内建页面均使用此方式，主入口不再判断具体业务页面。Dashboard、Provider 和日志诊断共用 `modules/operations` 下的数据与卡片组合模块，页面模块负责自己的视图；这部分共享业务服务尚需依赖隔离审计。Agent 页面拥有自己的选择状态和数据读取；备份迁移页面提供现有迁移与清理接口的入口，清理需显式勾选确认。外部独立发行包仍可使用下面的同源页面链接方式，无需参与 ACC 前端编译。

## 独立项目安装示例

`examples/acc-example-plugin` 提供可安装发行包、entry point、API 和独立页面。卡片可设置同源绝对路径 `href`，ACC 通用详情页显示“打开功能”入口。未来小项目可由自己的路由提供页面，无需修改 ACC React 编译入口或 DSH 源码。参见示例 README 的安装、禁用和卸载步骤。

集成测试将示例包真正安装到临时 Python 搜索路径，在新进程启动 ACC 并验证清单、API、HTML 页面与禁用后的 404；测试不改变常用 Python 环境。

## DSH 适配器

`integrations/dsh-plugin-acc` 是独立 npm bundle：

- 通过 `dsh plugin --profile web add <tarball>` 安装；
- Host 注册 `acc_overview`，只读取 ACC 的 loopback `/api/plugins`；
- Client 在 `tool.call.toolview` 插槽渲染 DSH 风格的可点击卡片；
- 在线时点击卡片打开 ACC，离线时返回结构化降级状态，不影响 DSH 主体启动和使用；
- DSH 只依赖公开 HTTP 清单，不 import ACC 源码或私有文件。

未来新增 ACC 插件后，清单、ACC 导航和 DSH 概览卡片会自动出现，无需修改 DSH 或重新编译其源码。只有在需要把某项 ACC 能力直接暴露为 DSH 工具时，才扩展稳定的 capability 调用协议；不能让 DSH 直接依赖业务插件实现。

## 启用配置与生命周期

启动进程前可设置 `ACC_DISABLED_PLUGINS` 为逗号分隔的插件 ID。修改后重启 ACC 生效；当前不提供运行中的热卸载。禁用插件不挂载路由，不出现在 `/api/plugins` 清单中，前端菜单和自动请求据此调整。未知 ID、禁用框架和已启用插件依赖被禁用插件均明确报错。

插件可提供 `lifespan(app)` 异步上下文管理器，在进入时申请资源、退出时释放资源。框架按依赖顺序进入，并按相反顺序退出；后续插件启动失败时也会释放已经进入的上下文。插件自身进入阶段失败前已申请的资源，仍需由该插件在自己的上下文管理器中负责清理。

此禁用开关管理路由、卡片和生命周期贡献，不卸载 Python 包；共享业务服务之间仍可能直接调用。前端组合卡片的操作按钮与模块间服务依赖仍需后续审核。

## 发布与回退

每个阶段按改动范围执行测试、构建和隐私扫描；DSH 集成变更另做打包与真实启动检查。阶段提交推送到 `develop`，以语义化标签形成回退点；改造前远端备份分支为 `backup/pre-plugin-0.3.0-20260916`。
# 框架统计依赖补充

请求和操作统计的实现归属 `feishu_stack.core.metrics`。旧路径 `modules.logs_diagnostics.metrics` 仅保留同一模块对象的兼容别名，避免重复注册 Prometheus 指标。宿主与操作执行器不再通过日志诊断功能取得统计服务。这只消除统计层的反向依赖，其他共享业务服务仍需逐项审计。
