---
id: 631
title: Revisit blocked-task DR scan when notification channel is enabled
status: backlog
priority: someday
created: 2026-04-05T12:53:09.6563754+02:00
updated: 2026-04-05T20:51:49.9710934+02:00
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
