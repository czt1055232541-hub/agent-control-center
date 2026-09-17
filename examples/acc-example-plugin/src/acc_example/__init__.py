"""A small project mounted through the public ACC plugin contract."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from feishu_stack.plugin_sdk import AccPlugin, PluginCard


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/example", tags=["Example"])

    @router.get("/status")
    def status() -> dict:
        return {"ok": True, "plugin": "example.hello"}

    @router.get("/ui", response_class=HTMLResponse)
    def ui() -> str:
        return """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ACC Example</title><style>
body{font:16px system-ui;background:#f8fafc;color:#0f172a;padding:3rem}
main{max-width:640px;margin:auto;background:white;padding:2rem;border:1px solid #cbd5e1;border-radius:16px}
a{color:#0e7490}</style><main><h1>独立项目已接入 ACC</h1>
<p>此页面由外部插件提供，ACC 与 DSH 无需修改源码。</p>
<a href="/api/example/status">查看插件状态</a></main></html>"""

    return router


def create_plugin() -> AccPlugin:
    return AccPlugin(
        id="example.hello", name="Hello ACC", version="0.1.0",
        description="可独立安装的插件示例", requires=("acc.framework",),
        capabilities=("example.status",), router_factory=create_router,
        cards=(PluginCard(
            id="example.hello.card", title="Hello ACC", description="打开独立项目页面",
            page="example-hello", order=110, href="/api/example/ui",
        ),),
    )
