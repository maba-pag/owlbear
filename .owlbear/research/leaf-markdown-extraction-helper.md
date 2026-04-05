# Leaf Markdown Extraction Helper for Cross-Layer Callers

> **Owning task:** #868 — Create leaf markdown extraction helper for cross-layer callers
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Archived research #537 concluded that `src/owlbear/tools/browser/content_extractor.py::extract_content()` was the right shared utility for every `trafilatura.extract()` call site. Follow-on architecture review narrowed that conclusion: `memory/` and `core/` callers cannot legally import from `tools/`, and bookmark ingestion must stay raw and unwrapped. Task #868 asks whether the correct fix is a package-root leaf helper `src/owlbear/web_extract.py::extract_markdown()` rather than more direct reuse of `extract_content()`.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| 1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 — canonical `extract()` parameters, Markdown output, `include_links`, and `url` behavior |
| 2 | adbar/trafilatura | <https://github.com/adbar/trafilatura> | .85 — upstream Markdown support and optional-dependency context |
| 3 | Archived shared-wrapper research | `docs/research/centralize-trafilatura.md`, `kanban/tasks/537-centralize-trafilatura-extract-into-shared-utility.md` | 1.0 — previous conclusion to validate and narrow |
| 4 | OwlBear architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 — `core/` and `memory/` may not import `tools/` |
| 5 | Current wrapped helper | `src/owlbear/tools/browser/content_extractor.py` | 1.0 — shows metadata extraction, settings access, and wrapping |
| 6 | Current lower-layer callers | `src/owlbear/memory/knowledge/bookmark_pipeline.py`, `src/owlbear/core/context_hydration.py` | 1.0 — callers that need raw Markdown without higher-layer policy |
| 7 | Leaf-module precedent | `src/owlbear/paths.py` | .90 — accepted package-root leaf utility pattern |
| 8 | Downstream board context | `kanban/tasks/825-migrate-bookmark-pipeline-py-to-use-web-extract.md`, `kanban/tasks/826-migrate-context-hydration-py-to-use-extract.md`, `kanban/tasks/867-update-bookmark-pipeline-tests-to-mock-extract.md`, `kanban/tasks/869-update-context-hydration-tests-to-mock-extract.md`, `kanban/tasks/873-migrate-context-hydration-py-to-use-web-extract.md` | .95 — confirms consumer chain and existing RED/GREEN split |
| 9 | Current tests | `tests/test_bookmark_pipeline.py`, `tests/test_content_safety_integration.py`, `tests/test_content_extractor.py` | .90 — verifies no-wrap and wrapper-specific expectations |

## 3. Analysis

### 3.1 Why the older "just use extract_content() everywhere" answer no longer holds

| Claim from #537 | New evidence | Result |
|---|---|---|
| `extract_content()` is the canonical shared utility | `extract_content()` now imports `OwlBearSettings` and may call `wrap_untrusted_content`; #825 and #826 reviews both reject lower-layer imports from `tools/` | Too broad; only valid for `tools/` callers |
| `bookmark_pipeline.py` can import-and-delegate to `content_extractor` | `memory/` may not import `tools/`; bookmark ingestion must remain raw and unwrapped | Invalid |
| `context_hydration.py` can import-and-delegate to `content_extractor` | `core/` may not import `tools/`; `fetch_url()` still owns its local wrapping branch | Invalid |
| No new abstraction is needed | `core/` and `memory/` now share the same raw-Markdown contract without the same wrapper policy | New leaf abstraction is warranted |

### 3.2 Option comparison

| Option | Layer legality | Raw/unwrapped output | DRY effect | Downstream fit | Recommendation |
|---|---|---|---|---|---|
| A. Keep local `trafilatura.extract()` calls in each lower-layer caller | Legal | Caller-controlled | Low | Duplicates call shape and import guard in multiple places | .35 |
| B. Reuse `tools.browser.content_extractor.extract_content().text` directly | Illegal for `core/` and `memory/` | No: wrapped/settings-aware in some flows | Medium | Conflicts with no-wrap and layering rules | .10 |
| C. Add package-root `owlbear.web_extract.extract_markdown()` leaf helper | Legal for `core/`, `memory/`, and `tools/` | Yes: helper owns only raw Markdown extraction | High | Supports #825 and #873 without policy leakage | **.94** |

### 3.3 What the helper should and should not own

| Concern | `web_extract.extract_markdown()` | `content_extractor.extract_content()` |
|---|---|---|
| Lazy optional-dependency import | Yes | Can reuse helper or keep local guard |
| `trafilatura.extract(..., output_format="markdown", include_links=True, url=url)` | Yes | Should delegate after #868 |
| `extract_metadata()` | No | Yes |
| `OwlBearSettings` / `wrap_untrusted_content` | No | Yes |
| Return type | `str` | `ExtractionResult` |
| Intended consumers | Cross-layer raw callers | Tools-layer wrapped/metadata callers |

This split is the smallest boundary that satisfies both KISS and the architecture rules. `src/owlbear/paths.py` is the existing package-root leaf precedent for this pattern.

### 3.4 Testing strategy

- Add focused unit tests for the helper itself: success path, `url` forwarding, empty-string fallback when extraction returns `None` or raises, and missing-dependency `ImportError`.
- Use the existing downstream RED tasks already on the board for consumer rewiring:
  - #867 for `bookmark_pipeline.py`
  - #869 for `context_hydration.py`
- Preserve the contrast invariant in `tests/test_content_safety_integration.py`: bookmark ingestion stays unwrapped, while `fetch_url()` still owns wrapping locally.

## 4. Recommendation (.94 confidence)

Implement #868 as a package-root leaf module `src/owlbear/web_extract.py` with a single raw API:

`extract_markdown(html: str, url: str | None = None) -> str`

Design constraints:

- lazy-import `trafilatura` on first use
- raise an actionable `ImportError` when the dependency is missing
- call `trafilatura.extract(html, output_format="markdown", include_links=True, url=url)`
- return `""` on `None` or extraction exceptions
- import no `owlbear.core`, `owlbear.tools`, `owlbear.memory`, `owlbear.agents`, wrapping helpers, or settings

This narrows, rather than fully reverses, the archived #537 conclusion:

- `extract_content()` remains the right higher-level API for `tools/` callers that want metadata and wrapping
- `web_extract.extract_markdown()` becomes the right shared API for lower-layer raw callers and for future code that only needs the raw text

## 5. Follow-up Tasks

1. Existing #867 — RED tests for bookmark pipeline after #868.
   Priority: nice-to-have. Dependencies: #868 then #825. AC: patch `bookmark_pipeline.extract_markdown` and keep the no-wrap assertion.
2. Existing #825 — GREEN bookmark migration.
   Priority: nice-to-have. Dependencies: #867, #868. AC: `bookmark_pipeline._default_web_read()` delegates to `owlbear.web_extract.extract_markdown`.
3. Existing #869 — RED tests for context hydration after #868.
   Priority: nice-to-have. Dependencies: #868 then #873. AC: patch `context_hydration.extract_markdown` and preserve wrapping assertions.
4. Existing #873 — GREEN context hydration migration.
   Priority: nice-to-have. Dependencies: #869, #868. AC: `fetch_url()` delegates to `owlbear.web_extract.extract_markdown` but keeps local wrapping.
5. New — Add RED tests for `owlbear.web_extract.extract_markdown`.
   Priority: nice-to-have because #868 currently has no paired RED task. Dependencies: none. AC: focused helper tests fail before implementation for success, `url`, empty fallback, and missing dependency.
6. New — Refactor `content_extractor.extract_content()` to reuse `owlbear.web_extract.extract_markdown` for text extraction.
   Priority: nice-to-have DRY cleanup after #868. Dependencies: #868. AC: wrapped/metadata semantics stay unchanged while the raw `trafilatura.extract()` call becomes single-sourced.

```powershell
kanban\kanban-md.exe create "Add RED tests for owlbear.web_extract.extract_markdown" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED phase for #868. Add focused tests for src/owlbear/web_extract.py covering successful markdown extraction, url forwarding, empty-string fallback when trafilatura.extract returns None or raises, and actionable ImportError behavior when trafilatura is missing. Source: docs/research/leaf-markdown-extraction-helper.md. AC: (1) focused helper tests exist, (2) success and url-forwarding cases patch the helper's trafilatura seam and assert markdown + url behavior, (3) None/exception paths assert empty-string fallback, (4) missing-dependency path asserts actionable ImportError, (5) scoped tests fail before #868 is implemented."

kanban\kanban-md.exe create "Refactor content_extractor to reuse web_extract.extract_markdown" --priority nice-to-have --status ideation --tags "dry,type:build,scope:core,phase-9" --body "After #868, make src/owlbear/tools/browser/content_extractor.py delegate its raw markdown text extraction to owlbear.web_extract.extract_markdown while preserving extract_metadata, ExtractionResult, and wrap_web_content behavior. Source: docs/research/leaf-markdown-extraction-helper.md. AC: (1) content_extractor no longer duplicates the raw trafilatura.extract markdown/include_links/url call, (2) metadata extraction and wrapping semantics stay unchanged, (3) existing tests in tests/test_content_extractor.py and relevant integration coverage pass, (4) no new upward dependency is introduced." --depends-on 868
```
