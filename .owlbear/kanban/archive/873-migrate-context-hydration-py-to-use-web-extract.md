---
id: 873
title: Migrate context_hydration.py to use web_extract.extract_markdown
status: archived
priority: nice-to-have
created: 2026-03-20T14:48:10.8062795+01:00
updated: 2026-03-26T16:14:45.1709313+01:00
tags:
    - dry
    - type:build
    - scope:core
    - phase-9
depends_on:
    - 868
    - 869
    - 876
class: standard
---

Replace the direct trafilatura extraction in src/owlbear/core/context_hydration.py::fetch_url with the package-root leaf helper from #868. This is the GREEN implementation step after RED tasks #869 and #876, and it must not reuse the blocked core -> tools plan from #826. Sources: docs/research/context-hydration-web-extract-migration.md and docs/research/context-hydration-extract-markdown-test-seam.md.

## AC

- src/owlbear/core/context_hydration.py imports extract_markdown from owlbear.web_extract, fetch_url() calls extract_markdown(resp.text, url=url) exactly once on the successful HTTP path, and the module no longer imports trafilatura directly.
- fetch_url() keeps its existing local url_checker invocation, httpx.AsyncClient request flow, and TimeoutException/HTTPStatusError/HTTPError empty-string handling; this task does not move HTTP policy into owlbear.web_extract.
- fetch_url() continues to own wrap_web_content behavior by applying wrap_untrusted_content only to the raw string returned from extract_markdown, so helper output is not pre-wrapped and no double-wrap path is introduced.
- src/owlbear/core/context_hydration.py does not import from owlbear.tools.* as part of this migration.
- The RED tests from #869 and #876 pass, and the scoped verification covers tests/test_context_hydration.py plus the fetch_url-related assertions in tests/test_content_safety_integration.py.

## Research

- Research doc: docs/research/context-hydration-web-extract-migration.md
- External attribution updated: docs/sources/overview.md
- Key finding: #873 is the legal GREEN path because core can depend on the package-root leaf helper from #868, but not on tools.browser.content_extractor.
- Key finding: fetch_url() must keep its local httpx error handling and wrap_web_content branch; only the raw trafilatura.extract(...) call should move behind extract_markdown(resp.text, url=url).
- Key finding: #876 closes the remaining RED gap by asserting helper-call arguments instead of relying only on wrapping behavior.
- Stale alternative: #826 remains the blocked extract_content plan and must not be reused as the GREEN partner for #869.

[[2026-03-20]] Fri 16:22

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Import package-root helper and remove direct trafilatura import | Precise and mechanically checkable against the current fetch_url() seam in src/owlbear/core/context_hydration.py. | Rewrote |
| Preserve local url_checker, HTTP request flow, and empty-string HTTP error handling | Needed the current caller policy spelled out so the builder does not push transport concerns into owlbear.web_extract. | Rewrote |
| Preserve local wrap_web_content ownership with raw helper output | Required to keep the contrast already exercised in tests/test_content_safety_integration.py and avoid a double-wrap regression. | Rewrote |
| Add no owlbear.tools.* imports to context_hydration.py | Explicit layer guard required by architecture-standards; content_extractor remains an illegal reuse target for core. | Added |
| Require RED coverage from #869 and #876 before GREEN verification | #869 exists, but current coverage did not explicitly prove HTML and url forwarding; #876 closes that gap. | Added dependency |

### Architecture Notes

- Current production seam in src/owlbear/core/context_hydration.py is a direct trafilatura.extract(...) call inside fetch_url(); this task should replace only that extraction call.
- Package-root leaf precedent already exists in src/owlbear/paths.py. The helper from #868 is the legal dependency for core/.
- src/owlbear/tools/browser/content_extractor.py is not a legal reuse target for core because it carries tools-layer behavior, OwlBearSettings access, and wrap_web_content logic.
- tests/test_context_hydration.py and tests/test_content_safety_integration.py already prove wrapping ownership; #876 adds the missing helper-argument contract so this GREEN task stays fully TDD-backed.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| fetch_url() | HTTP request fails before extraction | httpx.TimeoutException / httpx.HTTPStatusError / httpx.HTTPError | Yes - returns empty string | URL content is omitted from hydrated context |
| fetch_url() | extract_markdown() cannot import trafilatura | ImportError | No - propagated from #868 helper with install hint | User gets an actionable setup error instead of a silent empty result |
| fetch_url() | extract_markdown() returns empty string | none | Yes - local wrap branch is skipped | URL is recorded as an unsuccessful fetch upstream |

### Changes Made

- Rewrote #873 into explicit GREEN-phase AC.
- Added dependencies on #868, #869, and #876.
- Kept the task scoped to src/owlbear/core/context_hydration.py and its existing fetch_url-related tests.

### Dependencies

- Added/Verified: #868, #869, #876

## Test-Writer Notes

- BLOCKED: Cannot write RED (failing) tests for #873.
- Reason: The migration was already implemented by task #876 builder (commit b32ef27 changed src/owlbear/core/context_hydration.py to import extract_markdown from owlbear.web_extract and call extract_markdown(resp.text, url=url)).
- Verification: All 12 RED tests from #876 (TestFromAC_FetchUrlExtractMarkdownForwarding, TestFromAC_ExtractMarkdownSeam, TestFromAC_FetchUrlExtractMarkdownSeam) pass against current code.
- AC line 1 (import + call + no direct trafilatura): ALREADY SATISFIED in current source.
- AC line 2 (url_checker + httpx flow + error handling): ALREADY SATISFIED, covered by TestFromACFetchUrl.
- AC line 3 (wrap_web_content raw-string behavior): ALREADY SATISFIED, covered by TestFromAC_FetchUrlExtractMarkdownSeam.
- AC line 4 (no owlbear.tools.* imports): ALREADY SATISFIED in current source - structural test would pass, not fail.
- AC line 5 (RED tests from #869 and #876 pass): CONFIRMED - 12 tests pass.
- Recommendation: Architect should close #873 as delivered by #876 or redirect this task. No new failing tests are possible.

[[2026-03-26]] Thu 16:14

## Test-Writer Notes (2026-03-26, retry of blocked pass-through)

- Green-on-arrival: implementation was delivered by #876 builder before test-writer slot ran.
- Scoped test run: 42 passed in tests/test_context_hydration.py + tests/test_content_safety_integration.py
- AC coverage confirmed:
  - AC1 (import extract_markdown, no trafilatura import, call once on success path): COVERED by TestFromAC_FetchUrlExtractMarkdownForwarding + TestFromAC_ExtractMarkdownSeam
  - AC2 (url_checker + httpx flow + error handling): COVERED by TestFromACFetchUrl
  - AC3 (wrap_web_content owns raw output, no double-wrap): COVERED by fetch_url tests in test_content_safety_integration.py
  - AC4 (no owlbear.tools.* import): COVERED by TestFromAC_ExtractMarkdownSeam (structural import assertion)
  - AC5 (RED tests from #869 and #876 pass): CONFIRMED - all 42 tests pass
- No new tests needed. No fabrication. Overtaken RED - advancing to in-progress.
