---
id: 802
title: Tests for Slack message rate limiting
status: archived
priority: nice-to-have
created: 2026-03-14T04:25:55.6773733+01:00
updated: 2026-03-14T11:22:25.8802487+01:00
started: 2026-03-14T11:22:20.7920764+01:00
completed: 2026-03-14T11:22:20.7920764+01:00
tags:
    - security
    - channels
    - type:test
class: standard
---

Preceding test task for #796. Write failing tests that verify sliding window rate limiting in SlackChannel._handle_socket_event.

## AC
- [ ] New test class TestFromAC_RateLimitConfig in tests/test_slack_sender_validation.py (co-located with sender validation tests)
- [ ] Test: slack_rate_limit_per_minute field exists on OwlBearSettings with default 30, type int
- [ ] Test: SlackChannel.__init__ accepts keyword-only rate_limit_per_minute, stored as self._rate_limit_per_minute; default is 0
- [ ] Test: SlackChannel.__init__ initializes self._rate_windows as empty dict
- [ ] New test class TestFromAC_RateLimitEnforcement in tests/test_slack_sender_validation.py
- [ ] Test: message from user within limit (< rate_limit_per_minute in last 60s) is enqueued
- [ ] Test: message from user at limit (== rate_limit_per_minute in last 60s) is dropped, not enqueued
- [ ] Test: dropped message logs WARNING with user_id and window count, message content NOT in log
- [ ] Test: rate_limit_per_minute=0 disables rate limiting (all messages accepted regardless of count)
- [ ] New test class TestFromAC_SlidingWindow in tests/test_slack_sender_validation.py
- [ ] Test: expired entries (>60s old) are pruned from deque on check -- message accepted after window slides
- [ ] Test: per-user isolation -- user A at limit does not affect user B
- [ ] New test class TestFromAC_RateLimitBootstrap in tests/test_slack_sender_validation.py
- [ ] Test: create_channel passes rate_limit_per_minute from settings to SlackChannel constructor
- [ ] All existing tests in test_slack_sender_validation.py still pass
- [ ] New tests FAIL on current code (TDD RED)
- [ ] ruff clean

[[2026-03-14]] Sat 05:06
## Test-Writer Notes
- Test file: tests/test_slack_sender_validation.py (extended)
- Classes: TestFromAC_RateLimitConfig, TestFromAC_RateLimitEnforcement, TestFromAC_SlidingWindow, TestFromAC_RateLimitBootstrap
- Tests per category: happy 3, edge 2, error 2, boundary 4, config 3
- Total: 14 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| slack_rate_limit_per_minute field default 30, int | test_settings_field_exists, test_settings_field_default_is_30, test_settings_field_is_int | config |
| __init__ accepts rate_limit_per_minute, default 0 | test_init_accepts_rate_limit_per_minute_kwarg, test_init_rate_limit_default_is_zero | happy |
| __init__ creates empty _rate_windows dict | test_init_creates_empty_rate_windows | config |
| Within limit enqueued | test_message_within_limit_enqueued | happy |
| At limit dropped | test_message_at_limit_dropped | boundary |
| Dropped logs WARNING with user_id, no content | test_dropped_message_logs_warning_with_user_id, test_dropped_message_log_excludes_content | error |
| rate_limit=0 disables limiting | test_rate_limit_zero_disables_limiting | edge |
| Expired entries pruned, window slides | test_expired_entries_pruned_message_accepted | boundary |
| Per-user isolation | test_per_user_isolation | edge |
| create_channel passes rate_limit_per_minute | test_create_channel_passes_rate_limit | happy |
| Existing tests pass | 22 existing tests pass | regression |
| ruff clean | All checks passed | lint |

[[2026-03-14]] Sat 05:43
## Builder Notes
- Files changed: src/owlbear/channels/slack.py, src/owlbear/config.py, src/owlbear/bootstrap/channel.py, tests/test_slack_sender_validation.py
- Tests: 36 passed (14 new rate-limit + 22 existing), 0 failed
- Coverage: slack.py 49% overall (rate-limit lines fully covered; uncovered lines are pre-existing send/connect/disconnect)
- Lint: ruff clean
- Implementation: slack_rate_limit_per_minute config (default 30), rate_limit_per_minute kwarg on SlackChannel (default 0), _check_rate_limit helper with sliding window deque, bootstrap wiring
- Fixes applied: Added slack_rate_limit_per_minute to 2 existing TestFromAC_BootstrapWiring mock setups (mechanical fixture update)
- Commit: 298357a

[[2026-03-14]] Sat 10:44
## Review Evidence
See docs/scratch/802-reviewer.md for full evidence.

Verdict: PASS (.93)  36/36 tests pass, ruff clean, all 17 AC lines verified, all TestFromAC PRESERVED, test quality STRONG across all 5 dimensions, no security or data safety issues.

[[2026-03-14]] Sat 10:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added 'per-user sliding-window rate limiting' to Messaging row |
| 2 | Docstrings complete | Yes | Updated | Added rate_limit_per_minute param to SlackChannel class docstring |
| 3 | sources/overview.md | No | N/A | Sliding-window is standard CS pattern, no external source cited |
| 4 | README.md | No | N/A | No CLI changes, internal rate-limit logic only |
| 5 | Research doc linked | No | N/A | type:test task, no research phase |

### Files Updated
- .github/copilot-instructions.md (Messaging row)
- src/owlbear/channels/slack.py (class docstring only)

### Scratch Files Cleaned
- Deleted docs/scratch/802-reviewer.md

[[2026-03-14]] Sat 10:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added ConsolidationService mention to Knowledge row in tech stack |
| 2 | Docstrings complete | Yes | Pass | consolidation.py: module, class, 3 methods all have docstrings; config fields use Field(description=) |
| 3 | sources/overview.md | No | N/A | No new external patterns; follows existing GraphEnricher/KnowledgeQueryService patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | Both docs/research/always-on-memory-integration.md and gcp-always-on-memory-agent.md exist and linked in task body |

### Files Updated
- .github/copilot-instructions.md (Knowledge row: added ConsolidationService mention)

### Scratch Files Cleaned
- None found (no docs/scratch/723-* files)

[[2026-03-14]] Sat 10:59
## Docs Gate
See task body for checklist.

-t
