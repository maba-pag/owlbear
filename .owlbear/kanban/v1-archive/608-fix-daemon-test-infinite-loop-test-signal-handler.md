---
id: 608
title: Fix daemon test infinite loop (test_signal_handler_sets_shutdown_event)
status: archived
priority: critical
created: 2026-03-07T03:08:36.7754333+01:00
updated: 2026-03-07T18:08:18.3430482+01:00
started: 2026-03-07T04:50:05.4901841+01:00
completed: 2026-03-07T18:08:18.3430482+01:00
tags:
    - test
    - bugfix
    - phase-9
class: standard
---

## Root Cause
test_signal_handler_sets_shutdown_event calls signal handler via call_soon_threadsafe inside receive_then_stop, but AsyncMock resolves instantly without yielding, so the scheduled callback never fires and shutdown_event stays False -> infinite loop consuming 20+ GB RAM.

## Fix Applied
Added `await asyncio.sleep(0)` after signal handler invocation in receive_then_stop to let the event loop process the queued callback.

## AC
- [ ] test_signal_handler_sets_shutdown_event passes in < 5s (was infinite hang)
- [ ] Full daemon test file (56 tests) passes in < 10s
- [ ] No memory leak during full suite run
- [ ] Fix is in tests/test_daemon.py only (production code unchanged)
