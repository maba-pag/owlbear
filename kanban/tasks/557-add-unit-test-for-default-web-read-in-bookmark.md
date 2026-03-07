---
id: 557
title: Add unit test for _default_web_read in bookmark_pipeline
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:59.3906848+01:00
updated: 2026-03-07T01:11:17.536416+01:00
started: 2026-03-07T01:05:40.2133378+01:00
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
