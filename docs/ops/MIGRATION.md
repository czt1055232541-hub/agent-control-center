# 新机器迁移

1. 只克隆 ACC 单仓；`agent-runtime` 已包含飞书 Agent 源码与历史。
2. 使用 `pyproject.toml` 安装 ACC；`requirements-direct.lock` 是已验证的直接依赖组合，不是完整环境 `pip freeze`。
3. 分别在 `{ACC_ROOT}/web` 与 `{ACC_ROOT}/agent-runtime/agents/feishu-codex-agent` 使用已提交锁文件安装和构建。
4. 从示例创建本机配置，填写路径和身份映射，不复制旧机器 token 或运行目录。
5. 依次运行配置校验、Python 测试、前端构建和只读健康检查。
6. 配置 `projectsRoot` 指向外置项目目录；不得把项目产物复制进 Git。
7. 使用根 CLI 完成 watchdog、A2A、Node Agent 和控制中心冒烟测试。
