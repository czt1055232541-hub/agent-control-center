#!/usr/bin/env python3
"""No-key web search/fetch fallback for OpenClaw agents."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone


DDG_HTML_ENDPOINT = "https://html.duckduckgo.com/html"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def fetch_text(url: str, timeout: int) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, resp.read().decode(charset, errors="replace"), None
    except Exception as exc:  # noqa: BLE001 - CLI helper should return structured errors.
        return None, "", f"{type(exc).__name__}: {exc}"


def strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def ddg_result_url(raw_url: str) -> str:
    raw_url = html.unescape(raw_url)
    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    try:
        parsed = urllib.parse.urlparse(raw_url)
        params = urllib.parse.parse_qs(parsed.query)
        if params.get("uddg"):
            return params["uddg"][0]
    except Exception:
        pass
    return raw_url


def parse_ddg(html_text: str, limit: int) -> list[dict]:
    results: list[dict] = []
    result_re = re.compile(
        r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b[^"]*")([^>]*)>(.*?)</a>',
        re.I | re.S,
    )
    snippet_re = re.compile(
        r'<a\b(?=[^>]*\bclass="[^"]*\bresult__snippet\b[^"]*")[^>]*>(.*?)</a>',
        re.I | re.S,
    )
    next_re = re.compile(r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b[^"]*")', re.I)
    for match in result_re.finditer(html_text):
        attrs, raw_title = match.group(1), match.group(2)
        href_match = re.search(r'\bhref="([^"]*)"', attrs, re.I)
        if not href_match:
            continue
        trailing = html_text[match.end() :]
        next_match = next_re.search(trailing)
        scoped = trailing[: next_match.start()] if next_match else trailing
        snippet_match = snippet_re.search(scoped)
        result = {
            "title": strip_html(raw_title),
            "url": ddg_result_url(href_match.group(1)),
            "snippet": strip_html(snippet_match.group(1)) if snippet_match else "",
        }
        if result["title"] and result["url"]:
            results.append(result)
        if len(results) >= limit:
            break
    return results


def search(query: str, limit: int, timeout: int, region: str | None) -> dict:
    params = {"q": query, "kp": "-1"}
    if region:
        params["kl"] = region
    url = DDG_HTML_ENDPOINT + "?" + urllib.parse.urlencode(params)
    status, body, error = fetch_text(url, timeout)
    payload = {
        "mode": "search",
        "query": query,
        "searched_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "duckduckgo-html",
        "status": status,
        "results": [],
        "error": error,
    }
    if body:
        if re.search(r"g-recaptcha|are you a human|challenge-form", body, re.I):
            payload["error"] = "DuckDuckGo returned a bot-detection challenge"
        payload["results"] = parse_ddg(body, limit)
    return payload


def fetch_page(url: str, timeout: int, max_chars: int) -> dict:
    status, body, error = fetch_text(url, timeout)
    text = strip_html(body)[:max_chars] if body else ""
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", body or "")
    return {
        "mode": "fetch",
        "url": url,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "title": strip_html(title_match.group(1)) if title_match else "",
        "text": text,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="No-key web search/fetch fallback.")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--fetch", help="Fetch and extract text from a URL")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--region", help="DuckDuckGo region code, e.g. us-en or cn-zh")
    parser.add_argument("--max-chars", type=int, default=8000)
    args = parser.parse_args()

    if args.fetch:
        payload = fetch_page(args.fetch, args.timeout, args.max_chars)
    elif args.query:
        payload = search(args.query, max(1, min(args.limit, 10)), args.timeout, args.region)
    else:
        parser.error("provide a query or --fetch URL")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error") and not payload.get("results") and not payload.get("text"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
