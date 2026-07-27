#!/usr/bin/env python3
import json

path = 'F:/1AI/Agent control center/projects/task_directory.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_task = {
    'taskId': 'xzc-management-dashboard-phase1',
    'title': '芯智辰光管理驾驶舱 — Phase 1: 管理驾驶舱HTML模板开发',
    'parentProjectId': 'xzc-management-dashboard-phase1',
    'parentProjectName': '芯智辰光管理驾驶舱',
    'workspacePath': 'F:\\1AI\\Agent control center\\projects\\xzc-management-dashboard',
    'status': '进行中',
    'phase': '开发实现',
    'assignee': '代码执行官',
    'updatedAt': '2026-07-20T14:00:00+08:00',
    'tags': ['管理驾驶舱', 'HTML模板', '飞书妙搭', '芯智辰光', 'Phase 1'],
    'source': 'initiative',
    'hidden': False
}
data['tasks'].append(new_task)
data['updatedAt'] = '2026-07-20T14:00:00.000000+00:00'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
count = len(data['tasks'])
print(f"Task registered. Total: {count}")
