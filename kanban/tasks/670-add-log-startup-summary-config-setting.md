---
id: 670
title: Add log_startup_summary config setting
status: archived
priority: important
created: 2026-03-08T02:59:47.4463837+01:00
updated: 2026-03-09T16:12:15.1964323+01:00
started: 2026-03-08T04:30:34.4097747+01:00
completed: 2026-03-09T16:12:15.1964323+01:00
tags:
    - config
    - scope:core
depends_on:
    - 668
class: standard
---

Add log_startup_summary: bool field (default True) to OwlBearSettings. When False, suppress channel.send of startup summary (still log at DEBUG). AC: (1) Field exists in OwlBearSettings with default True. (2) OWLBEAR_LOG_STARTUP_SUMMARY=false env var disables channel delivery. (3) bootstrap() respects the setting. (4) Ruff clean. See docs/bootstrap-startup-summary-research.md S4.4.

[[2026-03-09]] Mon 16:11
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| Field in OwlBearSettings default=True | config.py L245-248: `log_startup_summary: bool = Field(default=True, ...)` | PASS |
| OWLBEAR_LOG_STARTUP_SUMMARY=false disables channel | env_prefix OWLBEAR_ at config.py L25; test_channel_send_suppressed_when_disabled confirms send not called | PASS |
| bootstrap() respects setting | bootstrap/__init__.py L180: `if settings.log_startup_summary: await channel.send(summary_text)` | PASS |
| Ruff clean | All checks passed on config.py, bootstrap/__init__.py, test_bootstrap.py | PASS |

### Test Results
- pytest (task-scoped): 2 passed in 2.48s
- pytest (full suite): 1271 passed, 20 skipped, 1 failed (pre-existing slack_sdk import, unrelated)
- ruff: clean on task files; 3 pre-existing issues in unrelated files

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 16:12
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| Field in OwlBearSettings default=True | config.py L245-248: `log_startup_summary: bool = Field(default=True, ...)` | PASS |
| OWLBEAR_LOG_STARTUP_SUMMARY=false disables channel | env_prefix OWLBEAR_ at config.py L25; test_channel_send_suppressed_when_disabled confirms send not called | PASS |
| bootstrap() respects setting | bootstrap/__init__.py L180: `if settings.log_startup_summary: await channel.send(summary_text)` | PASS |
| Ruff clean | All checks passed on config.py, bootstrap/__init__.py, test_bootstrap.py | PASS |

### Test Results
- pytest (task-scoped): 2 passed in 2.48s
- pytest (full suite): 1271 passed, 20 skipped, 1 failed (pre-existing slack_sdk import, unrelated)
- ruff: clean on task files; 3 pre-existing issues in unrelated files

### Confidence: .97
### Action: archive
