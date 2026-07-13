# 新机器迁移

1. 分别克隆 `{ACC_ROOT}` 与 `{FEISHU_AGENT_ROOT}`，保留独立仓库。
2. 使用 `pyproject.toml` 安装 ACC；`requirements-direct.lock` 是已验证的直接依赖组合，不是完整环境 `pip freeze`。
3. 在 `{ACC_ROOT}/web` 使用已提交的 `package-lock.json` 执行可复现安装和构建。
4. 从示例创建本机配置，填写路径和身份映射，不复制旧机器 token 或运行目录。
5. 依次运行配置校验、Python 测试、前端构建和只读健康检查。
6. 飞书 Agent 根级 Python 运维脚本当前仅依赖标准库和仓库内模块；Node Agent 使用其自身锁文件安装。
