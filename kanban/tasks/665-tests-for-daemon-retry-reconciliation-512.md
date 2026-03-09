---
id: 665
title: Tests for daemon retry reconciliation (#512)
status: archived
priority: important
created: 2026-03-08T02:10:10.4186435+01:00
updated: 2026-03-09T19:40:31.0801723+01:00
started: 2026-03-08T02:27:26.217633+01:00
completed: 2026-03-09T19:40:31.0801723+01:00
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

[[2026-03-09]] Mon 19:40
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tool-level transient exhausted does NOT trigger daemon retry | `test_tool_transient_exhausted_no_daemon_retry`: sets `_tool_retries_exhausted=True`, asserts `call_count==1`, `sleep.not_called`. Also `test_no_multiplicative_retries` asserts 1 call. | PASS |
| Model-level transient (503) DOES trigger daemon retry | `test_model_level_transient_still_retried_by_daemon`: 503 error, `side_effect=[exc,exc,'recovered']`, asserts `call_count==3` | PASS |
| Auth errors trigger token refresh (unchanged) | `test_auth_error_path_unchanged`: 401 error, asserts `call_count==2`, 'refreshed reply' sent | PASS |
| Permanent errors propagate immediately (unchanged) | `test_permanent_error_path_unchanged`: FileNotFoundError, `assert_called_once()`, error msg sent | PASS |
| Tests in tests/test_daemon.py | All 5 tests in `TestDaemonRetryReconciliation` class, test_daemon.py L1618-1775 | PASS |
| ruff clean, all tests pass | `ruff check` clean on #665 files; 5/5 tests pass; full suite 1315 pass (2 pre-existing failures unrelated) | PASS |

### Test Results
- pytest: 5/5 passed (TestDaemonRetryReconciliation); full suite 1315 passed, 2 pre-existing failures (slack_sdk, Windows perm)
- ruff: clean on #665 files (3 pre-existing errors in unrelated files)

### Confidence: .97
### Action: archive
