# Re-scope bookmark_pipeline extraction migration

> **Owning task:** #825 — Migrate bookmark_pipeline.py to use extract_content from content_extractor
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

`src/owlbear/memory/knowledge/bookmark_pipeline.py::_default_web_read()` still calls `trafilatura.extract(resp.text)` directly, which gives plain-text output and keeps bookmark ingestion unwrapped. Task #825 currently asks to replace that call with `extract_content(resp.text).text` from `src/owlbear/tools/browser/content_extractor.py`. The question is whether that is still the correct migration target after OwlBear's content-wrapping work and the current layering rules.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| 1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 — canonical output-format, `include_links`, and `url` behavior |
| 2 | trafilatura GitHub repo / README | <https://github.com/adbar/trafilatura> | .80 — confirms maintained upstream Markdown extraction support |
| 3 | OwlBear architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 — `memory/` must not import from `tools/` |
| 4 | Current bookmark caller | `src/owlbear/memory/knowledge/bookmark_pipeline.py` | 1.0 — current import behavior, plain-text output, and retry flow |
| 5 | Current shared wrapper | `src/owlbear/tools/browser/content_extractor.py` | 1.0 — wraps output and lives in `tools/` |
| 6 | Wrapping exclusion decision | `kanban/tasks/725-add-untrusted-content-wrapping-for-web-extracted.md`, `tests/test_content_safety_integration.py` | 1.0 — bookmark ingestion is intentionally excluded from untrusted-content wrapping |
| 7 | Leaf-module precedent | `src/owlbear/paths.py` | .90 — package-root leaf utility pattern already exists |
| 8 | Sibling migration review | `kanban/tasks/826-migrate-context-hydration-py-to-use-extract.md` | .85 — architect already blocked the same cross-layer reuse pattern for `core -> tools` |

## 3. Analysis

### 3.1 Behavior and architecture comparison

| Aspect | Current `_default_web_read()` | Direct `extract_content(...).text` | Leaf `extract_markdown(...)` helper |
|--------|-------------------------------|------------------------------------|-------------------------------------|
| Layering | Legal today: `memory/` talks to upstream lib directly | Invalid: `memory/` would import from `tools/` | Legal: `memory/` can import a package-root leaf module |
| Output format | Default TXT, no links | Markdown with links | Markdown with links |
| Wrapping | None | Wrapped when `wrap_web_content=True` | None |
| Shared logic | Duplicated trafilatura call | Centralized, but mixed with higher-layer policy | Centralized without policy leakage |
| Metadata work | None | Runs metadata extraction too | None unless a caller asks for it |
| Import guard | Local lazy `ImportError` message | Guard handled in wrapper | Shared first-use guard can stay in one place |
| Test impact | Existing tests patch `trafilatura` | Tests must rewire and would also need no-wrap guarantees | Tests must rewire, but the no-wrap contract stays intact |

Two facts make the current AC stale:

1. `extract_content()` is no longer just a raw trafilatura wrapper. It also applies `wrap_web_content`, which archived task #725 and the contrast test in `tests/test_content_safety_integration.py` explicitly exclude from bookmark ingestion.
2. Importing `src/owlbear/tools/browser/content_extractor.py` from `src/owlbear/memory/knowledge/bookmark_pipeline.py` would add a new `memory -> tools` dependency that the architecture standards reject.

### 3.2 Option comparison

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Reuse `tools/browser/content_extractor.py` directly | Smallest diff, removes direct `trafilatura` import | Breaks layering, adds wrapping to stored content, pulls in unused metadata work | .15 |
| B. Keep local `trafilatura` call but switch to Markdown params | Legal, preserves raw storage, small diff | Leaves DRY problem in place and does not help sibling task #826 | .55 |
| C. Introduce a package-root leaf helper for raw Markdown extraction, then migrate bookmark code to it | Legal layering, preserves unwrapped storage, centralizes the upstream call, and gives #826 a valid future target too | Adds one small module and focused tests | **.90** |

### 3.3 What the recommended helper should own

The shared helper should do exactly one thing: centralize `trafilatura.extract(html, output_format="markdown", include_links=True, url=url)` and return raw text.

It should **not**:

- import `OwlBearSettings`
- call `wrap_untrusted_content`
- live in `core/`, `tools/`, or `memory/`
- extract metadata unless a caller explicitly needs that in a separate API

This follows the existing `src/owlbear/paths.py` pattern: a package-root leaf module that multiple layers can import without inverting dependencies.

## 4. Recommendation (.90 confidence)

Do not implement #825 exactly as written. Instead:

1. add a package-root leaf module such as `src/owlbear/web_extract.py` with `extract_markdown(html: str, url: str | None = None) -> str`
2. keep higher-layer concerns where they belong: `tools/browser/content_extractor.py` can continue to own metadata extraction and wrapping for direct-to-LLM paths
3. refine #825 so `bookmark_pipeline.py` imports the new leaf helper, producing Markdown output while preserving the no-wrapping contract for stored knowledge

This is the smallest change that solves the root design problem instead of baking a layer violation into `memory/`.

## 5. Follow-up Tasks

1. **Existing task #825** — refine the implementation AC to use `owlbear.web_extract.extract_markdown`, preserve unwrapped storage, and verify Markdown output rather than `extract_content().text`.
2. **Created #868** — build the shared leaf helper.
3. **Created #867** — update bookmark-path tests to patch the new helper instead of direct `trafilatura` imports.

```powershell
kanban\kanban-md.exe create "Create leaf markdown extraction helper for cross-layer callers" --priority nice-to-have --status ideation --tags "dry,type:build,scope:core,phase-9" ...

kanban\kanban-md.exe create "Update bookmark_pipeline tests to mock extract_markdown instead of trafilatura" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" ...
```
