# operations

这个目录负责“执行动作”，也就是把各个模块串起来真正完成启动、停止、查看状态等操作。

文件说明：

- `cli.py`：命令行入口实现。`python -m feishu_stack.cli` 最终会走这里。
- `control_center.py`：启动或打开网页控制中心相关逻辑。
- `operations.py`：操作锁、最近操作记录等底层编排逻辑，避免冲突操作同时执行。
- `stack_actions.py`：把多个组件组合成更高层动作，比如启动整套 stack。
- `typing_indicator.py`：管理输入状态辅助组件。
- `__init__.py`：包初始化文件。

学习建议：

- 想改命令行命令，看 `cli.py`。
- 想改“启动整套 stack 会依次做什么”，看 `stack_actions.py`。
- 想理解为什么有些操作不能同时点，看 `operations.py`。
