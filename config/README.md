# config

这个目录放配置文件。

文件说明：

- `stack.settings.example.json`：可提交到 Git 的脱敏模板。新机器部署时可以参考它填写真实配置。
- `stack.settings.local.json`：你本机真实使用的配置文件，里面可能有 open_id、chat_id、本机路径等隐私信息，不会提交到 Git。

学习建议：

- 想改模型默认值、路径、端口、Agent 本机配置，通常从这里开始。
- 真正读取配置的代码入口在 `src/feishu_stack/core/settings.py`。
