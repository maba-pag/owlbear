---
id: 796
title: Add Slack message rate limiting
status: archived
priority: nice-to-have
created: 2026-03-14T02:17:16.690077+01:00
updated: 2026-03-14T12:26:18.8593585+01:00
started: 2026-03-14T12:26:13.635044+01:00
completed: 2026-03-14T12:26:13.635044+01:00
tags:
    - security
    - channels
depends_on:
    - 795
    - 802
class: standard
---

Add sliding window rate limiter to _handle_socket_event. See docs/research/slack-sender-validation.md S4.2.

## AC
1. `slack_rate_limit_per_minute: int = 30` added to `OwlBearSettings` in the `# --- Slack ---` section of config.py
2. `SlackChannel.__init__` accepts keyword-only `rate_limit_per_minute: int = 0`; stored as `self._rate_limit_per_minute`; `self._rate_windows: dict[str, deque[float]]` initialized empty
3. `_handle_socket_event` checks rate limit AFTER allowlist check (#795 AC4), BEFORE enqueue: counts entries in `_rate_windows[user_id]` within last 60s via `time.monotonic()`; drops message if count >= `_rate_limit_per_minute`
4. Expired entries (older than 60s) pruned from deque on each check -- prevents unbounded memory growth
5. Rate-limited messages dropped with `WARNING` log including `user_id` and current window count -- message content MUST NOT appear in log
6. `rate_limit_per_minute = 0` disables rate limiting (bypass check entirely)
7. `bootstrap/channel.py` passes `rate_limit_per_minute=settings.slack_rate_limit_per_minute` to `SlackChannel` constructor
8. No external dependencies -- stdlib `collections.deque` + `time.monotonic` only
9. Ruff clean on all changed files

## Pattern references
- `allowed_user_ids` constructor kwarg pattern in slack.py L60-61
- `_handle_socket_event` check ordering in slack.py L330-345 (subtype -> allowlist -> rate limit -> enqueue)
- `create_channel()` bootstrap wiring in bootstrap/channel.py L36-40

## Dependencies
- #795 (sender validation) -- code must exist before rate limit check
- #802 (test task) -- TDD RED phase

[[2026-03-14]] Sat 04:27
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Config field slack_rate_limit_per_minute | Clear type+default, follows existing Slack config pattern in config.py L77-105 | OK |
| 2. Constructor kwarg + _rate_windows init | Explicit type, default 0, follows allowed_user_ids pattern | Refined from vague original |
| 3. Rate limit check placement + logic | Verifiable: after allowlist, before enqueue, explicit time window | Refined: added placement + time.monotonic spec |
| 4. Expired entry pruning | Prevents unbounded memory growth, verifiable | Added (missing from original) |
| 5. WARNING log without content | Security-critical: user_id + count, no content | Refined: added count detail, explicit no-content |
| 6. rate_limit=0 disables | Clear edge case | OK |
| 7. Bootstrap wiring | Follows create_channel pattern in bootstrap/channel.py L36-40 | OK |
| 8. No external deps | Constraint verified: collections.deque + time.monotonic | OK |
| 9. Ruff clean | Standard gate | OK |

### Architecture Notes
Single domain: channels (config field is ancillary). Follows #795 pattern exactly: config field -> constructor kwarg -> handler check -> bootstrap wiring. Sliding window with deque+monotonic is the canonical stdlib approach per research S4.2. Check ordering (subtype -> allowlist -> rate limit -> enqueue) is security-correct: rate limit runs only on authenticated users. No new external boundaries. No failure modes worth mapping (stdlib time.monotonic is guaranteed monotonic, deque ops are O(1) amortized).

### Changes Made
- Refined 7 vague AC lines into 9 precise, verifiable lines
- Added AC for constructor spec (rate_limit_per_minute kwarg, _rate_windows init)
- Added AC for deque pruning (memory safety)
- Removed test AC from impl task (moved to #802)
- Created #802: Tests for Slack message rate limiting (TDD RED) at todo
- Added #802 as dependency

### Dependencies
- Verified: #795 (sender validation) -- at review, code exists
- Created: #802 (test task) at todo, depends on nothing

[[2026-03-14]] Sat 10:21
## Test-Writer Notes
- Tests already exist via sister task #802 (TDD RED completed, now at review)
- Test file: tests/test_slack_sender_validation.py
- Classes: TestFromAC_RateLimitConfig, TestFromAC_RateLimitEnforcement, TestFromAC_SlidingWindow, TestFromAC_RateLimitBootstrap
- Total: 14 tests, all PASS (implementation already in place via #802 builder)
- AC coverage: all 9 AC lines mapped
- ruff: clean
- Pass-through: no new tests needed, #802 covered this feature completely

[[2026-03-14]] Sat 10:51
## Builder Notes

[[2026-03-14]] Sat 10:51
- Pass-through: implementation already done by #802 builder
- Files: src/owlbear/channels/slack.py, src/owlbear/config.py, src/owlbear/bootstrap/channel.py
- Tests: 14 RateLimit/SlidingWindow tests passed (TestFromAC classes untouched)
- Full file: 36 passed in test_slack_sender_validation.py
- Lint: ruff clean on all 4 files
- Coverage: rate-limiting lines fully covered
- No code changes needed - no diff

[[2026-03-14]] Sat 11:30
## Review Evidence

### Test Results
- pytest: 36 passed, 0 failed (tests/test_slack_sender_validation.py)
- All 14 rate-limiting TestFromAC tests pass
- All 22 sender-validation TestFromAC tests pass

### Lint Results
- ruff: All checks passed! (slack.py, config.py, channel.py, test file)

### Coverage
- slack.py rate-limit code (L332-348, L388-390): 100% covered
- config.py L104 field: covered
- bootstrap/channel.py L39 wiring: covered

### Pass 1 -- CRITICAL

#### Security Review
- No hardcoded secrets
- No injection: pure time comparison and deque ops
- No log content leakage: WARNING log includes user_id and count only, verified at L340-344
- No new external dependencies (stdlib only: collections.deque, time.monotonic)
- monotonic clock prevents time-regression attacks
- No issues found

#### Test Integrity (TestFromAC Comparison)
Builder commit 298357a modified test file only to add mock attributes:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_RateLimitConfig (6 methods) | No change | PRESERVED |
| TestFromAC_RateLimitEnforcement (5 methods) | No change | PRESERVED |
| TestFromAC_SlidingWindow (2 methods) | No change | PRESERVED |
| TestFromAC_RateLimitBootstrap (1 method) | No change | PRESERVED |
| TestFromAC_BootstrapWiring::test_create_channel_passes_allowed_user_ids | Added settings.slack_rate_limit_per_minute=30 to mock | PRESERVED (fixture maintenance) |
| TestFromAC_BootstrapWiring::test_create_channel_passes_empty_frozenset | Added settings.slack_rate_limit_per_minute=30 to mock | PRESERVED (fixture maintenance) |

No assertions changed. Mock attribute additions are required to prevent AttributeError.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Exact value checks (==3, ==30, ==100), exact string matches, isinstance |
| Negative/error paths | STRONG | At-limit drop, log-excludes-content, disabled-by-zero, per-user isolation |
| Mutation reasoning | STRONG | Would catch: wrong operator (> vs >=), missing pruning, shared windows, content in logs, wrong log level |
| Test independence | STRONG | Each test creates own SlackChannel instance, independent mocks |
| Descriptive names | STRONG | e.g. test_expired_entries_pruned_message_accepted, test_dropped_message_log_excludes_content |

#### Data Safety
- No data safety issues. Rate windows use per-user deque with pruning (AC4); no shared state across async tasks beyond the channel instance itself (single-threaded event loop).

### Pass 2 -- INFORMATIONAL
- No informational findings

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. slack_rate_limit_per_minute: int = 30 | config.py L104: Field(default=30) | test_settings_field_exists + test_settings_field_default_is_30 + test_settings_field_is_int | PASS |
| 2. Constructor kwarg + _rate_windows | slack.py L68: rate_limit_per_minute kwarg, L79-80: stored + dict init | test_init_accepts_rate_limit_per_minute_kwarg + test_init_rate_limit_default_is_zero + test_init_creates_empty_rate_windows | PASS |
| 3. Check ordering: after allowlist, before enqueue | slack.py L382 (allowlist) -> L389 (rate limit) -> L395 (enqueue) | test_message_within_limit_enqueued + test_message_at_limit_dropped | PASS |
| 4. Expired entry pruning | slack.py L337-338: while/popleft loop | test_expired_entries_pruned_message_accepted | PASS |
| 5. WARNING log with user_id, no content | slack.py L340-344: logger.warning with user_id + count | test_dropped_message_logs_warning_with_user_id + test_dropped_message_log_excludes_content | PASS |
| 6. rate_limit=0 disables | slack.py L389: if > 0 guard | test_rate_limit_zero_disables_limiting (100 msgs, all accepted) | PASS |
| 7. Bootstrap wiring | channel.py L39: rate_limit_per_minute=settings.slack_rate_limit_per_minute | test_create_channel_passes_rate_limit | PASS |
| 8. No external deps | stdlib only: collections.deque + time.monotonic | Code inspection | PASS |
| 9. Ruff clean | uv run ruff check: All checks passed! | -- | PASS |

### Verdict: PASS
### Confidence: .95

[[2026-03-14]] Sat 11:56
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Already current | Messaging row includes 'per-user sliding-window rate limiting' |
| 2 | Docstrings | Yes | Pass | SlackChannel class docstring includes rate_limit_per_minute param; _check_rate_limit has docstring |
| 3 | sources/overview.md | No | N/A | stdlib only (collections.deque + time.monotonic), no external patterns |
| 4 | README.md | No | N/A | No CLI changes; config field is env var via pydantic-settings |
| 5 | Research doc | Yes | Pass | docs/research/slack-sender-validation.md exists, linked from task body (S4.2) |

### Files Updated
- None (all docs already accurate)

### Scratch Files Cleaned
- Deleted docs/scratch/796-b.tmp

[[2026-03-14]] Sat 12:26
## Audit
### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| 1. slack_rate_limit_per_minute: int=30 | config.py L104: Field(default=30) | PASS |
| 2. Constructor kwarg + _rate_windows | slack.py L68: rate_limit_per_minute kwarg, L79-80: stored + dict init | PASS |
| 3. Check after allowlist, before enqueue | slack.py L382 allowlist -> L389 rate limit -> L393 enqueue | PASS |
| 4. Expired entry pruning | slack.py L337-338: while/popleft loop with cutoff=now-60 | PASS |
| 5. WARNING log, no content | slack.py L340-344: logger.warning with user_id+count only | PASS |
| 6. rate_limit=0 disables | slack.py L389: if > 0 guard | PASS |
| 7. Bootstrap wiring | channel.py L39: rate_limit_per_minute=settings.slack_rate_limit_per_minute | PASS |
| 8. No external deps | stdlib only: collections.deque + time.monotonic (L7-8) | PASS |
| 9. Ruff clean | All checks passed on all 4 files | PASS |

### Test Results
- Task-scoped: 36/36 passed (14 rate-limit + 22 sender-validation)
- Full suite: 3004 passed, 30 failed (all pre-existing: regex module, bootstrap unpack, inter_doc, _chat_loop, exception identity, httpx timeouts)
- Ruff: clean

### Commits Verified
- 4b2e882: test: add failing tests for Slack message rate limiting (#802, test-writer)
- 298357a: feat: add sliding window rate limiting to SlackChannel (#802, builder)
- 62f3341: docs: add rate_limit_per_minute to SlackChannel docstring (#802, writer)
- Note: implementation shared with sister task #802

### Confidence: .96
### Action: archive
