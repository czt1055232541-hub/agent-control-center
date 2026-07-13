# 单仓物理合并记录（2026-07-13）

## Git 与回滚点

- ACC 合并前基线：`e7b27fab8a1517ff5efb30bca5141bed68152a07`
- ACC 优化检查点：`bd5dc2aa3cc79392a0afa9dda25f70c4f1efebd7`
- 飞书仓库导入 HEAD：`33ddf5db5c1871d2b3186e8b3f1a5ce428b30d59`
- 非 squash subtree 合并提交：`653a54e`
- 路径与入口收口提交：`926c7a9`
- 回滚标签：`pre-agent-stack-merge-acc`、`pre-agent-stack-merge-feishu`
- 完整 bundle：`F:/1AI/merge-backups/2026-07-13-agent-stack/`

飞书原始 HEAD 已验证为当前分支祖先；合并后提交总数为 53，两个提交图均被保留。

## 最终结构与本机切换

- 飞书运行面：`{ACC_ROOT}/agent-runtime`
- 唯一配置：`{ACC_ROOT}/config/stack.settings.local.json`
- 唯一公开入口：`python scripts/stack.py`
- 统一状态：`{ACC_ROOT}/runtime/{logs,pids,watchdogs,summaries}`
- 项目工作区：`{ACC_ROOT}/projects`，由 `projectsRoot` 指向并通过 `.gitignore` 排除
- 原飞书仓库在项目文件完成清单校验、配置验证及 bundle 恢复验证后删除；其提交历史仍保留在当前仓库和完整 bundle 中。

本机 lark-cli 与认证 profile 已复制到被 Git 忽略的 `agent-runtime/.npm-global` 和 `agent-runtime/.home`。根配置通过原子替换迁移并保留有限备份。桌面启动器已更新，未发现引用旧仓路径的计划任务。

2026-07-13 后续收口中，原 `projects` 的 5,598 个文件迁入 `{ACC_ROOT}/projects`，迁移前后路径与大小清单摘要一致；本机 `projectsRoot` 随后原子更新。旧 `feishu_agent` 工作区在恢复 bundle 验证通过后删除。

## 验收结果

- ACC Python：273 项测试通过。
- ACC Web：生产构建通过。
- Node Agent：27 项测试通过，npm audit 报告 0 个漏洞。
- 配置 API：`ok=true`、`peer_status=merged`、0 漂移、0 错误。
- lark-cli：新路径认证状态检查通过。
- 启停闭环：Native 栈从单仓成功启动，Node Agent cwd 指向新路径，随后全部正常停止。
- Provider：冒烟后恢复为切换前的 native `gpt-5.6-sol` / `medium`。
- 安全：Codex Desktop 未停止；未发送真实飞书测试消息；暂存内容未发现真实格式的 open ID、chat ID 或凭据赋值。

## 后续目录归类建议

合并后的整理应延续 ACC 的控制面逻辑：根目录只放公开入口、控制面源码、配置模板、文档、测试和本机运行边界；飞书运行面继续收敛在 `agent-runtime` 内。

- 保留根级：`src/`、`web/`、`scripts/`、`config/`、`tests/`、`docs/`、`runtime/`、`projects/`、`workspaces/`。
- 保留在 `agent-runtime/`：飞书角色定义、Node Agent package、OpenClaw/飞书工作流内部脚本、provider 辅助逻辑。
- 继续忽略且不提交：`runtime/*`、`projects/`、`workspaces/`、`.home/`、`.npm-global/`、日志、PID、会话、真实本机配置。
- 可下一阶段评估迁移：`agent-runtime/runtime/` 下的占位目录可并入根 `runtime/`；`agent-runtime/scripts/` 中被根 `scripts/stack.py` 包装的内部脚本可按命令组迁入 `src/feishu_stack/modules/operations/`。
- 不建议现在移动：`agent-runtime/agents/feishu-codex-agent` 的 `package.json`、锁文件、TypeScript 源码和测试应保持为独立 Node package，避免破坏构建边界。
- 代码执行官工作区固定为 `{ACC_ROOT}/workspaces/dev`；`agent-runtime/agents/feishu-codex-agent` 只表示 Agent 程序包，不再作为开发工作区展示。
