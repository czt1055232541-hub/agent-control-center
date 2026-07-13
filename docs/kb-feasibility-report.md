# 配置中心本地知识库——方案可行性验证报告

**验证时间**: 2026-07-10 16:30
**验证执行**: 运维验证官

---

## 1. 技术选型可行性

| 组件 | 当前环境 | 结论 |
|---|---|---|
| Python | 3.13.2 (64-bit) | ✅ 满足要求 (>=3.11) |
| FastAPI | 0.137.2 | ✅ 已安装 |
| uvicorn | 0.49.0 | ✅ 已安装 |
| pydantic | 2.13.4 | ✅ 已安装 |
| numpy | 2.3.1 | ✅ 已安装 |
| SQLite3 | 3.45.3 (FTS5 内置) | ✅ stdlib，零依赖 |
| **chromadb** | ❌ 未安装 | ⚠️ PyPI 最新 1.5.9，需安装 |
| **sentence-transformers** | ❌ 未安装 | ⚠️ PyPI 最新 5.6.0，需安装（含 torch） |
| **watchdog** | ❌ 未安装 | ⚠️ PyPI 最新 6.0.0，纯 Python wheel，兼容 |
| **langchain-text-splitters** | ❌ 未安装 | ⚠️ 轻量分块器，需安装 |

**关键风险：Python 3.13 兼容性**
- torch 2.13.0 已支持 Python 3.13，但在 Windows x64 上需确认预编译 wheel 可用
- chromadb 1.5.9 依赖 torch 和 onnxruntime，整体依赖链需实际安装验证
- 建议 Phase 1 第一周先验证 `pip install chromadb sentence-transformers watchdog langchain-text-splitters` 能否成功

**磁盘空间**: F: 盘 227.6 GB 空闲 / 310.5 GB 总容量，模型 (~90MB) + 向量存储完全足够

---

## 2. 架构合理性

**后端模块结构**
- 现有 11 个模块位于 `src/feishu_stack/modules/`，均平级排列。knowledge_base 作为第 12 个模块位置正确
- 但当前 API 采用**单体路由模式**：所有 `@app.get/post/...` 直接写在 `src/feishu_stack/api/app.py`（约 1400 行），未使用 FastAPI `APIRouter` 子路由
- 现有模块如 config_center、routing_rules 也是通过导入函数到 app.py 里注册路由，而非 `include_router`
- 计划中的 12 个 REST API 端点如果要沿用当前模式，会给 app.py 再增加约 200-300 行；推荐引入 `knowledge_base/router.py` 的 `APIRouter` + `app.include_router()` 模式，更整洁

**配置中心集成**
- config_center 当前是**纯内存存储**（dict + threading.Lock），重启后配置丢失
- 计划中 11 个 `kb.*` 配置项依赖 config_center 管理，如果 config_center 不做持久化改造，知识库配置会在控制中心重启后丢失
- 建议：要么改造 config_center 支持持久化（写入 runtime/ 的 JSON 或 SQLite），要么 knowledge_base 模块自行管理持久配置

**Web GUI 集成**
- 侧边栏在 `web/src/app/Sidebar.tsx`，使用 TypeScript 联合类型 `CommandPage` 和数组 `navItems`
- 新增"知识库"页面需要：
  1. 向 `CommandPage` 类型添加 `"knowledge"` 值
  2. 向 `navItems` 数组添加一项
  3. 创建 `web/src/modules/knowledge-base/` 页面组件
  4. 在路由处理中注册新页面分支
- 现有模式完全支持，技术无阻塞

**总结**: 架构概念上合理，但后端集成方式需要适配当前单体路由风格，配置持久化需要补充。

---

## 3. 防泄密设计评议

| 设计项 | 评价 |
|---|---|
| 角色白名单 (allowed_roles) | ✅ 合理。复用 X-Control-Token + stack.settings.local.json 角色映射 |
| 入库脱敏管线 | ✅ 默认规则覆盖 API Key、IP、open_id/chat_id。正则扩展机制灵活 |
| 审计日志 (90 天) | ✅ 结构完整，不记录条目正文，仅 entry_id + action |
| 外发拦截 (127.0.0.1 绑定) | ✅ 强约束。confidential 级别正文不进入向量索引 |
| 模型全本地化 | ✅ 不调用外部 API，不依赖云端向量数据库 |

**改进建议**:
1. 脱敏管线中的 `sk-...` 正则可能误伤正常文本中的 "task-" 等模式，建议加前后边界约束（如 `\b(sk-|api_key=|token=)\S+`）
2. 角色白名单中的"管理员角色（如项目调度官）可查看所有条目"存在特权过大风险，建议审计日志中对管理员跨级查看做高亮标记

**总体**: 防泄密设计合理、可落地，覆盖了从入库 → 存储 → 检索 → 导出各环节。

---

## 4. 实施计划评估

| Phase | 周期 | 评估 |
|---|---|---|
| Phase 1: 基础设施 | 2 周 | ✅ 合理。模块骨架 + SQLite 表 + CRUD API + GUI 基础页面，2 周充裕 |
| Phase 2: 检索能力 | 1 周 | ✅ 合理。ChromaDB + FTS5 + 混合检索 + 敏感过滤 |
| Phase 3: 自动化 | 1 周 | ⚠️ 适中。watchdog + 脱敏管线 + 审计日志 + CLI，1 周略紧 |
| Phase 4: 安全加固 | 1 周 | ✅ 合理。角色白名单 + 外发拦截 + 审计 GUI + 性能测试 |
| **合计** | **5 周** | ✅ **总体合理**，建议 Phase 1 中预留 2 天做依赖安装验证 |

**风险表覆盖**：6 项主要风险覆盖了模型下载、索引损坏、大文件性能、脱敏漏、版本膨胀、SQLite 并发，充分。
**补充建议风险**：第 7 项 — Python 3.13 下 torch/chromadb 安装兼容性风险，缓解措施为 Phase 1 前置安装验证 + 预留 pyproject.toml 备选 Python 3.12 兼容声明。

---

## 5. 资源依赖清单

### 5.1 新增 Python 依赖

| 包名 | 预计大小 | 用途 |
|---|---|---|
| chromadb | ~100MB (含 onnxruntime) | 向量存储 |
| sentence-transformers | ~50MB | 嵌入模型框架 |
| torch (自动依赖) | ~800MB (CPU 版) | 深度学习后端 |
| transformers (自动依赖) | ~300MB | 模型加载 |
| watchdog | ~79KB | 文件监控 |
| langchain-text-splitters | ~100KB | 文本分块 |

> **合计新增磁盘占用**: ~1.3 GB（含依赖包 + 模型文件）

### 5.2 模型下载

- **默认模型**: all-MiniLM-L6-v2（~90MB）
- **首次启动自动下载目录**: `runtime/knowledge_base/models/`
- **备选模型**: bge-small-zh-v1.5（~100MB）、text2vec-base-chinese（~400MB）
- 需确保网络可访问 HuggingFace 或配置镜像源

### 5.3 运行时目录

| 路径 | 用途 |
|---|---|
| `runtime/knowledge_base/chroma/` | ChromaDB 向量索引持久化 |
| `runtime/knowledge_base/metadata.db` | SQLite 元数据 + 审计日志 |
| `runtime/knowledge_base/models/` | 本地嵌入模型缓存 |
| `runtime/knowledge_base/file_watch_state.json` | 文件监控增量状态 |

### 5.4 不需要的资源

- ❌ 不依赖外部 API / 云端服务
- ❌ 不依赖 MoonBridge / OpenClaw 网络组件
- ❌ 不需要独立数据库服务
- ❌ 不需要 GPU（CPU 推理即可）

---

## 6. 验证结论

**总体判定: ⚠️ 有条件通过**

### 通过项
- ✅ 技术栈选择合理，全部组件纯本地运行，无外部依赖
- ✅ 架构与现有控制中心模块兼容，GUI 侧边栏可扩展
- ✅ 防泄密设计覆盖完整，各环节均有控制措施
- ✅ 实施计划 4 Phase / 5 周可行，风险表充分
- ✅ 磁盘空间充裕（227.6 GB 空余）

### 条件项（需在 Phase 1 中验证）
1. ⚠️ **Python 3.13 依赖兼容性** — `pip install chromadb sentence-transformers` 能否在 Windows + Python 3.13 上成功安装，需实际验证
2. ⚠️ **config_center 持久化** — 如果 kb.* 配置项依赖 config_center，需确认或改造 config_center 支持重启不丢失
3. ⚠️ **API 路由注册模式** — 建议使用 `APIRouter.include_router()` 而非继续膨胀单体 app.py

### 阻塞项
- 无绝对阻塞项

---

*本验证基于文档 `docs/knowledge-base-plan.md` 和当前运行环境 `F:\1AI\Agent control center` 进行*
