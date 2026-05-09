---
id: 1464
title: 'E2b: Delete/merge stale package-local Python tests (43 files in serve/*/tests/)'
status: research
priority: important
created: 2026-05-09T03:32:04.274801+00:00
updated: 2026-05-09T03:32:25.850029+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
parent: 1415
depends_on:
- 1463
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Parent: #1415
Brief: .owlbear/research/1415-stale-test-cleanup.md

## Acceptance Criteria
P1: 43 task-scoped test files in serve/*/tests/ cleaned up (delete duplicates, rename singles, merge multiples)
P2: Package-local test suites pass with same or better pass count
P3: kanban package (22 files) and mcp-kanban (13 files) are largest batches

## Scope
In scope: serve/*/tests/ task-scoped files only
Out of scope: tests/ root, frontend tests