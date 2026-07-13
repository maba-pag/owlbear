---
id: 514
title: 'Test: Notifier protocol and SlackNotifier'
status: archived
priority: medium
created: 2026-04-01 07:07:05.261776+02:00
updated: 2026-04-04 07:10:07.839160+02:00
started: 2026-04-04 07:09:42.150941+02:00
completed: 2026-04-04 07:09:42.150941+02:00
tags:
- phase-3
- scope:notifications
- scope:orchestrator
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for the Notifier protocol and SlackNotifier (webhook + urllib).
See docs/research/slack-notification-v2.md for design.

## Acceptance Criteria
- [ ] Test file: `tests/test_notifications.py`
- [ ] Test `Notifier` protocol compliance: `isinstance(SlackNotifier(...), Notifier)` passes at runtime
- [ ] Test `SlackNotifier.on_dispatch(task_id, agent)`: verifies HTTP POST to webhook URL with JSON body containing mrkdwn `*Dispatched* #{task_id} to {agent}`
- [ ] Test `SlackNotifier.on_completion(task_id, agent, success=True)`: verifies message `*Completed* #{task_id} ({agent})`
- [ ] Test `SlackNotifier.on_completion(task_id, agent, success=False)`: verifies message `*Failed* #{task_id} ({agent})`
- [ ] Test `SlackNotifier.on_decision_request(task_id, reason)`: verifies message `*Decision needed* #{task_id} — {reason}`
- [ ] Test error handling: `urllib.request.urlopen` raising `URLError` is caught and logged, never propagates
- [ ] Test missing webhook URL: constructor with empty/None URL makes all methods no-op (returns without POST)
- [ ] All HTTP mocked via `unittest.mock.patch("urllib.request.urlopen")` — zero network calls
- [ ] All tests fail before implementation (TDD RED)

[[2026-04-01]] Wed 20:26
## Architecture Review
**Verdict:** BLOCK
**DR Verification:** No approved DR found for owning task #26 (docs/research/slack-notification-v2.md). Created docs/decisions/pending/514-slack-notification-approach.md (T3, impact_tier: 3, no auto-resolve).

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file location | Clear, verifiable | No change needed |
| Notifier protocol compliance | Clear, verifiable | No change needed |
| on_dispatch test | Clear with expected message format | No change needed |
| on_completion success/fail | Clear with expected messages | No change needed |
| on_decision_request test | Clear with expected message | No change needed |
| Error handling (URLError) | Clear, verifiable | No change needed |
| Missing webhook no-op | Clear, verifiable | No change needed |
| HTTP mocking constraint | Clear | No change needed |
| TDD RED constraint | Clear | No change needed |

### Architecture Notes
AC quality is good -- every line is testable pass/fail. No vague criteria. However, blocking because this task originates from T3 research (new capability: Slack notifications) with no approved decision request. The research doc (slack-notification-v2.md) recommends Option A (webhook + urllib) at .85 confidence with three alternatives. User must approve the approach before implementation proceeds.

Once the DR is approved, this task can return to backlog and proceed through the pipeline unchanged -- the AC is ready.

### Changes Made
- Created DR: docs/decisions/pending/514-slack-notification-approach.md
- Blocked #514 to ideation with T3 DR reason

### Dependencies
- Verified: #26 (research) is archived
- Downstream: #515 depends on #514, #518 on #515, #519 on #518 -- all transitively blocked



## Decision Resolved
Chosen: D: Defer / do nothing
User notes: No Slack available. Teams integration due to corp policy currently not possible. So deferring right now.
Source: docs/decisions/resolved/514-slack-notification-approach.md
Resolved: 2026-04-01
