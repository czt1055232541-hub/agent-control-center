# dsh-plugin-acc

ACC 的树外 DeepSeek Harness bundle。它不修改 DSH 源码：Host 插件注册 `acc_overview` 工具，Client 插件把该工具渲染为可点击的 DSH 原生卡片。

客户端必须交付 DSH 模块加载器的经典脚本工厂（`window.__ModuleLoader__.load`），不能直接交付带 `import/export` 的 ES Module。0.1.2 修正该格式，并通过模块表共享宿主 React；无需修改或重建 DSH 源码。更新安装包后需重新加载 DSH 客户端，是否需要重启宿主取决于当前 profile 的热更新状态。

安装到 Web profile：

```bash
dsh plugin --profile web add /absolute/path/to/integrations/dsh-plugin-acc
dsh --profile web --dump-config
```

Windows 上如果 checkout 路径包含空格，当前 DSH CLI 的 pnpm 转发可能拆分本地目录参数。此时先运行 `npm pack --pack-destination <无空格目录>`，再安装生成的 `.tgz`。

默认连接 `http://127.0.0.1:8765`。部署可在 profile 的 `cordis.patch.yml` 中按 `acc-integration` id 覆盖完整配置。ACC 离线时工具返回离线状态，DSH 其他功能不受影响。

## 调出卡片与人工验收

卡片是 `acc_overview` 工具的调用结果，不是侧边栏固定入口，也不会自动插入历史会话。

1. 在 ACC 仓库运行 `python scripts/stack.py serve-control-center --no-build --open`，确认 ACC 页面可打开。
2. 打开已安装本插件的 DSH Web profile，在新会话发送：`请调用 acc_overview 查看 ACC 状态，只执行这项只读查询，不执行其他操作。`
3. 若当前是仅暴露 `run_code` 的 PTC 模式，应由 DSH 按该模式的工具调用规则调用；若报告工具不存在，记录原始错误，检查当前 profile 和安装配置，不能只凭自然语言回复认定插件生效。
4. 确认出现标题为 Agent Control Center 的卡片，状态在线，布局无溢出；点击主体应在新标签页打开 ACC。下方“查看调用详情”应仍能查看工具结果。
5. 保留卡片截图及点击后的 ACC 页面截图；分别检查常用浅色/深色主题。安装包脚本验证不能替代这一步。

ACC 服务与 DSH 独立启动；安装 DSH 插件不会自动启动 ACC。ACC 未运行时出现离线卡片是预期行为。不要为测试离线而中止正在执行任务的服务；自动化验证已使用独立模拟服务覆盖超时与离线。

维护者可从 ACC 仓库运行安装包验证（不调用模型、不停止用户服务）：

```bash
node integrations/dsh-plugin-acc/verify-installed.mjs <profile中已安装的插件目录> [在线ACC地址]
```

脚本使用已安装包和真实 DSH 工具定义库，检查在线清单、结果渲染、HTTP 错误、无效 JSON、错误清单结构、超时及模拟服务退出。它不替代浏览器显示/点击、宿主其他工具或卸载回归。

DSH profile 使用宿主共享依赖 fallback，`pnpm peers check` 可能报告 profile 本身未安装 peers。不要仅为消除警告而复制安装 Cordis 或 React；先运行上述脚本检查实际解析版本，并与本包 peerDependencies 对照。解析失败或版本不兼容时才处理宿主环境。
