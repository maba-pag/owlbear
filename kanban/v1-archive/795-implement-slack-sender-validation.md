---
id: 795
title: Implement Slack sender validation
status: archived
priority: needed
created: 2026-03-14T02:17:07.4570481+01:00
updated: 2026-03-14T10:34:27.2551422+01:00
started: 2026-03-14T10:34:21.4493944+01:00
completed: 2026-03-14T10:34:21.4493944+01:00
tags:
    - security
    - channels
depends_on:
    - 526
    - 801
class: standard
---

Implement Slack sender allowlist check in _handle_socket_event per docs/research/slack-sender-validation.md S4.1.

## AC
1. `OwlBearSettings.slack_allowed_user_ids: list[str] = Field(default_factory=list)` added to config.py in the `# --- Slack ---` section
2. `SlackChannel.__init__` accepts keyword-only `allowed_user_ids: frozenset[str] = frozenset()`; stored as `self._allowed_user_ids`; type is frozenset for O(1) lookup
3. `_handle_socket_event` drops (does not enqueue) message events that have a `subtype` field  filters bot_message, message_changed, etc. Event envelope is still ACK'd.
4. `_handle_socket_event` drops message events where `event.get('user')` is not in `self._allowed_user_ids`  only when the allowlist is non-empty. Event envelope is still ACK'd.
5. Subtype check (AC 3) runs BEFORE user check (AC 4)  messages without `user` field are caught early
6. Rejected senders logged at WARNING with `user_id`  message content MUST NOT appear in the log line
7. Empty allowlist (default) accepts all senders  backwards compatible with existing deployments
8. `create_channel()` in `bootstrap/channel.py` passes `frozenset(settings.slack_allowed_user_ids)` to `SlackChannel`
9. Ruff clean on all changed files

Depends on: #526 (research), #801 (RED tests)

[[2026-03-14]] Sat 03:14
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Config field slack_allowed_user_ids | Clear type+default, follows existing Slack config pattern in config.py L77-97 | OK |
| 2. SlackChannel.__init__ kwarg | Explicit type (frozenset), O(1) lookup per research S4.1 | OK |
| 3. Subtype filter drops+acks | Verifiable, prevents bot loops per SEC-15 | OK |
| 4. User allowlist check | Verifiable, non-empty guard is backwards compatible | OK |
| 5. Check order (subtype before user) | Prevents KeyError on messages without user field | OK |
| 6. WARNING log without content | Security-critical: no message content in logs | OK |
| 7. Empty allowlist accepts all | Backwards compatible default | OK |
| 8. Bootstrap wiring | Follows existing pattern in bootstrap/channel.py L36-40 | OK |
| 9. Ruff clean | Standard gate | OK |

### Architecture Notes
Single domain: channels. Config field addition is ancillary (standard pattern). SlackChannel constructor change is additive (keyword-only, default frozenset). Handler changes are localized to _handle_socket_event (slack.py L320-325). No new dependencies. Follows existing ChannelPlugin protocol. frozenset conversion at bootstrap boundary is correct (immutable, O(1) lookup). Subtype filter catches bot_message, message_changed, message_deleted etc. per Slack docs.

### Changes Made
- Created #801 Test Slack sender validation (RED) at todo (TDD compliance)
- Fixed dependency: #795 depends_on #801 (tests before impl)
- Removed erroneous #801 depends_on #795
- Refined AC: 9 verifiable lines replacing original 7 (added constructor spec, check ordering, ACK behavior)
- Removed unit test AC from impl task (moved to #801)

### Dependencies
- #526 (research): in review, but research doc exists and is stable
- #801 (RED tests): created, at todo, ready for test-writer
- #796, #797 (rate limit, logging): downstream, depend on #795

[[2026-03-14]] Sat 03:47
## Test-Writer Notes
- Test file: tests/test_slack_sender_validation.py (written in #801)
- Classes: TestFromAC_ConfigField, TestFromAC_ConstructorKwarg, TestFromAC_SubtypeFilter, TestFromAC_UserAllowlistFilter, TestFromAC_RejectionLogging, TestFromAC_AllowedUserEnqueued, TestFromAC_EmptyAllowlistAcceptsAll, TestFromAC_BootstrapWiring, TestFromAC_CheckOrdering
- Tests per category: happy 7, edge 3, error 5, boundary 7
- Total: 22 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| 1. Config field | test_field_exists_on_settings, test_default_is_empty_list, test_field_type_is_list_of_str | happy |
| 2. Constructor kwarg | test_init_accepts_allowed_user_ids_kwarg, test_allowed_user_ids_stored_as_frozenset, test_default_is_empty_frozenset | happy, boundary |
| 3. Subtype filter | test_bot_message_subtype_dropped, test_message_changed_subtype_dropped, test_subtype_message_acked_but_not_enqueued | happy, edge |
| 4. User allowlist | test_disallowed_user_message_dropped, test_disallowed_user_still_acked, test_message_without_user_field_dropped | error |
| 5. Check ordering | test_subtype_filter_catches_before_user_check | boundary |
| 6. Rejection logging | test_rejection_logged_at_warning, test_rejection_log_contains_user_id, test_rejection_log_excludes_message_content | error, boundary |
| 7. Empty allowlist | test_empty_allowlist_accepts_any_user, test_explicit_empty_frozenset_same_as_default | edge, boundary |
| 8. Bootstrap wiring | test_create_channel_passes_allowed_user_ids, test_create_channel_passes_empty_frozenset_for_empty_list | happy |
| 9. Ruff clean | gate check | N/A |

[[2026-03-14]] Sat 04:16
## Builder Notes
- Files changed: src/owlbear/channels/slack.py, src/owlbear/config.py, src/owlbear/bootstrap/channel.py
- Tests: 22/22 passed (all TestFromAC), ruff clean
- Coverage: slack.py 43% overall (new validation code paths 100%, uncovered lines are pre-existing send/connect/disconnect)
- Lint: ruff clean on all changed files
- TestFromAC: zero modifications to test file (git diff empty)
- Commit: 7173629
- Implementation: slack_allowed_user_ids config field, allowed_user_ids kwarg on SlackChannel, subtype filter + user allowlist in _handle_socket_event, bootstrap wiring in create_channel

[[2026-03-14]] Sat 04:49
## Review Evidence
### Test Results
- pytest: 22/22 passed, 0 failed (all 9 TestFromAC classes)
- ruff: All checks passed on all 4 files

### Coverage
- slack.py 42% overall (new validation code 100% — subtype filter, user check, warning log all exercised by tests)
- config.py 81%
- bootstrap/channel.py 56%

### Pass 1 CRITICAL
#### Security Review
1. Hardcoded secrets: None (test tokens are placeholders)
2. Injection: None (no SQL, shell, templates)
3. Path traversal: N/A
4. Insecure deserialization: N/A
5. Input validation: Correct — event.get() used safely, subtype+user validated at Slack boundary
6. Dependency risk: No new deps
7. Secret leakage: WARNING log uses only sender user_id (%s lazy fmt), no message content. Confirmed by test_rejection_log_excludes_message_content
No security issues found.

#### TestFromAC Comparison
git log -- tests/test_slack_sender_validation.py shows single commit a4818a9 (test-writer). Builder commit 7173629 does NOT touch the test file. All 22 tests PRESERVED.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks (queue content == expected text), isinstance(frozenset), exact user_id in logs |
| Negative/error paths | STRONG | 5 rejection scenarios: disallowed user, missing user field, bot_message, message_changed, plus ACK verification on all drops |
| Mutation reasoning | ADEQUATE | Removing subtype check, user check, check ordering, frozenset conversion, or bootstrap wiring each caught by specific tests |
| Test independence | STRONG | Each test creates own mock + channel, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario + expected outcome |

#### Data Safety
No issues. Read-only event processing in memory, no persistence, no shared mutable state beyond async-safe queue.

### Pass 2 INFORMATIONAL
- Pre-existing logger.debug logs message content on success path (out of scope)
- Config doesn't validate Slack user ID format (acceptable for admin config)

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Config field | config.py L97-103 | TestFromAC_ConfigField (3 tests) | PASS |
| 2. Constructor kwarg | slack.py L62 param, L74 stored | TestFromAC_ConstructorKwarg (3 tests) | PASS |
| 3. Subtype filter drops+acks | slack.py L333-334 | TestFromAC_SubtypeFilter (3 tests) | PASS |
| 4. User allowlist check | slack.py L337-344 | TestFromAC_UserAllowlistFilter (3 tests) | PASS |
| 5. Check ordering | slack.py L333 before L337 | TestFromAC_CheckOrdering (1 test) | PASS |
| 6. WARNING log, no content | slack.py L341-343 | TestFromAC_RejectionLogging (3 tests) | PASS |
| 7. Empty allowlist accepts all | slack.py L337 if self._allowed_user_ids | TestFromAC_EmptyAllowlistAcceptsAll (2 tests) | PASS |
| 8. Bootstrap wiring | channel.py L38 | TestFromAC_BootstrapWiring (2 tests) | PASS |
| 9. Ruff clean | ruff check: All checks passed | N/A | PASS |

### Verdict: PASS (confidence .94)

[[2026-03-14]] Sat 05:21
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Already current | Messaging row already includes 'sender allowlist filtering' |
| 2 | Docstrings complete | Yes | Updated | _handle_socket_event docstring updated to mention subtype filter + allowlist |
| 3 | sources/overview.md | Yes | Already current | Slack Sender Validation section (Task #526) already present at L377 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/slack-sender-validation.md exists, referenced in task body |
| 6 | No impact | -- | -- | Items 1-3 apply and verified; item 4 N/A; item 5 passes |

### Files Updated
- src/owlbear/channels/slack.py (_handle_socket_event docstring only)

### Scratch Files Cleaned
- None (no docs/scratch/795-* or 801-* files found)

[[2026-03-14]] Sat 05:21
## Docs Gate - docstring updated, all checks pass

[[2026-03-14]] Sat 10:33
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Config field | config.py L97-103: slack_allowed_user_ids | PASS |
| 2. Constructor kwarg | slack.py L67+L75 frozenset | PASS |
| 3. Subtype filter | slack.py L372-375 drops+acks | PASS |
| 4. User allowlist | slack.py L378-384 | PASS |
| 5. Check ordering | subtype L372 before user L378 | PASS |
| 6. WARNING no content | slack.py L381-383 | PASS |
| 7. Empty allowlist | L378 falsy guard | PASS |
| 8. Bootstrap | channel.py L41 | PASS |
| 9. Ruff | All checks passed | PASS |

### Test Results
- pytest: 36/36 passed, 306/308 broader (2 pre-existing)
- ruff: clean

### Confidence: .97
### Action: archive
