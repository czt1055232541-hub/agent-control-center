# Database

Agent Control Center 当前没有正式数据库依赖。

未来如果引入持久化数据库，本目录用于放置：

- `schema/`：结构定义
- `migrations/`：迁移脚本
- `seeds/`：初始化数据
- `local/`：仅本机使用的数据文件，必须加入 `.gitignore`
