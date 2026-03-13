# Centralize trafilatura.extract into Shared Utility

> **Owning task:** #537 — Centralize trafilatura.extract into shared utility
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

DRY-09 (from `docs/software-design-audit.md`): `trafilatura.extract()` is called in 3 files with divergent parameters and fallback logic. Can a single utility cover all 3?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | trafilatura docs — Python usage | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 — canonical API reference |
| 2 | trafilatura GitHub repo | <https://github.com/adbar/trafilatura> | 0.8 — confirms `extract()` params and `extract_metadata()` |
| 3 | OwlBear `content_extractor.py` | `src/owlbear/tools/browser/content_extractor.py` | 1.0 — existing richest wrapper |
| 4 | OwlBear `web_search.py` | `src/owlbear/tools/web_search.py` L204–224 | 1.0 — second call site |
| 5 | OwlBear `bookmark_pipeline.py` | `src/owlbear/memory/knowledge/bookmark_pipeline.py` L174–200 | 1.0 — third call site |

## 3. Call-Site Catalog

| Aspect | `content_extractor.py` | `web_search.py` | `bookmark_pipeline.py` |
|--------|----------------------|----------------|----------------------|
| `output_format` | `"markdown"` | `"markdown"` | default (`"txt"`) |
| `include_links` | `True` | `True` | default (`False`) |
| `url` param | Yes | Yes | No |
| Metadata extraction | `extract_metadata()` — title/author/date | None | None |
| Error handling | try/except → empty `ExtractionResult` | No try (caller handles HTTP errors) | No try (returns `None` on `extract()` → `None`) |
| Return type | `ExtractionResult` (Pydantic) | `str` (with raw HTML fallback) | `str \| None` |
| Import strategy | Module-level try/except | Module-level try/except | Lazy in-function import |

## 4. Analysis

### Can one utility cover all three?

The `extract()` call in `content_extractor.py` and `web_search.py` already use **identical parameters** (`output_format="markdown"`, `include_links=True`, `url=url`). The `bookmark_pipeline.py` call uses defaults (plain text, no links, no URL) — but since its output feeds knowledge ingestion, markdown+links is strictly better. No caller requires plain text.

**Conclusion:** Yes. `extract_content(html, url)` from `content_extractor.py` already covers the superset of behavior. The two other call sites can delegate to it.

### Where should the utility live?

| Option | Path | Pros | Cons | KISS |
|--------|------|------|------|------|
| A. Keep in place | `tools.browser.content_extractor` | Zero file moves, tested | `browser/` path misleading for non-browser callers | Medium |
| B. Promote one level | `tools.content_extractor` | Semantically neutral, small diff | 3 import paths change + move file | Medium |
| C. New core module | `core.content_extractor` | "Shared" namespace | `core/` is for framework infra, not optional-dep utils | Low |

### Recommendation (.85 confidence): Option A — keep in place

Rationale: The module already exists, is well-tested (12 test cases), and has the correct abstraction (`ExtractionResult` + `extract_content`). Moving it costs import churn for zero functional gain. The `browser/` path is slightly misleading, but Python developers care about import names, not directory aesthetics. If the browser toolset is ever extracted into its own package, the content extractor naturally comes with it.

**Option B** (.70) is defensible if the team finds the `browser/` path confusing, but violates YAGNI — rename when there's a concrete reason, not preemptively.

### Migration plan per call site

**`web_search.py`** (L213–218): Replace inline `trafilatura.extract()` call with `extract_content(response.text, url=url).text`. Keep the existing raw-HTML fallback on empty text. Remove the module-level `trafilatura` import.

**`bookmark_pipeline.py`** (L182–200): Replace `trafilatura.extract(resp.text)` with `extract_content(resp.text).text`. Remove the lazy `import trafilatura` block. The `ImportError` guard shifts to `extract_content`'s existing guard.

Both changes are < 10 lines each. No new abstractions needed.

## 5. Research Checklist

- [x] **Theoretical validity** — DRY consolidation of identical `trafilatura.extract()` calls. Sound.
- [x] **Prior art** — trafilatura docs confirm a single `extract()` API with consistent params (source #1, #2). The existing `content_extractor.py` already wraps it fully.
- [x] **Technical feasibility** — No blockers. Both `web_search.py` and `bookmark_pipeline.py` already depend on `trafilatura` via optional extras (`[search]`, `[crawl]`). Import from `content_extractor` works.
- [x] **Architecture fit** — `extract_content()` returns `ExtractionResult`; callers that only need text use `.text`. No interface changes needed.
- [x] **Implementation approach** — Import-and-delegate. ~10 lines changed per file. Remove redundant `import trafilatura` from two modules.

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Migrate web_search.py to use extract_content from content_extractor" --priority nice-to-have --status backlog --tags "dry,scope:core,phase-9" --body "Replace inline trafilatura.extract() in web_search.py L213-218 with extract_content(response.text, url=url).text. Keep raw-HTML fallback on empty .text. Remove module-level trafilatura import. See docs/centralize-trafilatura-research.md §4. AC: (1) web_search.py no longer imports trafilatura directly, (2) uses extract_content from content_extractor, (3) existing tests pass, (4) raw-HTML fallback preserved."

kanban\kanban-md.exe create "Migrate bookmark_pipeline.py to use extract_content from content_extractor" --priority nice-to-have --status backlog --tags "dry,scope:core,phase-9" --body "Replace trafilatura.extract(resp.text) in bookmark_pipeline.py L200 with extract_content(resp.text).text. Remove lazy import block (L182-186). See docs/centralize-trafilatura-research.md §4. AC: (1) bookmark_pipeline.py no longer imports trafilatura directly, (2) uses extract_content from content_extractor, (3) existing tests pass, (4) output is now markdown format (richer for knowledge ingestion)."
```
