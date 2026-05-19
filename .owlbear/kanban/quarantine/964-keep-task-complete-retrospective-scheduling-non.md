---
id: 964
title: Keep TASK_COMPLETE retrospective scheduling non-blocking before background handoff
status: archived
priority: important
created: 2026-03-23T04:26:24.7473433+01:00
updated: 2026-03-24T04:26:42.1051667+01:00
started: 2026-03-24T04:26:42.1051667+01:00
completed: 2026-03-24T04:26:42.1051667+01:00
tags:
    - agent
    - daemon
    - hooks
    - scope:core
    - type:build
parent: 953
depends_on:
    - 953
class: standard
---

See docs/research/hook-triggered-background-worker-supervision.md section 5. AC: RetrospectiveHook.__call__ must hand work off without synchronous activity.jsonl parsing or kanban-md show subprocess calls on the awaited hook path, with tests proving the metadata lookup happens behind a non-blocking seam.

[[2026-03-24]] Tue 03:45

## Research

- Doc: docs/research/non-blocking-retrospective-hook-handoff.md

- Recommendation (.85): Move eligibility checks (_count_rejections + _get_priority) into the background task, keeping __call__ instant. Approach A from the analysis.

- Follow-up task created: #981 - Move RetrospectiveHook eligibility checks behind supervisor handoff (status: archived, priority: needed)

- Sources logged in docs/sources/overview.md
