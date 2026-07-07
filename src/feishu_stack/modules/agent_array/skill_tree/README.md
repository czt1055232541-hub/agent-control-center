# skill_tree

这是 Agent 阵列最核心的后端目录，负责把 Agent 数据整理成网页能展示和编辑的形式。

文件说明：

- `agent_registry.py`：定义和读取 Agent 的基础信息。可以把它理解成“有哪些 Agent、顺序怎样、默认元数据是什么”。
- `agent_dashboard.py`：把多个来源的数据拼成前端展示需要的总览信息，比如 Agent 列表、基础设施摘要、诊断解释。
- `agent_config_editor.py`：处理 Agent 可编辑配置的读取、备份、回滚、写回。
- `__init__.py`：包初始化文件。

学习建议：

- 想改 Agent 列表、默认结构、排序规则，看 `agent_registry.py`。
- 想改网页上 Agent 展示的数据组织方式，看 `agent_dashboard.py`。
- 想改“保存配置”“回滚配置”这类行为，看 `agent_config_editor.py`。
