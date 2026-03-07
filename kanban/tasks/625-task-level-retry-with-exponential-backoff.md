---
id: 625
title: Task-level retry with exponential backoff
status: backlog
priority: important
created: 2026-03-07T05:21:17.2220292+01:00
updated: 2026-03-07T13:58:57.0420683+01:00
started: 2026-03-07T13:58:57.0420683+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 614
    - 512
class: standard
---

When agent run fails on a kanban task, schedule retry: delay = min(10s * 2^(attempt-1), max_backoff). Max 5 attempts before blocking task. See docs/orchestration-agent-frameworks-research.md S3.2 and docs/symphony-research.md S3.2

AC:
- [ ] RetryEntry model with attempt count, next_due, error
- [ ] Exponential backoff formula: min(10s * 2^(attempt-1), max_backoff)
- [ ] Max 5 retries before auto-block
- [ ] Continuation retry (1s) after success if task still active

Architecture notes:
- Distinct from #512 (message-level retry dedup within a single turn) - this is task-level retry across agent dispatches
- Resolve #512 first to clarify retry layer boundaries
- Integrates into poll-dispatch-reconcile loop (depends on #614)
