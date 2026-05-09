---
id: 1463
title: 'E2a: Delete/merge stale Python root tests (82 files in tests/)'
status: backlog
priority: important
created: 2026-05-09T03:32:04.142951+00:00
updated: 2026-05-09T04:12:27.167988+00:00
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
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/1463-python-root-test-cleanup.md
- Sources: 4 studied, 4 high-relevance (all codebase-internal)
- Recommendation: proceed as T1 autonomous cleanup (confidence: .90)

### Key Findings
1. **Count correction:** 84 task-scoped files (not 82). 83 stale, 1 active (#1439). Brief's #1448 and #1450 completed since original analysis.
2. **DELETE ≠ simple delete:** The 22 files with durable equivalents have significant unique tests (e.g., durable cockpit_decisions_api has 10 tests but task-scoped files have 72). Must merge unique tests into durable before deleting.
3. **test_decisions_1218.py:** Dead RED-phase test — imports `_find_decision_path` which never existed. Security concern (path traversal) addressed by `_validate_decision_id()`. Safe to delete.
4. **Baseline:** 3272 collected tests. Suite must pass ≥ 3272 after cleanup.
5. **Execution order:** rename (21) → delete-with-merge (22) → merge (40/16 groups) → delete 1218 → full suite verification.
6. **AC update needed:** P1 "20 files" → "22 files"; P1 "deleted" → "merged-then-deleted".

### Updated ACs
- P1: 22 task-scoped files merged into durable equivalents then deleted
- P1: 21 single-file task-scoped tests renamed (drop _{id} suffix)
- P2: 40 multi-file groups (16 modules) merged into durable files
- P2: Full suite passes ≥ 3272 tests
- P3: test_decisions_1218.py — delete (broken import, security covered elsewhere)