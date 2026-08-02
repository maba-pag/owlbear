---
id: 809
title: Tests — revision counter
status: archived
priority: medium
created: '2026-04-10T21:21:30.609548+00:00'
updated: '2026-04-12T07:18:11.187451+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `engine.revision` property starts at 0
- Tests verify revision increments on every write (`create_task`, `edit_task`, `move_task`, `claim_task`, `release_task`, `start_work`, `end_work`)
- Tests verify revision is read-only (no setter)
- Tests verify revision is per-instance (two engine instances have independent counters)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/revision-counter-tests-809.md
- Sources: 5 studied (all codebase), 3 high-relevance
- Recommendation: 10 test cases — exact deltas for atomic ops, `> before` for compounds (confidence: 0.92)
- Key finding: implementation already exists in engine.py; tests will pass GREEN immediately — TDD RED phase is moot
- Revision delta table mapped for all 7 AC operations including compound delegation paths
- Follow-up tasks created: none (this task IS the follow-up)
- Decision requests: none
[[2026-04-12]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: `engine.revision` starts at 0 | PASS — verifiable, `_revision = 0` at L66 of engine.py | None |
| AC2: revision increments on every write (7 ops listed) | PASS — verifiable. Atomic ops increment by exactly 1. Compound ops (`start_work` delegates to `claim_task`; `end_work` delegates to 2-3 internal calls). Assert exact delta for atomic ops; assert `revision > before` for compound ops to stay resilient to delegation changes. | None |
| AC3: revision is read-only (no setter) | PASS — verifiable via `AttributeError` on assignment | None |
| AC4: per-instance (independent counters) | PASS — verifiable, `_revision` is instance attr | None |
| AC5: Tests fail RED before implementation | INVALID — implementation pre-exists in engine.py (L66, L74-76, increments at L287, L394, L431, L472, L497). Tests will pass GREEN immediately. **Test-writer: ignore this AC line.** Write tests as regression coverage verifying existing behavior. |  Refinement noted below |

### AC5 Refinement (edit_task unavailable)

AC5 "Tests fail RED before implementation" is factually impossible — the revision counter is already implemented. The test-writer should treat this task as regression test coverage for existing behavior, not TDD RED phase. The research doc (`.owlbear/research/revision-counter-tests-809.md`) already documents this.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for revision counter |
| Interface clarity | PASS | 7 operations specified, property name explicit |
| Dependency correctness | PASS | No deps listed; correct per research — no Phase 1 dependencies |
| Module layering | N/A | Test-only task |
| TDD compliance | PASS (with caveat) | AC5 is moot but task tagged `type:test` — tests precede no impl task |
| KISS/YAGNI | PASS | 10 test cases, no over-testing |
| Premise challenge | PASS | Revision counter exists; regression tests are valuable |
| Pattern consistency | PASS | Follows `test_kanban_engine_crud.py` fixture pattern (`_BASE_CONFIG_YAML`, `kanban_dir`, `engine` fixtures) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | `scope:mcp-kanban` only |

### Compound Operation Guidance

- `start_work`: delegates to `claim_task` — revision delta is +1
- `end_work(success)`: `edit_task` + `release_task` + `move_task` — delta +3
- `end_work(fail)`: `edit_task` + `release_task` — delta +2
- `end_work(block)`: `edit_task` + `edit_task` + `release_task` — delta +3
- `end_work(reject)`: `edit_task` + `release_task` + `move_task` — delta +3
- Recommend: assert `revision > before` for compounds to decouple tests from internal delegation

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in tool allowlist
- Architect response: Proceeded without challenge. Low-risk test task with thorough research backing.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC5 refinement documented — test-writer should write regression tests for existing behavior, not RED-phase tests.
[[2026-04-12]]
## Test-Writer Notes

**Test file:** `tests/test_revision_counter_809.py`
**Class:** `TestFromAC_RevisionCounter`

### Tests by category

| Category | Tests | Count |
|----------|-------|-------|
| Happy | starts_at_zero, create/edit/move/claim/release/start_work/end_work all increment | 8 |
| Boundary | end_work all four outcomes (success/fail/block/reject) | 4 |
| Error | revision_is_read_only (AttributeError) | 1 |
| Edge | per-instance independence | 1 |

**Total: 13 tests — all PASS GREEN** (regression coverage, not RED phase)

### AC coverage

| AC Line | Tests |
|---------|-------|
| AC1 — starts at 0 | `test_revision_starts_at_zero` |
| AC2 — increments on create_task | `test_create_task_increments_revision` |
| AC2 — increments on edit_task | `test_edit_task_increments_revision` |
| AC2 — increments on move_task | `test_move_task_increments_revision` |
| AC2 — increments on claim_task | `test_claim_task_increments_revision` |
| AC2 — increments on release_task | `test_release_task_increments_revision` |
| AC2 — increments on start_work | `test_start_work_increments_revision` |
| AC2 — increments on end_work | `test_end_work_success/fail/block/reject_increments_revision` (4 tests) |
| AC3 — read-only | `test_revision_is_read_only` |
| AC4 — per-instance | `test_revision_is_per_instance` |
| AC5 — tests fail RED | **N/A** — architect review: implementation pre-exists at engine.py L66/L74-76; tests are regression coverage per architect directive |

### Notes

- Atomic ops (create/edit/move/claim/release) assert exact delta `+1`.
- Compound ops (start_work, end_work×4) assert `revision > before` to decouple from delegation changes — per architect guidance.
- end_work(reject) added as 4th compound outcome for complete AC2 coverage.
- ruff: no issues.
[[2026-04-12]]
## Builder Notes

**Verification-only pass** — task was stale at in-progress; no implementation changes needed or made.

### Evidence
- Test file: `tests/test_revision_counter_809.py` (pre-existing, written by test-writer)
- Tests: **13 passed, 0 failed**
- Ruff: **clean** (exit 0)
- Coverage: revision counter already implemented in `engine.py` (L66, L74-76); tests are regression coverage per architect directive

### Files changed
None — verification only.
[[2026-04-12]]
## Review Evidence

### Tests (Quality-Runner — independent run)
- **13 passed, 0 failed**
- ruff: clean (exit 0)
- Coverage: `owlbear_kanban.engine` → 61% (expected — targeted regression tests, not full engine suite)

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — starts at 0 | `assert engine.revision == 0` on fresh fixture; exact equality | COVERED |
| AC2 — create_task | `assert == before + 1`; exact delta | COVERED |
| AC2 — edit_task | `assert == before + 1`; exact delta | COVERED |
| AC2 — move_task | `assert == before + 1`; exact delta | COVERED |
| AC2 — claim_task | `assert == before + 1`; exact delta | COVERED |
| AC2 — release_task | `assert == before + 1`; exact delta | COVERED |
| AC2 — start_work | `assert > before`; compound per architect guidance | COVERED |
| AC2 — end_work ×4 outcomes | `assert > before` each; compound per architect guidance | COVERED |
| AC3 — read-only | `pytest.raises(AttributeError)` on assignment | COVERED |
| AC4 — per-instance | exact `== 2` and `== 0` on two independent instances | COVERED |
| AC5 — RED phase | N/A per architect directive | N/A |

### TestFromAC Integrity
Builder made no changes to test file. All 13 `TestFromAC_RevisionCounter` methods: PRESERVED.

### Test Quality
All STRONG. Atomic ops: exact ±1 delta. Compound ops: `> before` per architect mandate. Mutation-resistant. Independent fixtures. Descriptive names.

### Security
Test-only file; no security surface.

### Deductions: none
### Confidence: 0.95 → PASS
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task; no application logic modified; `copilot-instructions.md` accurate |
| 2 | Module docstrings | No | N/A | Only `tests/test_revision_counter_809.py` created; not an application module |
| 3 | External attribution | No | N/A | Research sources were all codebase-internal (task body: "5 studied, all codebase") |
| 4 | CLI changes | No | N/A | No CLI touched |
| 5 | Research doc | Yes | Verified | `.owlbear/research/revision-counter-tests-809.md` exists and linked in task body; follow-ups: none required ("this task IS the follow-up") |

### Files Updated
None — no docs impact.

### Scratch Files Cleaned
None found (`.owlbear/scratch/809-*` — no matches).
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — starts at 0 | `test_revision_starts_at_zero`: `assert engine.revision == 0` | PASS |
| AC2 — create_task | `test_create_task_increments_revision`: `assert == before + 1` | PASS |
| AC2 — edit_task | `test_edit_task_increments_revision`: `assert == before + 1` | PASS |
| AC2 — move_task | `test_move_task_increments_revision`: `assert == before + 1` | PASS |
| AC2 — claim_task | `test_claim_task_increments_revision`: `assert == before + 1` | PASS |
| AC2 — release_task | `test_release_task_increments_revision`: `assert == before + 1` | PASS |
| AC2 — start_work | `test_start_work_increments_revision`: `assert > before` (compound) | PASS |
| AC2 — end_work ×4 | 4 tests (success/fail/block/reject): `assert > before` each | PASS |
| AC3 — read-only | `test_revision_is_read_only`: `pytest.raises(AttributeError)` | PASS |
| AC4 — per-instance | `test_revision_is_per_instance`: independent counters verified | PASS |
| AC5 — RED phase | N/A per architect directive — implementation pre-exists | N/A |

### Test Results
- pytest (task-scoped): 13 passed, 0 failed
- pytest (full suite): 3743 passed, 370 failed — failures are pre-existing (task adds only a test file, no source changes)
- ruff: All checks passed

### Architect Quality: 4/5
AC1–4 specific and verifiable. AC5 was factually impossible (implementation pre-exists) but architect review caught and refined it properly. Minor upstream gap.

### Deduction Breakdown
- AC lines without evidence: 0 (all covered) → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (present, detailed, PASS at .95) → no deduction
- Full-suite failures in task scope: 0 → no deduction
- Process note: test file and research doc were uncommitted by upstream agents — committed as leftovers by auditor (6961bc87)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6961bc87 | test | tests/test_revision_counter_809.py, .owlbear/research/revision-counter-tests-809.md | #809 |