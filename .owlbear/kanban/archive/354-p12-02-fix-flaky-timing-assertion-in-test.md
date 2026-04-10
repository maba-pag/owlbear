---
id: 354
title: 'P12-02: Fix flaky timing assertion in test_successive_calls_advance_last_used'
status: archived
priority: important
created: 2026-03-01T17:31:35.2534984+01:00
updated: 2026-03-01T17:41:21.5014802+01:00
started: 2026-03-01T17:39:49.6047906+01:00
completed: 2026-03-01T17:41:21.5014802+01:00
tags:
    - phase-12
    - test
    - reliability
class: standard
---

In tests/test_progress_reporter.py, test_successive_calls_advance_last_used does two successive calls and asserts reporter._last_used > before. On fast machines both calls can land in the same time tick, making > fail.

Fix: add time.sleep(0.001) between calls or use >= with a secondary assertion that proves the call happened.

AC:
- test_successive_calls_advance_last_used passes reliably (no timing dependence)
- All other progress reporter tests still pass
- ruff check tests/test_progress_reporter.py clean

Context: Found during phase-12 review of progress reporter tests.
