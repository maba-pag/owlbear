---
id: 801
title: Test Slack sender validation (RED)
status: archived
priority: needed
created: 2026-03-14T03:12:52.1534179+01:00
updated: 2026-03-14T05:28:50.6723034+01:00
started: 2026-03-14T05:28:45.8896483+01:00
completed: 2026-03-14T05:28:45.8896483+01:00
tags:
    - security
    - channels
    - type:test
class: standard
---

TDD RED tests for #795 (Slack sender validation). See docs/research/slack-sender-validation.md S4.1.

## AC
- Test file: tests/test_slack_sender_validation.py
- Tests cover all 8 AC lines from #795:
  1. Config field exists with default empty list
  2. SlackChannel accepts allowed_user_ids kwarg
  3. Message with subtype dropped (not enqueued), event still ACK'd
  4. Message from disallowed user dropped when allowlist non-empty
  5. Rejected sender logged at WARNING with user_id (no content)
  6. Message from allowed user enqueued
  7. Empty allowlist accepts all senders
  8. bootstrap/channel.py passes frozenset to SlackChannel
- All tests FAIL (RED phase) before builder implements
- Ruff clean

[[2026-03-14]] Sat 03:30
## Test-Writer Notes
- Test file: tests/test_slack_sender_validation.py
- Classes: TestFromAC_ConfigField, TestFromAC_ConstructorKwarg, TestFromAC_SubtypeFilter, TestFromAC_UserAllowlistFilter, TestFromAC_RejectionLogging, TestFromAC_AllowedUserEnqueued, TestFromAC_EmptyAllowlistAcceptsAll, TestFromAC_BootstrapWiring, TestFromAC_CheckOrdering
- Tests per category: happy 7, edge 3, error 5, boundary 7
- Total: 22 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| 1. Config field slack_allowed_user_ids | test_field_exists_on_settings, test_default_is_empty_list, test_field_type_is_list_of_str | happy |
| 2. SlackChannel accepts allowed_user_ids | test_init_accepts_allowed_user_ids_kwarg, test_allowed_user_ids_stored_as_frozenset, test_default_is_empty_frozenset | happy, boundary |
| 3. Subtype messages dropped, ACK'd | test_bot_message_subtype_dropped, test_message_changed_subtype_dropped, test_subtype_message_acked_but_not_enqueued | happy, edge |
| 4. Disallowed user dropped | test_disallowed_user_message_dropped, test_disallowed_user_still_acked, test_message_without_user_field_dropped | error |
| 5. Rejected sender WARNING log | test_rejection_logged_at_warning, test_rejection_log_contains_user_id, test_rejection_log_excludes_message_content | error, boundary |
| 6. Allowed user enqueued | test_allowed_user_message_enqueued, test_allowed_user_among_multiple_still_passes | happy |
| 7. Empty allowlist accepts all | test_empty_allowlist_accepts_any_user, test_explicit_empty_frozenset_same_as_default | edge, boundary |
| 8. Bootstrap passes frozenset | test_create_channel_passes_allowed_user_ids, test_create_channel_passes_empty_frozenset_for_empty_list | happy |
| 5b. Subtype before user check | test_subtype_filter_catches_before_user_check | boundary |

[[2026-03-14]] Sat 03:49
## Builder Notes
- Files changed: src/owlbear/config.py, src/owlbear/channels/slack.py, src/owlbear/bootstrap/channel.py
- Tests: 22 passed (all TestFromAC), 89 related tests passed (slack_interactive + config)
- Coverage: config.py 81%, slack.py 43% (misses are pre-existing unrelated code), channel.py 56%
- Lint: ruff clean on all changed files
- Commit: 7173629
- Implementation: added slack_allowed_user_ids config field, allowed_user_ids kwarg to SlackChannel.__init__, subtype filter + user allowlist check in _handle_socket_event, WARNING log for rejected senders (no content), bootstrap wiring via frozenset conversion

[[2026-03-14]] Sat 04:16
## Review Evidence
### Test Results
- pytest: 22/22 passed, 0 failed
- All 9 TestFromAC classes executed: ConfigField (3), ConstructorKwarg (3), SubtypeFilter (3), UserAllowlistFilter (3), RejectionLogging (3), AllowedUserEnqueued (2), EmptyAllowlistAcceptsAll (2), BootstrapWiring (2), CheckOrdering (1)

### Lint Results
- ruff: All checks passed (config.py, slack.py, channel.py, test file)

### Coverage
- slack.py: 43% (new lines 322-335 covered; misses are pre-existing unrelated code: send_image, connect, disconnect, interactive handler)
- config.py: 81% (new field lines 97-103 covered; misses are pre-existing validators)
- channel.py: 56% (new line 38 covered; misses are cli/voice/unknown branches)

### Pass 1 CRITICAL
#### Security Review
1. Hardcoded secrets: None
2. Injection: None (no SQL, no shell, no template rendering)
3. Path traversal: N/A (no file operations)
4. Insecure deserialization: N/A
5. Input validation: Config field uses pydantic Field with list[str] type (validated at system boundary). Frozenset conversion in bootstrap for O(1) lookup. WARNING log uses %s formatting (not f-string) with only user_id, no content. GOOD.
6. Dependency risk: No new dependencies
7. Secret leakage: WARNING log explicitly excludes message content (logs only sender user_id). test_rejection_log_excludes_message_content verifies this. GOOD.
No security issues found.

#### TestFromAC Comparison
Builder commit 7173629: 3 files changed (config.py, slack.py, channel.py). Test file NOT touched.
All 22 tests in 9 TestFromAC classes: PRESERVED (zero modifications).

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks (== frozenset, == 'hello from allowed user'), queue.empty() for drops, assert_awaited_once() for ACK, caplog level+content checks |
| Negative/error paths | STRONG | Disallowed user (U_ATTACKER), missing user field, subtype messages (bot_message, message_changed), ordering check (subtype before user) |
| Mutation reasoning | ADEQUATE | Removing subtype check caught by 3 tests; removing allowlist caught by 3 tests; swapping check order caught by CheckOrdering test; removing WARNING log caught by 3 logging tests |
| Test independence | STRONG | Each test creates its own SlackChannel + mock SocketModeClient, no shared mutable state |
| Descriptive names | STRONG | All names describe scenario and expected outcome (test_disallowed_user_message_dropped, test_rejection_log_excludes_message_content) |

#### Data Safety
No data safety issues. Event handler performs read-only checks on incoming payloads with early returns. No writes to disk/DB. Frozenset is immutable. Queue put is async-safe (asyncio.Queue).

### Pass 2 INFORMATIONAL
- Implementation is clean and minimal (24 lines added across 3 files)
- Comments reference AC numbers for traceability
- Logger uses %s formatting (safe, avoids f-string interpolation)
- No informational findings worth noting

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Config field with default empty list | config.py L97-103: Field(default_factory=list) | test_field_exists_on_settings, test_default_is_empty_list, test_field_type_is_list_of_str | PASS |
| 2. SlackChannel accepts allowed_user_ids | slack.py L58: kwarg with frozenset default | test_init_accepts_allowed_user_ids_kwarg, test_allowed_user_ids_stored_as_frozenset, test_default_is_empty_frozenset | PASS |
| 3. Subtype messages dropped, ACK'd | slack.py L323-324: early return on subtype | test_bot_message_subtype_dropped, test_message_changed_subtype_dropped, test_subtype_message_acked_but_not_enqueued | PASS |
| 4. Disallowed user dropped | slack.py L327-334: allowlist check with early return | test_disallowed_user_message_dropped, test_disallowed_user_still_acked, test_message_without_user_field_dropped | PASS |
| 5. Rejected sender WARNING log | slack.py L330-332: logger.warning with user_id only | test_rejection_logged_at_warning, test_rejection_log_contains_user_id, test_rejection_log_excludes_message_content | PASS |
| 6. Allowed user enqueued | slack.py L336-337: text enqueued after all checks pass | test_allowed_user_message_enqueued, test_allowed_user_among_multiple_still_passes | PASS |
| 7. Empty allowlist accepts all | slack.py L327: 'if self._allowed_user_ids' skips check when empty frozenset | test_empty_allowlist_accepts_any_user, test_explicit_empty_frozenset_same_as_default | PASS |
| 8. Bootstrap passes frozenset | channel.py L38: frozenset(settings.slack_allowed_user_ids) | test_create_channel_passes_allowed_user_ids, test_create_channel_passes_empty_frozenset_for_empty_list | PASS |

### Verdict: PASS (confidence .94)

[[2026-03-14]] Sat 04:45
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added 'sender allowlist filtering' to Messaging row in tech stack table |
| 2 | Docstrings complete | Yes | Updated | Added allowed_user_ids to SlackChannel class Parameters section |
| 3 | sources/overview.md | No | N/A | Sources already added during research task #526 (5 Slack API entries present) |
| 4 | README.md | No | N/A | No CLI changes (config-only feature) |
| 5 | Research doc linked | Yes | Pass | docs/research/slack-sender-validation.md exists, referenced in task body |

### Files Updated
- .github/copilot-instructions.md (Messaging row)
- src/owlbear/channels/slack.py (docstring only)

### Scratch Files Cleaned
- None (no docs/scratch/801-* files found)

[[2026-03-14]] Sat 05:28
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Test file exists | tests/test_slack_sender_validation.py, 22 tests in 9 TestFromAC classes | PASS |
| 2. Tests cover all 8 AC lines from #795 | ConfigField(3) ConstructorKwarg(3) SubtypeFilter(3) UserAllowlistFilter(3) RejectionLogging(3) AllowedUserEnqueued(2) EmptyAllowlistAcceptsAll(2) BootstrapWiring(2) CheckOrdering(1) | PASS |
| 3. All tests FAIL before builder | Commit a4818a9 RED; 7173629 GREEN | PASS |
| 4. Ruff clean | All checks passed on test + impl files | PASS |

### Test Results
- pytest (scoped): 22/22 passed
- pytest (full suite): 3343 passed, 37 failed (all pre-existing: trafilatura, consolidation RED, pipeline e2e)
- ruff: clean

### Implementation Verified
- slack.py L323-337: subtype filter + user allowlist + WARNING log
- config.py L97: slack_allowed_user_ids field
- channel.py L38: frozenset wiring
- copilot-instructions.md: sender allowlist filtering added to Messaging row

### Commits Verified
- a4818a9: test: add failing tests for Slack sender validation (#801, test-writer)
- 7173629: feat: add Slack sender validation (#801, builder)
- 7821c8a: docs: update docstring (#795, writer)

### Confidence: .97
### Action: archive
