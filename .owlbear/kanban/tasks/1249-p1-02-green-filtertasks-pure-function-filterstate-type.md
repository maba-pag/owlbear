---
id: 1249
title: 'P1-02: GREEN — filterTasks pure function + FilterState type'
status: research
priority: critical
created: 2026-05-01T04:34:45.636679+00:00
updated: 2026-05-01T04:37:37.047382+00:00
tags:
- phase-1
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1248
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- filterTasks function exported from lib/filterTasks.ts
- FilterState interface exported from the same module
- All #1248 unit tests pass (GREEN)
- Pure function — no React imports, no side effects
- AND semantics across all four dimensions

## In Scope
- filterTasks implementation
- FilterState type (may already exist from #1248 if co-located)

## Out of Scope
- React components
- Memoization (React Compiler handles this at call sites)

Brief: see parent #1247