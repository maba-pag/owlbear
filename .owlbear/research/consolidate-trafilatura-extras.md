# Consolidate trafilatura Across Extras Groups

> **Owning task:** #569 — Consolidate trafilatura across extras groups
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

F-08 from `docs/config-dependency-audit.md`: `trafilatura>=2.0.0` appears in both `crawl` and `search` extras. `bookmark_pipeline.py` also uses it but its `knowledge` extra doesn't declare it. Should we create a shared `web` extra, or is the current layout fine?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python Packaging Guide — pyproject.toml | <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/> | .90 |
| 2 | uv docs — optional dependencies | <https://docs.astral.sh/uv/concepts/projects/dependencies/#optional-dependencies> | .90 |
| 3 | httpx pyproject.toml | <https://github.com/encode/httpx/blob/master/pyproject.toml> | .85 |
| 4 | pydantic pyproject.toml | <https://github.com/pydantic/pydantic/blob/main/pyproject.toml> | .80 |
| 5 | OwlBear #537 research | `docs/research/centralize-trafilatura.md` | 1.0 |

## 3. Current State

### Extras that include trafilatura

```toml
crawl = ["trafilatura>=2.0.0"]                       # L30
search = ["duckduckgo-search>=7.0", "trafilatura>=2.0.0"]  # L32
```

### Files that import trafilatura

| File | Import style | Guard? | Extras hint in error |
|------|-------------|--------|---------------------|
| `tools/browser/content_extractor.py` | Module-level try/except | Yes | `owlbear[crawl]` |
| `tools/web_search.py` | Module-level try/except | Yes | `owlbear[search]` |
| `memory/knowledge/bookmark_pipeline.py` | Lazy in-function | Yes (#500) | `owlbear[search]` |

### Key context: #537 will eliminate 2 of 3 import sites

Task #537 (backlog) centralizes all `trafilatura.extract()` calls into `content_extractor.py`. After #537, `web_search.py` and `bookmark_pipeline.py` will import `extract_content` from `content_extractor.py` instead of importing trafilatura directly. Only `content_extractor.py` will remain as the single trafilatura consumer.

## 4. Analysis

| Option | Description | Pros | Cons | KISS |
|--------|------------|------|------|------|
| A. Shared `web` extra | `web=["trafilatura>=2.0.0"]`; crawl/search self-ref as `owlbear[web]` | Single source of truth | Self-ref extras are fragile; some tools handle poorly; 1 extra to save 1 line | Low |
| B. Keep duplication | Leave both extras declaring `trafilatura>=2.0.0`; add inline comment | Zero churn; follows httpx/pydantic idiom | 1 line duplicated | **High** |
| C. Merge crawl into search | Drop `crawl` extra, keep only `search` | Fewer extras | Breaks `uv sync --extra crawl` for existing users; conflates semantics | Low |
| D. Add to knowledge | Add `trafilatura>=2.0.0` to `knowledge` extra | bookmark_pipeline declares its own dep | After #537, bookmark_pipeline won't import trafilatura directly — wasteful | Low |

### Prior art

- **httpx**: 5 extras (brotli, cli, http2, socks, zstd) — all flat, self-contained, no cross-refs.
- **pydantic**: extras (email, timezone) are flat. Cross-refs only in `dependency-groups` (dev tooling), not `optional-dependencies`.
- **Python Packaging Guide**: no mechanism for extras to include other extras. Self-referencing (`owlbear[web]`) is technically valid per PEP 508 but non-idiomatic and fragile with some build tools.

### Why duplication is fine

1. The duplication is **1 line** (`trafilatura>=2.0.0`). Creating an extra to DRY one line violates YAGNI.
2. After #537, `bookmark_pipeline.py` delegates to `content_extractor.py` — the "knowledge doesn't declare trafilatura" issue **resolves itself**.
3. `crawl` and `search` have distinct semantic intent. A user installing `crawl` wants browser content extraction. A user installing `search` wants web search + page reading. Both independently need trafilatura.
4. The `crawl` extra may grow (e.g., `beautifulsoup4` for fallback parsing). Keeping it separate preserves that extensibility.

## 5. Recommendation (.90 confidence)

**Option B — keep duplication, add inline comment, document install guidance.**

The only action needed is:

1. Add a `# shared with search` / `# shared with crawl` comment in pyproject.toml for maintainer clarity.
2. Update `content_extractor.py` import guard message to mention both extras: `"uv sync --extra crawl"` or `"uv sync --extra search"`.
3. Wait for #537 to complete — it eliminates the `bookmark_pipeline.py` direct dependency entirely.

No structural changes to extras groups required.

## 6. Follow-up Tasks

```shell
kanban\kanban-md.exe create "Add pyproject.toml comments for shared trafilatura dep" --priority nice-to-have --status backlog --tags "config,deps,phase-9" --body "Add inline comments to pyproject.toml explaining trafilatura duplication across crawl and search extras (intentional, per docs/research/consolidate-trafilatura-extras.md). Update content_extractor.py import guard to mention both --extra crawl and --extra search. AC: (1) pyproject.toml crawl/search lines have clarifying comments, (2) content_extractor.py ImportError message mentions both extras, (3) uv lock succeeds."
```

Note: #537 (backlog) already covers the `bookmark_pipeline.py` migration that eliminates its direct trafilatura import. No additional task needed for that.
