---
id: 1463
title: 'E2a: Delete/merge stale Python root tests (82 files in tests/)'
status: research
priority: important
created: 2026-05-09T03:32:04.142951+00:00
updated: 2026-05-09T03:32:25.707047+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
parent: 1415
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Parent: #1415
Brief: .owlbear/research/1415-stale-test-cleanup.md

## Acceptance Criteria
P1: 20 task-scoped test files with existing durable equivalents deleted from tests/
P1: 21 single-file task-scoped tests renamed to drop _{id} suffix (become durable module tests)
P2: 40 multi-file groups (16 modules) merged into single durable test files
P2: Full Python test suite passes with same or better pass count after cleanup
P3: test_decisions_1218.py inspected — fix or document why it's broken

## Scope
In scope: tests/ directory Python files only (test_*_{task_id}.py pattern)
Out of scope: serve/*/tests/, frontend tests, creating new test coverage