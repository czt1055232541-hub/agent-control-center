#!/usr/bin/env python3
"""Small public-API academic search helper for OpenClaw agents."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


USER_AGENT = "openclaw-academic-search/1.0 (mailto:research@example.invalid)"


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_json(url: str, timeout: int = 20) -> dict:
    return json.loads(fetch_text(url, timeout=timeout))


def compact_authors(authors, limit: int = 6) -> list[str]:
    out: list[str] = []
    for author in authors or []:
        if isinstance(author, str):
            name = author
        elif "author" in author:
            person = author.get("author") or {}
            name = person.get("display_name") or " ".join(
                part for part in [person.get("given"), person.get("family")] if part
            )
        else:
            name = author.get("name") or " ".join(
                part for part in [author.get("given"), author.get("family")] if part
            )
        if name:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def normalize_title(value) -> str:
    if isinstance(value, list):
        return " ".join(str(x) for x in value if x).strip()
    return str(value or "").strip()


def doi_url(doi: str | None) -> str | None:
    if not doi:
        return None
    return "https://doi.org/" + doi.strip().removeprefix("https://doi.org/")


def search_openalex(query: str, limit: int) -> list[dict]:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"search": query, "per-page": limit}
    )
    data = fetch_json(url)
    results = []
    for item in data.get("results", []):
        doi = item.get("doi")
        results.append(
            {
                "source": "OpenAlex",
                "title": normalize_title(item.get("title") or item.get("display_name")),
                "year": item.get("publication_year"),
                "authors": compact_authors(item.get("authorships")),
                "venue": (item.get("primary_location") or {}).get("source", {}).get("display_name"),
                "doi": doi,
                "url": doi or item.get("id"),
                "citations": item.get("cited_by_count"),
                "abstract": None,
            }
        )
    return results


def search_crossref(query: str, limit: int) -> list[dict]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query": query, "rows": limit}
    )
    data = fetch_json(url)
    results = []
    for item in data.get("message", {}).get("items", []):
        doi = item.get("DOI")
        year_parts = (
            item.get("published-print")
            or item.get("published-online")
            or item.get("issued")
            or {}
        ).get("date-parts", [[]])
        year = year_parts[0][0] if year_parts and year_parts[0] else None
        results.append(
            {
                "source": "Crossref",
                "title": normalize_title(item.get("title")),
                "year": year,
                "authors": compact_authors(item.get("author")),
                "venue": normalize_title(item.get("container-title")),
                "doi": doi,
                "url": doi_url(doi) or item.get("URL"),
                "citations": item.get("is-referenced-by-count"),
                "abstract": None,
            }
        )
    return results


def search_semantic_scholar(query: str, limit: int) -> list[dict]:
    fields = "title,authors,year,venue,citationCount,externalIds,url,abstract"
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(
        {"query": query, "limit": limit, "fields": fields}
    )
    data = fetch_json(url)
    results = []
    for item in data.get("data", []):
        external = item.get("externalIds") or {}
        doi = external.get("DOI")
        arxiv = external.get("ArXiv")
        results.append(
            {
                "source": "Semantic Scholar",
                "title": normalize_title(item.get("title")),
                "year": item.get("year"),
                "authors": compact_authors(item.get("authors")),
                "venue": item.get("venue"),
                "doi": doi,
                "url": doi_url(doi) or (f"https://arxiv.org/abs/{arxiv}" if arxiv else item.get("url")),
                "citations": item.get("citationCount"),
                "abstract": item.get("abstract"),
            }
        )
    return results


def search_arxiv(query: str, limit: int) -> list[dict]:
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f"all:{query}", "start": 0, "max_results": limit}
    )
    text = fetch_text(url)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(text)
    results = []
    for entry in root.findall("atom:entry", ns):
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = entry.findtext("atom:published", default="", namespaces=ns)
        arxiv_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        results.append(
            {
                "source": "arXiv",
                "title": normalize_title(entry.findtext("atom:title", default="", namespaces=ns)),
                "year": published[:4] if published else None,
                "authors": compact_authors(authors),
                "venue": "arXiv",
                "doi": entry.findtext("arxiv:doi", default=None, namespaces=ns),
                "url": arxiv_id,
                "citations": None,
                "abstract": normalize_title(entry.findtext("atom:summary", default="", namespaces=ns)),
            }
        )
    return results


SEARCHERS = {
    "openalex": search_openalex,
    "crossref": search_crossref,
    "semanticscholar": search_semantic_scholar,
    "arxiv": search_arxiv,
}


def dedupe(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for rec in records:
        key = rec.get("doi") or rec.get("url") or rec.get("title", "").lower()
        key = str(key).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Search public academic APIs.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Results per source")
    parser.add_argument(
        "--source",
        choices=["all", *SEARCHERS.keys()],
        default="all",
        help="Source to query",
    )
    parser.add_argument("--sleep", type=float, default=0.25, help="Pause between API calls")
    args = parser.parse_args()

    sources = list(SEARCHERS) if args.source == "all" else [args.source]
    payload = {
        "query": args.query,
        "searched_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "results": [],
        "errors": [],
    }

    for source in sources:
        try:
            payload["results"].extend(SEARCHERS[source](args.query, max(1, args.limit)))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ET.ParseError) as exc:
            payload["errors"].append({"source": source, "error": str(exc)})
        time.sleep(args.sleep)

    payload["results"] = dedupe(payload["results"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["results"] else 2


if __name__ == "__main__":
    sys.exit(main())
