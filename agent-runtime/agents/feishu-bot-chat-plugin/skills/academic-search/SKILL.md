---
name: academic-search
description: |
  学术搜索与论文检索工作流。Use this skill when a user asks for academic literature search,
  paper recommendations, research background, DOI/arXiv/PubMed lookup, citation evidence,
  survey-style summaries, or asks to find recent papers on a topic.
---

# Academic Search

## Core Rules

- Prefer primary scholarly indexes and publisher records over general web snippets.
- Use live search for recent, niche, or citation-sensitive claims. Record the search date.
- Do not invent papers, authors, DOI values, venues, citation counts, abstracts, or links.
- Cite each paper with enough information to verify it: title, year, venue/source, DOI or stable URL.
- Separate evidence from interpretation. Say when a conclusion is inferred from abstracts only.
- Avoid scraping Google Scholar directly. Use OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed, DOAJ, publisher pages, or institutional repositories instead.

## Search Workflow

1. Restate the research question, field, time window, and inclusion/exclusion criteria.
2. Build 2-4 query variants with synonyms, acronyms, and key methods.
3. Search at least two scholarly sources when practical:
   - OpenAlex for broad cross-field discovery and metadata.
   - Crossref for DOI and publisher records.
   - Semantic Scholar for abstracts, citation counts, and related-paper discovery.
   - arXiv for preprints in CS, math, physics, statistics, quantitative biology, and related areas.
   - PubMed for biomedical and clinical topics.
4. Deduplicate by DOI first, then arXiv ID, then normalized title.
5. Rank papers by relevance, recency, venue/source quality, citation signal, and whether the full text is available.
6. Read abstracts or full text when available before summarizing. If only metadata was checked, say so.
7. Deliver a compact bibliography plus a synthesis of themes, disagreements, and gaps.

## Local Helper

If local filesystem access is available, use this helper for a first pass:

```bash
python agents/feishu-bot-chat-plugin/skills/academic-search/scripts/academic_search.py "query" --limit 8
```

For the active OpenClaw plugin install, the same helper may be under:

```bash
python E:/openclaw/clawclaw/.openclaw/npm/projects/feishu-bot-chat/node_modules/feishu-bot-chat/skills/academic-search/scripts/academic_search.py "query" --limit 8
```

The helper returns normalized JSON records from public APIs. Treat it as discovery, not final proof.

## Output Format

For each selected paper:

- `Title`:
- `Authors`:
- `Year / Venue`:
- `DOI / URL`:
- `Why it matters`:
- `Caveat`:

End with:

- `Search date`:
- `Sources searched`:
- `Query variants`:
- `What I could not verify`:
