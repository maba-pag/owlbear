---
id: 557
title: Add unit test for _default_web_read in bookmark_pipeline
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:59.3906848+01:00
updated: 2026-03-04T07:38:59.3906848+01:00
tags:
    - audit
    - test
class: standard
---

I1: Fallback web reader in bookmark_pipeline.py completely untested. Mock httpx.AsyncClient and trafilatura.extract to cover function shape. AC: _default_web_read has test coverage. See docs/test-quality-audit.md.
