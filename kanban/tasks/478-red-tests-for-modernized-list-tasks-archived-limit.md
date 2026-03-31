---
id: 478
title: 'RED: tests for modernized list_tasks (archived, limit, reverse, blocked tri-state, lean JSON)'
status: ideation
priority: needed
created: 2026-03-31T06:13:41.4018366+02:00
updated: 2026-03-31T06:13:41.4018366+02:00
tags:
    - scope:mcp
    - ' type:test'
    - ' phase-2'
depends_on:
    - 472
class: standard
---

## Acceptance Criteria

- [ ] Test archived=True passes --archived; archived=False omits it
- [ ] Test limit>0 passes --limit N; limit=0 omits it
- [ ] Test reverse=True passes --reverse; reverse=False omits it
- [ ] Test blocked=True passes --blocked (not --not-blocked)
- [ ] Test blocked=False passes --not-blocked (not --blocked)
- [ ] Test blocked=None passes neither flag
- [ ] Test lean JSON output: mock JSON with body/file/created/updated fields, verify they are stripped from result
- [ ] All tests fail before implementation (RED phase)

## Design Notes

Follow existing _patch_run() mock pattern in test_server.py. For lean JSON test, mock _run_kanban to return a JSON string with all fields, verify list_tasks strips the noisy ones.

See docs/research/modernize-list-tasks.md for full analysis.
