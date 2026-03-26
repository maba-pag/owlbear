# Migrate context_hydration.fetch_url to use extract_content

> **Owning task:** #826 — Migrate context_hydration.py to use extract_content from content_extractor
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

`src/owlbear/core/context_hydration.py::fetch_url()` still imports `trafilatura` lazily and calls `extract(..., output_format="markdown", include_links=True, url=url)` directly. `src/owlbear/tools/browser/content_extractor.py::extract_content()` already wraps the same upstream API, already owns `wrap_web_content`, and is the accepted migration target from the earlier trafilatura-centralization research. The open question for #826 is whether `fetch_url()` can delegate directly to `extract_content(...).text` without changing its behavior in the hydration pipeline.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| 1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 — canonical `extract()` parameters, Markdown output, `include_links`, and `url` handling |
| 2 | trafilatura GitHub repo / README | <https://github.com/adbar/trafilatura> | .80 — confirms maintained upstream API and Markdown-oriented extraction support |
| 3 | OwlBear shared wrapper | `src/owlbear/tools/browser/content_extractor.py` | 1.0 — exact abstraction the task wants to use |
| 4 | OwlBear current caller | `src/owlbear/core/context_hydration.py` | 1.0 — current direct import, call shape, and local wrapping branch |
| 5 | Web search precedent | `src/owlbear/tools/web_search.py`, `kanban/tasks/824-migrate-web-search-py-to-use-extract-content-from.md` | .95 — same migration pattern already accepted and implemented |
| 6 | Fetch-url test surface | `tests/test_context_hydration.py`, `tests/test_content_safety_integration.py` | .95 — identifies the exact mocks that break when direct `trafilatura` import disappears |

## 3. Analysis

### 3.1 Behavior comparison

| Aspect | `fetch_url()` today | `extract_content(resp.text, url=url).text` | Impact for #826 |
|--------|----------------------|--------------------------------------------|-----------------|
| Upstream API | Direct `trafilatura.extract()` call | Same upstream call wrapped in one place | Meets AC with less duplication |
| Extraction params | `output_format="markdown"`, `include_links=True`, `url=url` | Same params inside wrapper | No content-format regression expected |
| Wrapping | Local `wrap_web_content` branch after extraction | Wrapper already applies wrapping before returning `.text` | Local wrap branch should be removed to avoid duplicate logic |
| Empty extraction | `content or ""` | `ExtractionResult.text` is `""` on extraction failure | Same caller-visible result |
| Missing optional dependency | Lazy `import trafilatura` raises on first use | `extract_content()` raises `ImportError` on first use | Equivalent operational behavior |
| Extra work | Text only | Text plus metadata extraction | Slight overhead, but hydration is network-bound and budget-limited |

### 3.2 Migration options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Delegate directly to `extract_content(...).text` | Smallest diff, removes direct `trafilatura` import, centralizes wrapping, matches accepted `web_search` pattern | Also runs metadata extraction that `fetch_url()` ignores | **Recommended (.92)** |
| B. Add a new text-only helper in `content_extractor.py` | Avoids metadata work | New API surface for a single caller, more code and tests, no current evidence metadata cost matters | .55 |
| C. Keep direct `trafilatura` usage in `fetch_url()` | No test rewrites | Fails AC, preserves duplication, conflicts with prior research | .05 |

### 3.3 The important semantic difference from `web_search`

`web_search` needed extra acceptance criteria because it preserves a raw-HTML fallback when extraction returns empty text. `fetch_url()` does not have that branch today; it returns `""` on failed HTTP and failed extraction paths. That means #826 is simpler than #824:

- successful extraction should return `extract_content(...).text` directly
- no second `wrap_web_content` pass is needed
- no raw-HTML fallback logic needs to survive the migration

### 3.4 Test impact

- `tests/test_context_hydration.py` contains 4 direct `sys.modules["trafilatura"]` patches tied to `fetch_url()` or `hydrate()` success-path coverage.
- `tests/test_content_safety_integration.py` contains 5 fetch-url-related `sys.modules["trafilatura"]` patches, including the contrast test that proves bookmark ingestion stays unwrapped while `fetch_url()` does not.
- The prior `web_search` migration needed a dedicated RED task (#842) for the same reason. This task now has the analogous RED follow-up #864.

## 4. Recommendation (.92 confidence)

Implement #826 by importing `extract_content` into `context_hydration.py`, replacing the inline `trafilatura.extract(...)` call with `extract_content(resp.text, url=url).text`, and deleting the local `import trafilatura` plus the local `wrap_web_content` block.

Why this is the right boundary:

1. It satisfies the task acceptance criteria exactly, with the smallest possible diff.
2. It removes duplicated security behavior instead of moving it around; the wrapper already owns content wrapping.
3. It matches the architecture decision already accepted for `web_search`, but without that task's raw-fallback complexity.
4. The only meaningful downstream work is test rewiring, not additional production abstraction.

Risk to note: `extract_content()` also runs metadata extraction. If profiling later shows hydration is CPU-bound on large batches, split out a text-only helper in a separate task. Current evidence does not justify that extra API now.

## 5. Follow-up Tasks

1. **Existing task #826** — implement the production migration exactly as above; no additional architecture split is needed.
2. **Created task #864** — update the fetch-url tests to mock `extract_content` instead of `trafilatura`.

```powershell
kanban\kanban-md.exe create "Update context_hydration tests to mock extract_content instead of trafilatura" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED phase for #826. Update fetch_url-related tests in tests/test_context_hydration.py and tests/test_content_safety_integration.py that currently patch trafilatura via sys.modules to patch owlbear.core.context_hydration.extract_content instead. Source: docs/research/context-hydration-extract-content.md. AC: (1) 4 trafilatura mocks in tests/test_context_hydration.py are replaced with extract_content or ExtractionResult-based mocks, (2) 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced likewise, (3) wrapping assertions are preserved by controlling ExtractionResult.text values, (4) scoped tests pass."
```
