---
id: 784
title: Corporate entity and relation type extensions
status: research
priority: needed
created: '2026-04-10T12:31:05.162187+00:00'
updated: '2026-04-13T00:14:37.402926+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 779
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `models.py` `EntityType` enum includes 5 new members: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- `models.py` `RelationType` enum includes 2 new members: GOVERNS, SUPERSEDES_VERSION
- All #779 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/models.py`

## Context
- WS-A: Schema + Models Foundation
- Scope items 6+7 from #775
- See research F3: entity/relation/prompt must ship atomically

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: enum extensions |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | **FAIL** | Depends on #779 which is in `research` (rejected as stale duplicate), not `done` |
| Module layering | PASS | Single-file change in knowledge domain |
| TDD compliance | N/A | Preceding test task #779 rejected as duplicate |
| KISS/YAGNI | **FAIL** | All AC lines already implemented — task is a no-op |
| Premise challenge | **FAIL** | Capability already exists: `models.py` already contains all 7 enum members. Implementation is complete. |
| Pattern consistency | PASS | — |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | knowledge domain only |

### AC Coverage — Already Implemented

| AC Line | Evidence | Status |
|---------|----------|--------|
| EntityType includes REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `models.py` L22-L26 | DONE |
| RelationType includes GOVERNS, SUPERSEDES_VERSION | `models.py` L38-L39 | DONE |
| All #779 tests pass | #779 rejected; coverage in `test_schema_extensions_754.py` (21 tests) | DONE |
| File: `serve/knowledge/src/owlbear_knowledge/models.py` | File exists with all members | DONE |

### Challenge Results
- Challenger: SKIPPED — REJECT verdict (no approve to challenge)
- Architect response: N/A

### Verdict: REJECT
### Action Taken: Rejected to research. Task is a stale decomposition artifact from archived parent #775. All AC lines are already satisfied in the codebase — the enum members exist in `models.py` and are fully tested by `test_schema_extensions_754.py`. Dependency #779 was also rejected as stale. Recommend orchestrator archive this task.</note>
<parameter name="move_to">research
[[2026-04-12]]
## Research

### Validation Pass — Stale No-Op Confirmed

Architecture review findings independently verified against current codebase state.

| AC Line | Evidence | Status |
|---------|----------|--------|
| EntityType: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `models.py` L22-L26 — all 5 members present | DONE |
| RelationType: GOVERNS, SUPERSEDES_VERSION | `models.py` L38-L39 — both members present | DONE |
| All #779 tests pass | `test_schema_extensions_754.py` — 59/59 green (21 directly cover AC) | DONE |
| File: models.py | File exists with all members | DONE |

**Test execution:** 59 passed in `test_schema_extensions_754.py` (5.40s). EntityType coverage: 15 tests (exist ×5, value ×5, round-trip ×5). RelationType coverage: 6 tests (exist ×2, value ×2, round-trip ×2).

### Research Gate (Trivial — N/A)

N/A — stale decomposition artifact. All AC satisfied. Parent #775 archived. Dependency #779 also stale (backlog, awaiting archival). No implementation work exists.

### Recommendation

Archive immediately. Confidence: .95. Zero follow-up tasks — no work remains.

### Note

`.owlbear/research/two-pass-review-checklist.md` references a prior task #784 (different topic: review checklist). Current #784 was created 2026-04-10; that doc is from 2026-03-13. Task ID was recycled — no conflict, just a data artifact.

- Research doc: N/A — trivial stale validation, no new doc warranted
- Sources: 3 internal (models.py, test_schema_extensions_754.py, #779 task body)
- Recommendation: Archive (confidence: .95)
- Follow-up tasks created: none
- Decision requests: none
[[2026-04-13]]
[[2026-04-13]]
## Architecture Review (3rd pass)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: enum extensions |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | **FAIL** | Depends on #779 which is in `research` (rejected 3× as stale duplicate) |
| Module layering | PASS | Single-file change in knowledge domain |
| TDD compliance | N/A | Preceding test task #779 rejected as duplicate |
| KISS/YAGNI | **FAIL** | All AC lines already implemented — task is a no-op |
| Premise challenge | **FAIL** | All 7 enum members exist in `models.py` L23-27, L40-41. Fully tested by `test_schema_extensions_754.py`. |
| Pattern consistency | PASS | — |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | knowledge domain only |

### Codebase Verification (3rd pass)

| AC Line | Evidence | Status |
|---------|----------|--------|
| EntityType: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `models.py` L23-27 — all 5 present | DONE |
| RelationType: GOVERNS, SUPERSEDES_VERSION | `models.py` L40-41 — both present | DONE |
| All #779 tests pass | #779 rejected 3×; coverage in `test_schema_extensions_754.py` (21+ tests) | DONE |
| File: models.py | File exists with all members | DONE |

### Challenge Results
- Challenger: SKIPPED — REJECT verdict (no approve to challenge)
- Architect response: N/A

### Verdict: REJECT
### Action Taken: Rejected to research (3rd cycle). This task is a stale decomposition artifact — parent #775 is archived (not found on board), dependency #779 is also stale-rejected. All AC lines verified satisfied in codebase for the 3rd time. **ESCALATION: Orchestrator must archive this task immediately to break the review loop.**