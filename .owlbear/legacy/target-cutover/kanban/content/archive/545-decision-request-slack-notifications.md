---
id: 545
title: Decision-request Slack notifications
status: archived
priority: medium
created: 2026-04-02 10:28:27.827401+02:00
updated: 2026-04-05 03:55:00.172739+02:00
started: 2026-04-05 03:55:00.172739+02:00
completed: 2026-04-05 03:55:00.172739+02:00
tags:
- phase-3
- ' scope:notifications'
- ' type:build'
depends_on:
- 26
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Notify the user via Slack when a task is blocked with a decision or action request, so they know input is needed without checking the board.

## Acceptance Criteria
- [ ] During `run_loop()` board-read cycle, detect tasks blocked with decision/action requests (marker: `docs/decisions/pending/` reference in block reason or task body)
- [ ] Send Slack notification for newly-blocked tasks only (deduplication: track notified task IDs across cycles, reset when task is unblocked)
- [ ] Message format: "Decision needed: #{task_id} {title} -- {block_reason}"
- [ ] Uses the `Notifier` protocol from #26
- [ ] Unit tests with mocked notifier verifying deduplication and message format

## Context
Split from #26 (Slack notification integration). This requires board observation with state tracking, which is a separate concern from dispatch-event notifications.
