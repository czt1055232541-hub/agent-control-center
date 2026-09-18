"""Business-free built-in metadata; implementations load only when mounted."""
from importlib import import_module
from feishu_stack.plugin_sdk import AccPlugin, PluginCard

def _mount_agent_array():
    module = import_module("feishu_stack.modules.agent_array.plugin")
    return module.router

def create_agent_array_plugin() -> AccPlugin:
    return AccPlugin(id='acc.agent-array', name='Agent 阵列', version='1.0.0', description='Agent 阵列', requires=('acc.framework',), capabilities=('agents.read', 'skills.manage'), cards=(PluginCard('acc.agent-array.overview', 'Agent 阵列', 'Agent 阵列', 'agents', icon='swords', order=20),), router_factory=_mount_agent_array)

def _mount_backup_migration():
    module = import_module("feishu_stack.modules.backup_migration.plugin")
    return module.router

def create_backup_migration_plugin() -> AccPlugin:
    return AccPlugin(id='acc.backup-migration', name='备份与迁移', version='1.0.0', description='Backup Migration', requires=('acc.framework',), capabilities=('backups.manage',), cards=(PluginCard('acc.backup-migration.overview', '备份与迁移', 'Backup Migration', 'backup', icon='archive', order=100),), router_factory=_mount_backup_migration)

def _mount_config_center():
    module = import_module("feishu_stack.modules.config_center.plugin")
    return module.create_router()

def create_config_center_plugin() -> AccPlugin:
    return AccPlugin(id='acc.config-center', name='配置中心', version='1.0.0', description='配置校验、导入和导出。', requires=('acc.framework',), capabilities=('config.manage',), cards=(PluginCard('acc.config-center.overview', '配置中心', '配置校验、导入和导出。', 'config', 'file-cog', 80),), router_factory=_mount_config_center)

def _mount_dashboard():
    module = import_module("feishu_stack.modules.dashboard.plugin")
    return module.router

def create_dashboard_plugin() -> AccPlugin:
    return AccPlugin(id='acc.dashboard', name='Dashboard 总览', version='1.0.0', description='运行状态与关键指标总览。', requires=('acc.framework',), capabilities=('dashboard.read',), cards=(PluginCard('acc.dashboard.overview', 'Dashboard 总览', '运行状态与关键指标总览。', 'dashboard', icon='layout-dashboard', order=10),), router_factory=_mount_dashboard)

def _mount_feishu_connection():
    module = import_module("feishu_stack.modules.feishu_connection.plugin")
    return module.create_router()

def create_feishu_connection_plugin() -> AccPlugin:
    return AccPlugin(id='acc.feishu-connection', name='飞书连接', version='1.0.0', description='飞书账号、权限与授权状态。', requires=('acc.framework',), capabilities=('feishu.inspect',), cards=(PluginCard('acc.feishu-connection.overview', '飞书连接', '飞书账号、权限与授权状态。', 'feishu', 'send', 40),), router_factory=_mount_feishu_connection)

def _mount_local_tools():
    module = import_module("feishu_stack.modules.local_tools.plugin")
    return module.router

def create_local_tools_plugin() -> AccPlugin:
    return AccPlugin(id='acc.local-tools', name='外部应用', version='1.0.0', description='管理独立程序的进程和页面，不重复管理 ACC 功能插件。', requires=('acc.framework',), capabilities=('tools.manage',), cards=(PluginCard('acc.local-tools.overview', '外部应用', '独立程序的注册、启动与页面嵌入', 'tools', icon='package-open', order=70),), router_factory=_mount_local_tools)

def _mount_logs_diagnostics():
    module = import_module("feishu_stack.modules.logs_diagnostics.plugin")
    return module.router

def create_logs_diagnostics_plugin() -> AccPlugin:
    return AccPlugin(id='acc.logs-diagnostics', name='日志与诊断', version='1.0.0', description='日志与诊断', requires=('acc.framework',), capabilities=('diagnostics.read',), cards=(PluginCard('acc.logs-diagnostics.overview', '日志与诊断', '日志与诊断', 'diagnostics', icon='file-text', order=90),), router_factory=_mount_logs_diagnostics)

def _mount_model_provider():
    module = import_module("feishu_stack.modules.model_provider.plugin")
    return module.router

def create_model_provider_plugin() -> AccPlugin:
    return AccPlugin(id='acc.model-provider', name='模型与 Provider', version='1.0.0', description='模型与 Provider', requires=('acc.framework',), capabilities=('providers.manage',), cards=(PluginCard('acc.model-provider.overview', '模型与 Provider', '模型与 Provider', 'provider', icon='server-cog', order=50),), router_factory=_mount_model_provider)

def _mount_routing_rules():
    module = import_module("feishu_stack.modules.routing_rules.plugin")
    return module.create_router()

def create_routing_rules_plugin() -> AccPlugin:
    return AccPlugin(id='acc.routing-rules', name='路由规则', version='1.0.0', description='消息与任务路由规则管理。', requires=('acc.framework',), capabilities=('routing.manage',), cards=(PluginCard('acc.routing-rules.overview', '路由规则', '消息与任务路由规则管理。', 'routing', 'route', 60),), router_factory=_mount_routing_rules)

def _mount_task_battlefield():
    module = import_module("feishu_stack.modules.task_battlefield.plugin")
    return module.router

def create_task_battlefield_plugin() -> AccPlugin:
    return AccPlugin(id='acc.task-battlefield', name='Task Battlefield', version='1.0.0', description='Task directory and watchdog management', requires=('acc.framework',), capabilities=('tasks.manage',), cards=(PluginCard('acc.task-battlefield.overview', '任务战场', '任务目录与看门狗', 'tasks', icon='calendar-clock', order=30),), router_factory=_mount_task_battlefield)
