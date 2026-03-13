---
id: 555
title: Extract shared test helpers to conftest.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:57.7640987+01:00
updated: 2026-03-07T01:11:01.9916854+01:00
started: 2026-03-07T01:05:39.1532416+01:00
tags:
    - audit
    - test
class: standard
---

M3/L1: conftest.py has only 1 fixture. 16 test files define identical _run(coro) helper. 3 files duplicate MockChannel class. 3 files duplicate make_mock_toolset(). 2 files duplicate make_settings(). Research complete -- see docs/research/conftest-extraction.md. Two-phase approach: (1) Extract MockChannel/make_mock_toolset/make_settings to conftest.py, (2) Eliminate_run() by converting 16 files to async def + @pytest.mark.asyncio. Phase 2 is a separate task (large diff).

## AC

- [x] Research doc at docs/research/conftest-extraction.md
- [x] Identified all duplicated helpers (MockChannel, make_mock_toolset, make_settings,_run)
- [x] Proposed two-phase approach
- [x] Follow-up implementation tasks created
