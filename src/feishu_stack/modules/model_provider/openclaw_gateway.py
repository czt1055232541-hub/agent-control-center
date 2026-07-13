from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import is_port_listening, pids_by_port, start_process, stop_component, wait_for_port, write_pid


def _ensure_feishu_a2a_runtime(cfg: StackConfig) -> None:
    if not cfg.openclaw.a2a_bots:
        return
    _ensure_feishu_raw_post_config(cfg)
    _ensure_feishu_send_patch(cfg)


def _ensure_feishu_raw_post_config(cfg: StackConfig) -> None:
    config_path = cfg.openclaw_home / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return
    data = json.loads(config_path.read_text(encoding="utf-8"))
    feishu = data.setdefault("channels", {}).setdefault("feishu", {})
    changed = False
    if feishu.get("renderMode") != "raw":
        feishu["renderMode"] = "raw"
        changed = True
    if feishu.get("streaming") is not False:
        feishu["streaming"] = False
        changed = True
    if "blockStreaming" in feishu:
        feishu.pop("blockStreaming", None)
        changed = True
    accounts = feishu.get("accounts")
    account_iter = accounts if isinstance(accounts, list) else accounts.values() if isinstance(accounts, dict) else []
    for account in account_iter:
        if not isinstance(account, dict):
            continue
        if account.get("renderMode") != "raw":
            account["renderMode"] = "raw"
            changed = True
        if account.get("streaming") is not False:
            account["streaming"] = False
            changed = True
        if "blockStreaming" in account:
            account.pop("blockStreaming", None)
            changed = True
    if changed:
        config_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")


def _ensure_feishu_send_patch(cfg: StackConfig) -> None:
    package_root = cfg.openclaw_home / ".openclaw" / "npm" / "projects" / "openclaw-feishu-dc69f44688"
    send_file = package_root / "node_modules" / "@openclaw" / "feishu" / "dist" / "send-B3kteMF8.js"
    if not send_file.exists():
        return
    text = send_file.read_text(encoding="utf-8")
    if "function resolveA2AMentionTargets()" in text and "function shouldAutoMentionCoordinator(" in text:
        return
    needle = """function buildFeishuPostMessagePayload(params) {
\tconst { messageText } = params;
\treturn {
\t\tcontent: JSON.stringify({ zh_cn: { content: [[{
\t\t\ttag: "md",
\t\t\ttext: messageText
\t\t}]] } }),
\t\tmsgType: "post"
\t};
}
"""
    replacement = """function buildFeishuPostMessagePayload(params) {
\tconst { messageText } = params;
\tconst a2aElements = buildA2APostElements(messageText);
\tif (a2aElements) return {
\t\tcontent: JSON.stringify({ zh_cn: { content: [a2aElements] } }),
\t\tmsgType: "post"
\t};
\treturn {
\t\tcontent: JSON.stringify({ zh_cn: { content: [[{
\t\t\ttag: "md",
\t\t\ttext: messageText
\t\t}]] } }),
\t\tmsgType: "post"
\t};
}
function resolveA2AMentionTargets() {
\tconst raw = process.env.OPENCLAW_FEISHU_A2A_BOTS;
\tif (!raw) return [];
\ttry {
\t\tconst parsed = JSON.parse(raw);
\t\tif (!Array.isArray(parsed)) return [];
\t\treturn parsed.map((entry) => {
\t\t\tif (!entry || typeof entry !== "object") return null;
\t\t\tconst openId = normalizeFeishuExternalKey(toStringOrEmpty(entry.openId));
\t\t\tconst name = toStringOrEmpty(entry.name).trim();
\t\t\tif (!openId || !name) return null;
\t\t\tconst aliases = Array.isArray(entry.aliases) ? entry.aliases.map((alias) => toStringOrEmpty(alias).trim()).filter(Boolean) : [];
\t\t\treturn {
\t\t\t\topenId,
\t\t\t\tname,
\t\t\t\taliases: [...new Set([name, ...aliases])]
\t\t\t};
\t\t}).filter(Boolean);
\t} catch {
\t\treturn [];
\t}
}
function buildA2APostElements(messageText) {
\tconst targets = resolveA2AMentionTargets();
\tif (targets.length === 0) return null;
\tlet text = messageText;
\tif (!hasA2AMentionSyntax(text, targets) && shouldAutoMentionCoordinator(text)) {
\t\tconst coordinator = targets.find((target) => target.name === "项目调度官");
\t\tif (coordinator) text = `@${coordinator.name} ${text}`;
\t}
\tconst aliases = [];
\tfor (const target of targets) for (const alias of target.aliases) aliases.push({
\t\talias,
\t\ttarget
\t});
\taliases.sort((a, b) => b.alias.length - a.alias.length);
\tconst elements = [];
\tlet cursor = 0;
\tlet matched = false;
\twhile (cursor < text.length) {
\t\tlet hit;
\t\tfor (const candidate of aliases) {
\t\t\tconst prefix = text[cursor];
\t\t\tif (prefix !== "@" && prefix !== "＠") continue;
\t\t\tconst start = cursor + 1;
\t\t\tconst slice = text.slice(start, start + candidate.alias.length);
\t\t\tif (slice.toLowerCase() === candidate.alias.toLowerCase()) {
\t\t\t\thit = candidate;
\t\t\t\tbreak;
\t\t\t}
\t\t}
\t\tif (!hit) {
\t\t\tconst nextAt = findNextAt(text, cursor + 1);
\t\t\tconst end = nextAt === -1 ? text.length : nextAt;
\t\t\telements.push({ tag: "text", text: text.slice(cursor, end) });
\t\t\tcursor = end;
\t\t\tcontinue;
\t\t}
\t\tif (!matched) {
\t\t\telements.push({
\t\t\t\ttag: "at",
\t\t\t\tuser_id: hit.target.openId,
\t\t\t\tuser_name: hit.target.name
\t\t\t});
\t\t} else {
\t\t\telements.push({ tag: "text", text: `＠${hit.target.name}` });
\t\t}
\t\tcursor += 1 + hit.alias.length;
\t\tmatched = true;
\t}
\treturn matched ? elements.filter((element) => element.tag !== "text" || element.text) : null;
}
function hasA2AMentionSyntax(value, targets) {
\tconst lower = value.toLowerCase();
\tfor (const target of targets) {
\t\tfor (const alias of target.aliases) {
\t\t\tconst normalized = alias.toLowerCase();
\t\t\tif (lower.includes(`@${normalized}`) || lower.includes(`＠${normalized}`)) return true;
\t\t}
\t}
\treturn false;
}
function shouldAutoMentionCoordinator(value) {
\tif (/派发完成|watchdog\\s*倒计时|看护倒计时|轻推一下|催促/i.test(value)) return false;
\treturn /审计报告|验证完成|归档完成|任务完成|审计结论|验证结论|不通过|通过/.test(value);
}
function findNextAt(value, start) {
\tconst normal = value.indexOf("@", start);
\tconst fullwidth = value.indexOf("＠", start);
\tif (normal === -1) return fullwidth;
\tif (fullwidth === -1) return normal;
\treturn Math.min(normal, fullwidth);
}
"""
    if needle not in text:
        raise RuntimeError("OpenClaw Feishu send patch target not found; package version may have changed.")
    send_file.write_text(text.replace(needle, replacement), encoding="utf-8")

def _gateway_command(cfg: StackConfig) -> list[str]:
    return ["cmd.exe", "/d", "/c", str(cfg.openclaw_gateway_cmd)]


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(cfg.openclaw_port):
        return OperationResult(True, "openclaw", "start", "OpenClaw Gateway is already listening.", port=cfg.openclaw_port)
    _ensure_feishu_a2a_runtime(cfg)
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = str(cfg.openclaw_home)
    env["OPENCLAW_GATEWAY_PORT"] = str(cfg.openclaw_port)
    env.setdefault("TMPDIR", str(Path.home() / "AppData" / "Local" / "Temp"))
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(proxy_key, None)
    if cfg.openclaw.a2a_bots:
        env["OPENCLAW_FEISHU_A2A_BOTS"] = json.dumps(cfg.openclaw.a2a_bots, ensure_ascii=False)
    proc = start_process(
        _gateway_command(cfg),
        cwd=cfg.openclaw_home,
        stdout_log=cfg.openclaw_stdout_log,
        stderr_log=cfg.openclaw_stderr_log,
        env=env,
    )
    ready = wait_for_port(cfg.openclaw_port, True, timeout=480)
    port_pids = pids_by_port(cfg.openclaw_port) if ready else []
    write_pid(cfg.pid_openclaw, port_pids[0] if port_pids else proc.pid)
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=ready,
        component="openclaw",
        action="start",
        message="OpenClaw Gateway started." if ready else "OpenClaw Gateway did not become ready.",
        pid=port_pids[0] if port_pids else proc.pid,
        port=cfg.openclaw_port,
        stdout_log=str(cfg.openclaw_stdout_log),
        stderr_log=str(cfg.openclaw_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    return stop_component(
        component="openclaw",
        pid_file=cfg.pid_openclaw,
        port=cfg.openclaw_port,
        expected_process_markers=("openclaw", "gateway.cmd"),
    )


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result


def _read_gateway_token(cfg: StackConfig) -> str | None:
    config_path = cfg.openclaw_home / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    token = data.get("gateway", {}).get("auth", {}).get("token")
    return str(token).strip() if token else None


def ui_url(config: StackConfig | None = None) -> str:
    cfg = config or load_config()
    token = _read_gateway_token(cfg)
    base = f"http://127.0.0.1:{cfg.openclaw_port}/"
    return f"{base}#token={token}" if token else base


def open_ui(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    url = ui_url(cfg)
    os.startfile(url)
    return OperationResult(
        ok=True,
        component="openclaw",
        action="open-ui",
        message="OpenClaw Control UI opened in the default browser.",
        port=cfg.openclaw_port,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
