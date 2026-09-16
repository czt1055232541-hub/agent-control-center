# common

这个目录放前端通用组件，也就是很多页面会反复复用的小积木。

文件说明：

- `ActionButton.tsx`：统一风格的操作按钮。
- `CodexRuntimePanel.tsx`：展示和切换 Codex / DeepSeek 运行相关状态的面板。
- `ComponentPanel.tsx`：通用信息面板容器。
- `DiagnosticCard.tsx`：展示诊断结果的小卡片。
- `StatusPill.tsx`：状态小标签。
- `statusStyles.ts`：状态颜色和样式映射。

学习建议：

- 想统一修改常用 UI 外观，优先从这里改。
- 如果只是某个业务区块独有的展示，不一定适合放这里。
