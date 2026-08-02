---
id: 631
title: Revisit blocked-task DR scan when notification channel is enabled
status: archived
priority: medium
created: 2026-04-05T12:53:09.6563754+02:00
updated: 2026-04-05T23:49:51.5361147+02:00
started: 2026-04-05T23:49:51.5361147+02:00
completed: 2026-04-05T23:49:51.5361147+02:00
tags:
    - phase-3
    - scope:orchestrator
    - scope:notifications
    - type:build
class: standard
---

## Objective

When a notification channel (Slack, Teams, or alternative) becomes available, implement the blocked-task scan that feeds into `Notifier.on_decision_request()`.

## Context

- Decision #514 deferred the notification feature (no Slack/Teams available).
- Task #348 researched this and recommended deferral — see `.owlbear/research/blocked-task-scan-decision-notifications.md`.
- The dispatch planner already emits `pending` counts (`decisions_t2`, `decisions_t3`, `actions`) in its JSON output.
- `bearclaw status` already shows blocked tasks with reasons.
- The scan should: (1) call `read_board()` with `--blocked` flag, (2) detect tasks blocked on pending DRs, (3) trigger `Notifier.on_decision_request(task_id, reason)`.

## AC

- [ ] Notification channel is available and configured
- [ ] `read_blocked_tasks()` added to board.py (uses `--blocked` flag)
- [ ] Blocked-task scan runs once per cycle in `run_loop()`, before wave assembly
- [ ] `Notifier.on_decision_request()` called for each blocked task with DR pending
- [ ] Scan is no-op when `notifier=None`
- [ ] Unit tests with mock notifier verify callbacks fire

## Predecessors

- #348 (research, deferred)
- #514 (decision: defer notifications)
- #344 (Notifier protocol — must be built first)
- #347 (loop integration — must be built first)

[[2026-04-05]] Sun 20:51
## Research
- Research doc: .owlbear/research/revisit-blocked-task-dr-scan-notification.md
- Sources: 8 studied, 6 high-relevance (validation pass on existing research)
- Recommendation: Keep deferred — Decision #514 unchanged, zero notification code exists, #597 (manual Teams verification) is critical path (confidence: .85)
- Follow-up tasks created: none (#597 already exists as correct next step)
- Decision requests: none (T1 — applying existing approved decision)
- Archived #348 (superseded by #631, per architect recommendation)

## Challenge Results
- Challenger: SKIPPED (validation pass on existing research, no new recommendation)
- Confidence in prior research: .80 (from #348) — no revision needed

[[2026-04-05]] Sun 22:26
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: blocked-task DR scan |
| Interface clarity | PASS | AC lines 2-6 specific and testable |
| Dependency correctness | FAIL | #344 and #347 must-build-first but depends_on empty, both archived, zero notification code |
| Module layering | N/A | Prerequisite modules do not exist |
| TDD compliance | PASS | AC6 specifies unit tests |
| KISS/YAGNI | FAIL | Implementation against nonexistent infrastructure |
| Premise challenge | FAIL | Decision #514 (Defer) in effect. Own research: Keep deferred (.85). #597 unresolved |
| Pattern consistency | N/A | No notification patterns exist |
| Security surface | N/A | No new boundaries until channel exists |
| Single domain | PASS | Notifications domain only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Channel available | UNMET PRECONDITION | #514 defers, #597 unresolved |
| AC2: read_blocked_tasks() | Verifiable | Depends on nonexistent infrastructure |
| AC3: Scan in run_loop() | Verifiable | Depends on #347, archived |
| AC4: on_decision_request() | Verifiable | Depends on #344, archived |
| AC5: No-op notifier=None | Verifiable | Good defensive pattern |
| AC6: Unit tests | Verifiable | Standard TDD |

### Challenge Results
- Challenger: SKIPPED (REJECT verdict)
- Rationale: Three blocking signals: own research recommends deferral, #514 unchanged, prerequisites archived

### Verdict: REJECT
### Reason
Own research recommends Keep at ideation/someday (.85). Decision #514 unchanged. Prerequisites #344 and #347 archived, never implemented. Zero notification code. Critical path #597 unresolved.

### Action Taken
Rejected to ideation. Tracking placeholder for when notification channel becomes available.

[[2026-04-05]] Sun 22:26
Architecture review: REJECT. Own research (.85) recommends deferral. Decision #514 unchanged. Prerequisites #344/#347 archived, never built. Zero notification code exists. Critical path #597 unresolved.

[[2026-04-05]] Sun 22:35
## Research (Validation Pass #2)
- Research doc: .owlbear/research/revisit-blocked-task-dr-scan-notification.md (unchanged)
- Validation: all 8 sources re-checked, no material changes since prior research (same day)
- Decision #514: unchanged (Defer). Zero notification code. #344/#347 archived. #597 unexecuted.
- Recommendation: Keep deferred, unchanged (confidence: .85)
- Follow-up tasks: none (#597 remains critical path)
- Decision requests: none (T1, revalidating existing approved decision)
- Challenge: SKIPPED (validation pass, no new recommendation)
- Note: Task cycled ideation to backlog to ideation (arch REJECT) once today. Advancing per pipeline; architect should archive if deferral permanent until #597 resolves.

[[2026-04-05]] Sun 23:49
## Architecture Review (Pass #3)

### Status: No material change since prior REJECT (same day)
- Decision #514: unchanged (Defer notifications)
- #597 (manual Teams verification): still in-progress, unclaimed, unresolved
- #344 (Notifier protocol): archived, never built
- #347 (loop integration): archived, never built
- Zero notification code exists in the codebase
- Own research recommends deferral with .85 confidence (confirmed twice)

### Verdict: REJECT
### Reason
Third review cycle in one day with identical findings. Task cannot progress until: (1) #597 resolves and confirms Teams Workflows availability, (2) Decision #514 is reopened, (3) prerequisite tasks #344/#347 are unarchived and built. Recommending ARCHIVE to stop pipeline cycling — reopen only when #597 completes and #514 is revised.
