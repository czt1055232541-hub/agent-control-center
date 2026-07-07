# hooks

这个目录放 React 自定义 Hook。你可以把它们理解成“前端拿数据和处理状态的可复用方法”。

文件说明：

- `useStatus.ts`：读取后端状态。
- `useOperations.ts`：执行启动、停止、切换等操作。
- `useLogs.ts`：读取日志。
- `useMigration.ts`：处理线程迁移、provider 迁移相关请求。
- `useCommandDashboard.ts`：读取命令面板需要的聚合数据。

学习建议：

- 页面“显示什么数据、点按钮后请求哪里”，通常先在这些 Hook 里找。
