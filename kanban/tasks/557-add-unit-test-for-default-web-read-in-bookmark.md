---
id: 557
title: Add unit test for _default_web_read in bookmark_pipeline
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:59.3906848+01:00
updated: 2026-03-15T08:21:25.4067689+01:00
started: 2026-03-07T01:05:40.2133378+01:00
completed: 2026-03-15T08:21:10.6037909+01:00
tags:
    - audit
    - test
class: standard
---

I1: Fallback web reader in bookmark_pipeline.py completely untested. Mock httpx.AsyncClient and trafilatura.extract to cover function shape. AC: _default_web_read has test coverage. See docs/test-quality-audit.md.

## Research (2026-03-07)

**Function:** _default_web_read(url: str) -> str | None in src/owlbear/memory/knowledge/bookmark_pipeline.py (line 173). Lazy-imports httpx, trafilatura, TRANSIENT_RETRY. Inner _fetch wrapped with tenacity retry. Returns trafilatura.extract(resp.text).

**Existing coverage:** 2 tests for ImportError guard only. Zero coverage on fetch+extract path.

**Mock patterns (in-project prior art):**
- httpx.AsyncClient as async CM: test_browser_launcher.py L165-215
- trafilatura.extract: test_content_extractor.py L78

**Test plan -- add class TestDefaultWebReadFunction to tests/test_bookmark_pipeline.py:**
1. Happy path: mock httpx 200 + trafilatura.extract returns text
2. trafilatura returns None: mock httpx 200 + extract returns None
3. HTTP error propagates: raise_for_status raises HTTPStatusError (4xx, no retry)
4. Passes resp.text to trafilatura: assert extract called with resp.text

**Mock targets:** httpx.AsyncClient (async CM mock), trafilatura.extract (direct patch), owlbear.core.retry.TRANSIENT_RETRY (lambda fn: fn for error test)

[[2026-03-15]] Sun 08:08
## Architecture Review
Verdict: ALREADY DONE

All AC items from the research test plan are already implemented and passing in committed code (WIP commit 9edecc9).

### Evidence
- TestDefaultWebReadImportGuard: 2 tests (import guard) -- existed before research
- TestDefaultWebReadFetch: 3 tests (happy, error, None) -- added in 9edecc9
- All 5 tests PASS (pytest 5/5 in 1.24s)
- Research plan item 4 (resp.text passed to trafilatura) verified at L648 assert

### Action
Task closed -- no pipeline work needed. Tests already exist and pass.

[[2026-03-15]] Sun 08:21
## Audit (2026-03-15)
### AC Verification
- _default_web_read has test coverage: 5 tests in 2 classes, all PASS (1.34s) -- PASS
- Happy path: test_happy_path_returns_extracted_text mocks httpx+trafilatura -- PASS
- HTTP error: test_http_error_propagates -- PASS
- None result: test_extract_returns_none -- PASS
- Import guard: 2 tests with install hint message -- PASS

### Test Results
- pytest: 5 passed, 16 deselected
- ruff: All checks passed

### Confidence: .97
### Action: archive
