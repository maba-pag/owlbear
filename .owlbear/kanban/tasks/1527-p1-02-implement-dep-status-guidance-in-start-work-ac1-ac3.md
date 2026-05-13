---
id: 1527
title: 'P1-02: implement dep-status guidance in start_work (AC1-AC3)'
status: research
priority: critical
created: 2026-05-13T12:17:51.690274+00:00
updated: 2026-05-13T12:17:51.690274+00:00
tags:
  - phase-1
  - scope:kanban
  - feature
parent: 1525
depends_on:
  - 1526
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

Implement dep-status guidance in `agent_view.start_work()`: after successful claim, iterate deps, compute dep_status, and return guidance string if blocked.

Brief: see parent #1525

## Acceptance Criteria

- AC1: `start_work()` on a dep-blocked task returns `guidance` containing exactly one string with format `"⚠️ This task has unresolved dependencies (IDs: {comma-separated ints}). Review and confirm with the user that starting this work is intentional."`
- AC2: `start_work()` on a task with no deps or all resolved deps returns `guidance == []`
- AC3: Dep lookup exceptions `(FileNotFoundError, CorruptionError, ValueError, KeyError)` silently continue (resilience)

## Scope

- In scope: ~15 LoC inline dep iteration in `agent_view.start_work()` after successful claim, passing guidance to `_to_single_response()`
- Out of scope: MCP layer, schema changes, helper extraction, redirect handling

## Context

- Mirror the dep iteration pattern from `show_task()` at L214
- Use `engine._compute_dep_status()` to determine blocked status
- Pass guidance via existing `_to_single_response(task, guidance=guidance)`

Proof bundle: behavioral