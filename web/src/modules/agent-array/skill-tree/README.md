# skill-tree

这个目录对应 Agent 阵列里的技能树和冒险视图部分。

文件说明：

- `AgentCard.tsx`：技能树视图里的 Agent 卡片样式。
- `AgentDetailPanel.tsx`：某个 Agent 的详细信息面板。
- `EquipmentSlots.tsx`：装备槽位展示。
- `RecentRunsTable.tsx`：最近运行记录表格。
- `SkillConfigInspector.tsx`：技能/配置检查面板。
- `ConfiguredSkillTree.tsx`：读取后端 `tree-config` 接口后渲染的正式配置驱动技能树。
- `SkillNode.tsx`：单个技能节点。
- `SkillTreeCanvas.tsx`：技能树主画布。
- `TaskTraceMap.tsx`：任务轨迹展示。
- `TopStatusBar.tsx`：顶部状态栏。
- `viewModels.ts`：把后端原始数据转换成前端更好渲染的数据结构。

学习建议：

- 想改“显示效果”，通常看各个 `.tsx` 组件。
- 想改“前端怎么理解后端数据”，优先看 `viewModels.ts`。
- 想改每个 Agent 的真实技能树图谱，优先改 `config/skill-tree-workshop/agents/*.skill-tree.json`，不要直接改 React 里的节点。
