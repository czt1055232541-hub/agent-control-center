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
