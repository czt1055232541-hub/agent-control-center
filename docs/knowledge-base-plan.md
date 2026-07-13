<!--
  TASK-ID: config-center-knowledge-base
  Author: 代码执行官
  Date: 2026-07-10
  Version: 1.0
-->

# 配置中心本地知识库——功能方案设计

## 1. 背景与目标

### 1.1 现状

Agent Control Center 当前通过 config_center 模块提供内存级键值配置管理，支持 CRUD 和导入导出，仅面向控制中心自身运行参数。多 Agent 协作场景下（项目调度官、代码执行官、运维验证官、质量审计官、项目档案官），各 Agent 的 AGENTS.md 各自硬编码项目规范，缺乏统一的本地知识调用层。

### 1.2 核心目标

1. Agent 能快速检索和引用本地知识（项目文档、配置说明、开发规范、运维手册）
2. 有效防止机密信息通过 Agent 对外泄露

### 1.3 非目标

- 不做云端知识库或飞书文档同步
- 不做通用 RAG 搜索引擎
- 不替代 Agent 自身的 AGENTS.md / SKILL.md
- 不创建飞书应用、Spark/Miaoda 或云资源

## 2. 总体架构

知识库作为 feishu_stack/modules/knowledge_base/ 新模块嵌入控制中心，与现有模块平级：

    src/feishu_stack/modules/knowledge_base/
      __init__.py          # 模块注册
      router.py            # FastAPI 路由
      models.py            # Pydantic 数据模型
      store.py             # 向量存储 + 元数据管理
      ingest.py            # 知识入库管线
      retrieval.py         # 混合检索
      security.py          # 访问控制 + 脱敏 + 审计
      embeddings.py        # 本地嵌入模型封装

与现有模块的关系：
- **config_center** → 知识库配置参数（索引路径、嵌入模型名、相似度阈值）通过 config_center 读写
- **routing_rules** → 可增加规则条件引用知识库检索结果
- **logs_diagnostics** → 知识库审计日志复用统一日志管线

## 3. 数据模型

### 3.1 知识条目 KnowledgeEntry

```python
class KnowledgeEntry(BaseModel):
    id: str                    # UUIDv7，排序友好
    title: str                 # 标题（必填，纯文本）
    content: str               # 正文（Markdown，必填）
    content_hash: str          # SHA-256，用于增量同步比对
    source_type: SourceType    # manual | file_watch | batch_import
    source_path: str | None    # 来源文件绝对路径（file_watch 时有值）
    category: str              # 分类标签
    tags: list[str]            # 自由标签
    sensitivity: Sensitivity   # public | internal | restricted | confidential
    created_at: datetime
    updated_at: datetime
    version: int               # 单调递增版本号
    status: EntryStatus        # active | archived | draft
```

### 3.2 分类体系 Category

```python
class Category(BaseModel):
    id: str
    name: str                  # 项目规范 / 运维手册 / API文档 / 配置说明 / 故障排查
    parent_id: str | None      # 支持二级分类
    description: str
```

预设分类：

| 分类 | 用途 |
|---|---|
| project-specs | 项目规范（AGENTS.md、开发约定） |
| ops-manuals | 运维手册（部署、监控、备份） |
| api-docs | API 文档（接口说明、参数约定） |
| config-guides | 配置说明（stack.settings 字段释义） |
| troubleshooting | 故障排查（常见问题、修复步骤） |
| meeting-notes | 会议/复盘记录 |
| security-policies | 安全策略（脱敏规则、访问控制） |

### 3.3 版本管理

- 每次更新 content 时 version 自增，旧版本保留在 knowledge_versions 表中
- 支持按 ID + version 精确回溯
- 保留最近 N 个版本（默认 10），超出自动清理

### 3.4 存储结构

    runtime/knowledge_base/
      chroma/                    # ChromaDB 持久化向量存储
      metadata.db                # SQLite：知识条目、分类、标签、版本、审计日志
      file_watch_state.json      # 文件监控增量状态

选用 SQLite + ChromaDB 组合：
- SQLite 零配置，与控制中心其他本地状态一致
- ChromaDB 嵌入式运行，无需独立服务进程
- 向量存储和元数据分离，便于独立重建索引

## 4. 知识入库与更新机制

### 4.1 手动导入（Web GUI）

- 控制中心 GUI 新增 知识库 侧边栏页面
- 支持 Markdown 编辑器直接编写/粘贴
- 支持拖拽 .md / .txt / .rst 文件导入
- 导入时必填：标题、分类、敏感级别；选填：标签

### 4.2 自动扫描（file_watch）

- 配置监控目录列表（如 `{ACC_ROOT}/docs/`、`{PROJECTS_ROOT}` 下的项目 docs 目录）
- 基于 watchdog 库监听文件变更（创建、修改、删除）
- 文件 hash 比对实现增量同步，避免重复索引
- 支持 glob 过滤（默认 **/*.md、**/*.txt）
- 变更事件去抖（5 秒窗口），批量处理

### 4.3 批量导入

- API POST /api/knowledge-base/import 接受 JSON 数组
- CLI 命令 python scripts/stack.py knowledge-base import --dir <path>
- 导入时做去重（按 source_path + content_hash 判断）

### 4.4 更新策略

| 场景 | 行为 |
|---|---|
| 手动编辑 | 直接覆盖 content，version +1，重新向量化 |
| 文件变更 | 检测 hash 变化 → 触发更新 → 重新向量化 |
| 批量导入同源文件 | content_hash 未变则跳过，变化则更新 |
| 删除源文件 | 知识条目标记为 archived，不移除向量索引（保留可回溯性） |

## 5. 检索与调用方式

### 5.1 混合检索策略

    用户查询
      ├── 向量检索 (ChromaDB, cosine similarity)
      │     └── 嵌入模型: all-MiniLM-L6-v2（本地）
      ├── 关键词检索 (SQLite FTS5, BM25)
      │     └── 对 title + content 建全文索引
      └── 元数据过滤 (category, tags, sensitivity)
      → 结果融合 (RRF: Reciprocal Rank Fusion)
      → 返回 Top-K

### 5.2 嵌入模型选型

| 模型 | 维度 | 大小 | 理由 |
|---|---|---|---|
| all-MiniLM-L6-v2 | 384 | ~90MB | 默认推荐：速度快、资源低、中文可接受 |
| bge-small-zh-v1.5 | 512 | ~100MB | 备选：中文优化更好 |
| text2vec-base-chinese | 768 | ~400MB | 高精度场景备选 |

默认使用 all-MiniLM-L6-v2，通过 sentence-transformers 库加载。首次启动时自动下载模型到 runtime/knowledge_base/models/。模型选择通过 config_center 配置项 kb.embedding_model 切换。

### 5.3 API 设计

    GET  /api/knowledge-base/search?q=...&category=...&sensitivity=...&top_k=5
    GET  /api/knowledge-base/entries              # 列表（分页）
    GET  /api/knowledge-base/entries/{id}         # 详情
    POST /api/knowledge-base/entries              # 创建
    PUT  /api/knowledge-base/entries/{id}         # 更新
    DELETE /api/knowledge-base/entries/{id}       # 删除（软删除 → archived）
    GET  /api/knowledge-base/entries/{id}/versions # 版本历史
    POST /api/knowledge-base/import               # 批量导入
    GET  /api/knowledge-base/categories           # 分类列表
    POST /api/knowledge-base/watch/start          # 启动文件监控
    POST /api/knowledge-base/watch/stop           # 停止文件监控
    GET  /api/knowledge-base/audit-log            # 审计日志查询
    POST /api/knowledge-base/rebuild-index        # 重建向量索引

### 5.4 权限控制

基于敏感级别控制检索范围：

| 级别 | Agent 可见 | 说明 |
|---|---|---|
| public | 全部 Agent | 通用规范、公开文档 |
| internal | 全部 Agent | 内部开发文档 |
| restricted | 仅指定 Agent 角色 | 按 allowed_roles 字段白名单 |
| confidential | 不入库 / 不入索引 | 仅元数据可见，正文需单独授权 |

Agent 通过控制中心 API 调用时携带 X-Control-Token（复用现有鉴权）。角色映射从 stack.settings.local.json 的 a2aBots 中解析。

## 6. 防泄密设计

### 6.1 访问白名单

- 每个知识条目可指定 allowed_roles: list[str]（如 ["代码执行官", "运维验证官"]）
- 检索时自动按请求方角色过滤
- 管理员角色（如项目调度官）可查看所有条目

### 6.2 内容脱敏

- 在入库管线 ingest.py 中植入脱敏处理器链
- 默认规则：
  - 匹配 sk-... / api_key=... / token=... → 替换为 [REDACTED]
  - 匹配 IP 地址 → 替换为 [IP_REDACTED]
  - 匹配 open_id / chat_id 格式 → 替换为 [ID_REDACTED]
- 脱敏规则可配置（config/kb_sanitize_rules.json），支持正则扩展
- 入库前预览脱敏结果，人工确认后生效

### 6.3 审计日志

记录每次知识库访问事件：

```python
class AuditEvent(BaseModel):
    id: str
    timestamp: datetime
    agent_role: str           # 请求方 Agent 角色
    action: str               # search | read | create | update | delete | export
    entry_id: str | None
    query: str | None
    result_count: int | None
    client_ip: str            # 127.0.0.1（本地调用）
```

审计日志写入 runtime/knowledge_base/metadata.db 的 audit_log 表，保留 90 天。

### 6.4 外发拦截

- 知识库仅向本地控制中心 API（127.0.0.1:8765）暴露，不绑定外部网卡
- confidential 级别条目正文不进入向量索引，检索时仅返回元数据摘要
- 批量导出 API 仅限管理员角色调用，且导出内容自动脱敏
- 不提供"复制全文"类一次性导出按钮，降低误操作风险

### 6.5 模型本地化

- 嵌入模型全部本地加载，不调用外部 API
- 向量索引本地持久化，不依赖云端向量数据库
- 与 MoonBridge / OpenClaw 等网络组件隔离

## 7. 与配置中心的集成

### 7.1 配置项清单

| 配置键 | 默认值 | 说明 |
|---|---|---|
| kb.enabled | true | 知识库总开关 |
| kb.data_dir | runtime/knowledge_base | 数据目录 |
| kb.embedding_model | all-MiniLM-L6-v2 | 嵌入模型名 |
| kb.chunk_size | 512 | 文本分块大小（tokens） |
| kb.chunk_overlap | 64 | 分块重叠量 |
| kb.top_k | 5 | 默认检索返回数 |
| kb.similarity_threshold | 0.7 | 相似度阈值 |
| kb.watch_dirs | [] | 监控目录列表（JSON 数组） |
| kb.watch_enabled | false | 是否启用文件监控 |
| kb.audit_retention_days | 90 | 审计日志保留天数 |
| kb.max_versions | 10 | 单条目版本保留数 |

### 7.2 集成方式

- 知识库模块在 feishu_stack/modules/knowledge_base/__init__.py 中注册
- 启动时从 config_center 读取配置项 → 完成初始化
- 配置变更时通过 config_center.set_config() 写入，知识库模块热加载
- API 路由在 api/app.py 中挂载，与现有模块平级

### 7.3 GUI 集成

在控制中心 Web GUI 侧边栏新增：

    Agent 阵列
    配置中心
    知识库        ← 新增
    模型供应商
    路由规则
    飞书连接
    日志与诊断
    备份与迁移
    运维操作
    作战任务

知识库页面包含三个子视图：

1. **知识检索**：搜索框 + 过滤器（分类、标签、敏感级别） + 结果列表
2. **知识管理**：条目 CRUD、分类管理、批量导入
3. **设置与审计**：监控状态、索引重建、审计日志查看

## 8. 技术选型总结

| 组件 | 选择 | 理由 |
|---|---|---|
| 向量存储 | ChromaDB (嵌入式) | 零配置、Python 原生、持久化 |
| 全文检索 | SQLite FTS5 | 已在技术栈内，零额外依赖 |
| 元数据存储 | SQLite | 与控制中心 runtime 状态一致 |
| 嵌入模型 | all-MiniLM-L6-v2 | ~90MB，本地运行，384 维 |
| 嵌入框架 | sentence-transformers | 社区成熟，模型生态丰富 |
| 文件监控 | watchdog | Python 原生，跨平台 |
| 文本分块 | langchain.text_splitter | 仅用分块器，不引入完整 langchain |
| 前端 | React 组件（复用现有 web/ 架构） | 与控制中心 GUI 统一 |
| API 框架 | FastAPI（复用现有 api/app.py） | 与控制中心后端统一 |

## 9. 隐私安全合规

### 9.1 数据最小化

- 仅索引用户显式指定的目录和文件
- 不扫描系统目录、浏览器缓存、聊天记录
- file_watch 仅限于白名单目录

### 9.2 数据隔离

- 全部数据存储于 runtime/knowledge_base/，不写入系统 Temp 目录
- 向量索引与元数据均不外传
- 与控制中心其他运行时数据在同一安全域内

### 9.3 访问控制

- confidential 条目正文不参与向量检索，仅元数据可见
- restricted 条目按角色白名单过滤
- 所有 API 调用受 X-Control-Token 保护

### 9.4 审计合规

- 完整审计日志覆盖所有读写操作
- 日志保留期可配置，默认 90 天
- 日志内容不含知识条目正文（仅记录 entry_id + action）

### 9.5 合规对齐

- 符合项目 README「隐私与公开仓库边界」中列出的禁止提交项
- 知识库内的机密信息遵循与 stack.settings.local.json 同等级的保护
- 外发拦截确保 Agent 不会将知识库机密内容发送到外部 API

## 10. 实施路线图

### Phase 1: 基础设施（预计 2 周）

- 搭建 knowledge_base 模块骨架（models、router、store）
- SQLite 元数据表创建与迁移
- 嵌入模型加载封装
- 手动 CRUD API + GUI 基础页面

### Phase 2: 检索能力（预计 1 周）

- ChromaDB 集成，向量索引构建
- SQLite FTS5 全文索引
- 混合检索（RRF 融合）
- 敏感级别过滤

### Phase 3: 自动化（预计 1 周）

- 文件监控（watchdog）与增量同步
- 内容脱敏管线
- 审计日志
- CLI 命令：导入、重建索引、导出

### Phase 4: 安全加固（预计 1 周）

- 角色白名单接入
- 外发拦截验证
- 审计日志查询 GUI
- 性能测试（1000+ 条目检索延迟）

## 11. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 嵌入模型首次下载失败 | 知识库无法启动 | 预置模型文件 + 离线回退方案 |
| ChromaDB 向量索引损坏 | 检索不可用 | 提供 API 重建索引，元数据独立不受影响 |
| 大文件索引性能 | 入库/检索延迟 | 分块处理 + 异步队列，单文件上限 10MB |
| 敏感信息漏脱敏 | 机密泄露 | 多层防线：入库脱敏 + 检索过滤 + 外发拦截 |
| 版本膨胀 | 磁盘占用过大 | 自动清理旧版本 + 可配置保留数 |
| SQLite 并发写入瓶颈 | 写入延迟 | 单写入者 + WAL 模式，读并发不受限 |
