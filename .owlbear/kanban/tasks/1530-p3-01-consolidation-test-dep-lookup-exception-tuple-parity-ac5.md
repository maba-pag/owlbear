---
id: 1530
title: 'P3-01: consolidation test — dep-lookup exception tuple parity (AC5)'
status: research
priority: needed
created: 2026-05-13T12:18:18.887371+00:00
updated: 2026-05-13T12:18:18.887371+00:00
tags:
  - phase-3
  - scope:kanban
  - consolidation-test
parent: 1525
depends_on:
  - 1527
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

Write a consolidation test asserting that the exception tuple used for dep lookups in `start_work()` matches the one in `show_task()`.

Brief: see parent #1525

## Acceptance Criteria

- AC5: A test asserts that both `start_work()` and `show_task()` catch the same exception tuple `(FileNotFoundError, CorruptionError, ValueError, KeyError)` in their dep iteration loops — verified via AST inspection or source inspection

## Scope

- In scope: consolidation test in `serve/kanban/tests/` following the `test_consolidate_helpers.py` pattern
- Out of scope: implementation changes, MCP tests

## Context

- `show_task()` dep iteration at `agent_view.py` L253 uses `except (FileNotFoundError, CorruptionError, ValueError, KeyError)`
- `start_work()` must use the identical tuple (AC3)
- This test prevents future drift between the two dep-lookup sites

Proof bundle: behavioral