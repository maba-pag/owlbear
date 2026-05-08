---
id: 1415
title: 'E2: Stale test cleanup — delete/archive 219 task-scoped tests from completed
  tasks'
status: research
priority: important
created: 2026-05-07T23:16:25.317145+00:00
updated: 2026-05-07T23:18:14.530966+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
parent: 1403
depends_on:
- 1410
- 1407
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: Task-scoped test files (`test_*_{task_id}.py`) for completed/archived tasks identified and removed from `tests/`
P2: Before: ~219 stale task-scoped tests in `tests/`. After: only tests for active/in-progress tasks remain as task-scoped files
P2: Valuable test coverage from deleted files consolidated into durable module tests in `serve/*/tests/` per C2 conventions
P2: No test coverage regression — overall test pass rate and coverage percentage unchanged or improved after cleanup
P3: Verification by counting remaining `test_*_{task_id}.py` files in `tests/` against board state; running full test suite to confirm no regressions

## Scope

**In scope:** Stale test identification, deletion, coverage consolidation where warranted
**Out of scope:** Test convention changes (C2), reviewer changes (B1), new test creation beyond consolidation