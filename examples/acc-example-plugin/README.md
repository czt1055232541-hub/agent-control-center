# 独立小项目接入 ACC

这个示例是独立 Python 发行包，不复制到 ACC 核心代码中运行。

1. 将小项目的接口封装为 `APIRouter`，入口工厂返回 `AccPlugin`。
2. 在 `pyproject.toml` 注册 `agent_control_center.plugins` entry point。
3. 使用运行 ACC 的同一 Python 环境安装本包：

   ```text
   python -m pip install --no-deps ./examples/acc-example-plugin
   ```

4. 重启 ACC，导航自动出现 Hello ACC；进入详情后点击“打开功能”即可访问插件页面。
5. DSH 的 `acc_overview` 再次执行时会从 ACC 清单读到新插件，无需重新安装 DSH 适配器。

卡片 `href` 必须是同源绝对路径，例如 `/api/example/ui`；不允许外部域名或脚本 URL。
现有独立 Web 项目可把构建产物通过自己的路由提供，不必加入 ACC 的 React 编译。
写入接口应使用 `Depends(require_control_token)`；此示例仅提供只读接口。

临时禁用：为 ACC 进程设置 `ACC_DISABLED_PLUGINS=example.hello` 后重启。
卸载：`python -m pip uninstall acc-example-plugin` 后重启 ACC。以上操作只影响外部包。

自动化集成测试把本包复制到 pytest 临时目录，在隔离 `--target` 目录安装，验证发现、API、页面和禁用行为，不安装进用户的常用 Python 环境。
