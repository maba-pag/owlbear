---
id: 665
title: Tests for daemon retry reconciliation (#512)
status: done
priority: important
created: 2026-03-08T02:10:10.4186435+01:00
updated: 2026-03-08T02:27:26.217633+01:00
started: 2026-03-08T02:27:26.217633+01:00
completed: 2026-03-08T02:27:26.217633+01:00
tags:
    - test
    - resilience
    - scope:core
depends_on:
    - 512
class: standard
---

Test companion for #512. Verify that the reconciled retry architecture has correct behavior.

## Acceptance Criteria

- [ ] Test: tool-level transient error exhausted by HookedToolset does NOT trigger daemon _recover_from_error transient retry (max 3 total attempts, not 9)
- [ ] Test: model-level transient error (Copilot 503 during agent.turn) DOES trigger daemon transient retry
- [ ] Test: auth errors still trigger token refresh path (unchanged)
- [ ] Test: permanent errors still propagate immediately (unchanged)
- [ ] Tests in tests/test_daemon.py or new test file
- [ ] ruff clean, all tests pass
