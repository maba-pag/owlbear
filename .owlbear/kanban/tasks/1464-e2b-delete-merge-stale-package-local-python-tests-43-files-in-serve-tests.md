---
id: 1464
title: 'E2b: Delete/merge stale package-local Python tests (43 files in serve/*/tests/)'
status: in-progress
priority: important
created: 2026-05-09T03:32:04.274801+00:00
updated: 2026-05-09T14:56:53.256751+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
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
P1: All 43 task-scoped files in serve/*/tests/ processed per research doc (.owlbear/research/1464-package-local-test-cleanup.md): 21 renames (drop _NNNN suffix), 10 merge-new (→ 5 durables), 5 merge-into-durable, 7 merge-guidance (td:0)
P1: No test_*_[0-9]*.py files remain in serve/*/tests/ after cleanup (td:0)
P2: Each package's test suite (uv run pytest serve/{pkg}/tests/) passes with same or better pass count before and after each batch (td:0)

## Scope
In scope: serve/*/tests/ task-scoped files only
Out of scope: tests/ root, frontend tests

## Research
- Research doc: .owlbear/research/1464-package-local-test-cleanup.md
- Sources: 4 studied (all codebase-internal), 4 high-relevance
- 43 task-scoped files confirmed across 6 packages
- Categorization: 21 rename, 10 merge-new (5 groups), 5 merge-into-durable, 7 merge-guidance
- Recommendation: execute in 3 batches by operation type — renames first, merge-new second, merge-into-durable + guidance last (confidence: .90)
- Challenge: SKIPPED — T1 autonomous mechanical cleanup
- No follow-up task decomposition needed — this task proceeds as single builder unit

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: clean up 43 package-local task-scoped test files |
| Interface clarity | PASS | AC refined — specifies exact operation counts referencing research doc categorization |
| Dependency correctness | PASS | #1463 archived (done); dependency satisfied |
| Module layering | N/A | File rename/merge/delete only — no code changes |
| TDD compliance | N/A | No new code; verification via existing suite pass counts |
| KISS/YAGNI | PASS | Mechanical cleanup — no new abstractions |
| Premise challenge | PASS | 43 stale files confirmed by live workspace check (exact match to research) |
| Pattern consistency | PASS | Follows parent #1415 approach and sibling #1463 precedent |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Test Depth
All AC lines: (td:0) — mechanical file operations (rename, merge, delete)
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0, no architectural decisions

### Design Diverge
- Skipped — single approach (batch by operation type), no competing alternatives

### Verdict: APPROVE
- Refined AC: replaced vague "cleaned up" with specific operation counts; removed informational P3; added zero-remainder gate (no task-scoped files remain)
- Added `quality` tag for test-writer pass-through
- Dependency #1463 verified archived/done

[[2026-05-09]]
Architecture review complete. AC refined: replaced vague "cleaned up" with specific operation counts (21 rename, 10 merge-new, 5 merge-into-durable, 7 merge-guidance) referencing research doc; removed informational P3; added zero-remainder gate. Added `quality` tag for test-writer pass-through. All td:0 — mechanical file ops only. Challenger skipped. Dependency #1463 verified archived.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- All AC lines annotated `(td:0)`: mechanical file operations only (rename, merge, delete).
- Passing through to builder.