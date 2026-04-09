---
id: 727
title: 'P3-15: RED — activity.jsonl logging'
status: backlog
priority: needed
created: 2026-04-09T03:27:45.3139969+02:00
updated: 2026-04-09T03:27:45.3139969+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 722
class: standard
---

## Objective
Write failing tests for append-only activity.jsonl logging.

Brief: see parent #712 — action vocabulary: create, edit, move, claim, release, block, unblock, archive

## AC
- [ ] Test log entry format: {"timestamp":"<ISO>","action":"<verb>","task_id":<int>,"detail":"<string>"}
- [ ] Test each action verb produces correct log entry
- [ ] Test append-only semantics (new entries appended, existing entries untouched)
- [ ] Test log file created if missing
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_activity.py` (new)
