---
id: 542
title: Handle channel failure in daemon _recover_from_error
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:46.4992228+01:00
updated: 2026-03-07T18:08:01.0822049+01:00
started: 2026-03-07T00:45:02.3988259+01:00
completed: 2026-03-07T18:08:01.0822049+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

## Research (trivial)\n\nN/A - already implemented. Task #471 (archived 2026-03-06) added try/except guards around all three terminal channel.send() calls in _recover_from_error with logger.exception fallback.\n\nEvidence:\n- daemon.py L272-274: transient exhausted path guarded\n- daemon.py L303-305: auth refresh failed path guarded\n- daemon.py L319-321: permanent error path guarded\n- Tests: TestChannelSendFailureLogsOriginalError (test_daemon.py L984-1100) covers all three categories\n\n## Recommendation\n\nClose as duplicate of #471. No code changes needed.
