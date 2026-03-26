---
id: 825
title: Migrate bookmark_pipeline.py to use web_extract.extract_markdown
status: backlog
priority: nice-to-have
created: 2026-03-15T09:42:57.2505291+01:00
updated: 2026-03-20T14:35:56.9835463+01:00
tags:
    - dry
    - phase-9
    - scope:memory
depends_on:
    - 867
    - 868
class: standard
---

Replace the direct trafilatura extraction in src/owlbear/memory/knowledge/bookmark_pipeline.py::_default_web_read with the package-root leaf helper from #868 rather than src/owlbear/tools/browser/content_extractor.py. This task is the GREEN implementation step after RED task #867 and helper task #868. Source: docs/research/bookmark-pipeline-extract-content.md.

AC:
(1) src/owlbear/memory/knowledge/bookmark_pipeline.py imports and calls owlbear.web_extract.extract_markdown(resp.text, url=url) from _default_web_read(), and no longer imports trafilatura directly.
(2) _default_web_read() does not import from owlbear.tools.*, owlbear.config, or owlbear.core.content_safety; bookmark ingestion output remains raw Markdown without untrusted-content wrapper tags.
(3) _default_web_read() preserves current fetch semantics: the HTTP fetch remains wrapped in TRANSIENT_RETRY, resp.raise_for_status() errors still propagate, and missing-trafilatura first-use failures still surface as actionable ImportErrors.
(4) The RED cases introduced by #867 pass without weakening the bookmark no-wrap invariant asserted in tests/test_content_safety_integration.py.
(5) The scoped tests covering tests/test_bookmark_pipeline.py and the bookmark-path assertions in tests/test_content_safety_integration.py pass.

[[2026-03-20]] Fri 14:35
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) bookmark_pipeline.py no longer imports trafilatura directly | Valid intent, but the original wording targeted the wrong reuse boundary. | Rewrote to call owlbear.web_extract.extract_markdown(resp.text, url=url). |
| (2) uses extract_content from content_extractor | Invalid as written: src/owlbear/memory/knowledge/bookmark_pipeline.py is in memory/, and src/owlbear/tools/browser/content_extractor.py is in tools/. That import would violate the memory -> tools boundary. | Rejected and replaced with the leaf-helper dependency from #868. |
| (3) existing tests pass | Too vague for TDD sequencing and does not identify the predecessor RED work. | Rewrote to require the RED cases from #867 and the scoped bookmark/content-safety tests. |
| (4) output is now markdown format (richer for knowledge ingestion) | Good intent, but incomplete: bookmark ingestion must stay raw and unwrapped. | Rewrote to preserve raw Markdown plus the no-wrap invariant. |

### Architecture Notes
- Layering check: src/owlbear/memory/knowledge/bookmark_pipeline.py cannot import src/owlbear/tools/browser/content_extractor.py under the architecture-standards memory -> tools prohibition.
- Behavior check: extract_content() now reads OwlBearSettings and can call wrap_untrusted_content, while tests/test_content_safety_integration.py explicitly keeps bookmark ingestion unwrapped.
- Shared-boundary precedent: src/owlbear/paths.py shows the acceptable package-root leaf-module pattern for code shared across lower layers.
- Atomicity: #825 is still one memory-domain implementation task once narrowed to bookmark_pipeline integration only. The helper creation remains in #868; the RED test update remains in #867.
- Because #867 and #868 are still ideation and #825 needed a contract rewrite, this review leaves #825 in backlog rather than advancing it to todo today.

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| _default_web_read() | trafilatura unavailable on first use | ImportError | Yes - actionable install hint must still surface | bookmark extraction is skipped |
| _default_web_read() | HTTP request fails or status is non-2xx | httpx.HTTPError | Yes - propagates to process(), which records a skipped reason | bookmark is not ingested |
| _default_web_read() | extraction returns empty content | none | Yes - empty/raw content flows to evaluator without wrapper tags | bookmark may be evaluated as low value |

### Changes Made
- Retitled #825 to target owlbear.web_extract.extract_markdown instead of tools/browser/content_extractor.extract_content.
- Replaced the stale task body with verifiable AC tied to the actual layering and no-wrap invariants.
- Added dependencies on #867 and #868.
- Changed the scope tag from scope:core to scope:memory.
- Appended this architecture review.

### Dependencies
- Added: #867 - RED tests for bookmark_pipeline helper migration.
- Added: #868 - leaf extraction helper required before bookmark_pipeline can consume it.
- Verified: no legal lower-layer shared helper exists in src/owlbear yet; #868 is the architecture-correct prerequisite.
