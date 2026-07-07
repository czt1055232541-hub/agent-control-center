# tests/core

这里测试后端基础设施层。

文件说明：

- `test_config.py`：测试配置读取与校验。
- `test_models.py`：测试数据模型行为。
- `test_process.py`：测试进程工具相关逻辑。
- `test_status.py`：测试状态聚合。
- `test_module_layout.py`：测试目录结构约定和旧导入兼容。

学习建议：

- 改了 `core/` 里的底层逻辑以后，这里通常是第一批会失败的测试。
