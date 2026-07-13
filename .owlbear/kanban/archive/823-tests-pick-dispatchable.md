---
id: 823
title: Tests — pick_dispatchable()
status: archived
priority: medium
created: '2026-04-10T21:23:01.614181+00:00'
updated: '2026-04-13T18:26:43.647978+00:00'
tags:
- phase-3
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 822
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `pick_dispatchable(engine, limit=25, tag="")` returns `list[Task]`
- Tests verify TDD gate: in-progress task without test-writer notes or non-impl tag is excluded
- Tests verify clarity gate: active-status task without bullet/numbered AC is excluded
- Tests verify priority ranking: critical > needed > important > nice-to-have > someday
- Tests verify status ranking: done > docs > review > in-progress > todo > backlog > research
- Tests verify result capping at `limit`
- Tests verify tag filtering
- Tests verify function is importable without MCP dependency
- Tests fail RED before implementation

## Context

Phase 3, step 1. Depends on #822 (Phase 2 complete).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/823-pick-dispatchable-test-design.md
- Sources: 9 studied, 7 high-relevance (≥.85)
- Recommendation: Real engine + temp filesystem fixture pattern (confidence: .85)
- Follow-up tasks created: none needed — #824 (implementation) already exists and depends on #823
- Decision requests: none

### Validation Pass (2026-04-13)
Existing research doc confirmed current. Key verifications:
- dispatch.py implemented via #824; tests/test_pick_dispatchable_823.py covers all 9 ACs
- 37/37 tests pass GREEN (data flow issue resolved: reads via task_io.read_task)
- Gate contracts (TDD + clarity), rank maps, tag filter, limit cap all match between doc and implementation
- Challenge: N/A — T1 test task with established patterns
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only `pick_dispatchable()` — one function, one test file |
| Interface clarity | PASS | AC defines exact signature `(engine, limit=25, tag="")`, gate behaviors, rank orders, limit semantics, tag filtering |
| Dependency correctness | PASS | depends_on=[822] — #822 archived (done) |
| Module layering | PASS | Tests in `tests/` import from `owlbear_kanban.dispatch` — correct direction |
| TDD compliance | PASS | This IS the test task; AC9 requires RED before implementation |
| KISS/YAGNI | PASS | 37 tests, one class per AC, no speculative coverage |
| Premise challenge | PASS | Custom dispatch logic for kanban engine — no existing capability covers this |
| Pattern consistency | PASS | Uses real-engine + `tmp_path` fixture pattern matching existing test conventions |
| Security surface | PASS | No new system boundaries — tests use temp filesystem fixtures |
| Single domain | PASS | `scope:kanban` only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 — returns `list[Task]` | Verifiable | 5 tests in `TestFromAC_PickDispatchableSignature` |
| AC2 — TDD gate | Verifiable | 5 tests in `TestFromAC_PickDispatchableTDDGate` incl. all non-impl tags |
| AC3 — Clarity gate | Verifiable | 8 tests in `TestFromAC_PickDispatchableClarityGate` covering all active statuses |
| AC4 — Priority ranking | Verifiable | 3 tests in `TestFromAC_PickDispatchablePriorityRanking` |
| AC5 — Status ranking | Verifiable | 4 tests in `TestFromAC_PickDispatchableStatusRanking` incl. cross-dimension |
| AC6 — Limit capping | Verifiable | 4 tests in `TestFromAC_PickDispatchableLimit` incl. edge cases (0, default 25) |
| AC7 — Tag filtering | Verifiable | 5 tests in `TestFromAC_PickDispatchableTagFilter` |
| AC8 — Importable w/o MCP | Verifiable | 3 tests in `TestFromAC_PickDispatchableImport` |
| AC9 — RED before impl | Verifiable | Docstring documents RED-phase intent; validated by pipeline |

### Challenge Results
- Challenger: reconsider (6 concerns raised)
- Architect response: **Rebutted all 6.**
  1. `__init__.py` import concern: invalid — `dispatch.py` exists, 37/37 tests pass GREEN
  2. AC2 wording: standard project phrasing, tests unambiguously verify behavior
  3. AC3 "bullet/numbered AC" scope: clarity gate checks structured content, matching documented behavior
  4–6. Tiebreaker/stability/private attribute: implementation details for #824, not AC requirements for this test task

### Codebase Verification
- Test file: `tests/test_pick_dispatchable_823.py` — 37 tests, all pass
- Implementation: `serve/kanban/src/owlbear_kanban/dispatch.py` — `pick_dispatchable()` with gate predicates and rank maps
- Non-impl tag `type:test` already present

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 9 ACs verifiable with precise test coverage. No AC refinement needed.
[[2026-04-13]]
## Test-Writer Notes

**Status:** Non-implementation pass-through — task tagged `type:test` (non-impl tag per Step 1a protocol).

**Anomalous state:** Test file and implementation both pre-exist from a prior pipeline cycle (test-writer + builder already completed RED → GREEN via #824). Arch Reviewer validated and re-queued to `todo`.

**Test file:** `tests/test_pick_dispatchable_823.py`

| Class | AC | Tests | Status |
|-------|----|-------|--------|
| `TestFromAC_PickDispatchableImport` | AC8 | 3 | GREEN |
| `TestFromAC_PickDispatchableSignature` | AC1 | 5 | GREEN |
| `TestFromAC_PickDispatchableTDDGate` | AC2 | 5 | GREEN |
| `TestFromAC_PickDispatchableClarityGate` | AC3 | 8 | GREEN |
| `TestFromAC_PickDispatchablePriorityRanking` | AC4 | 3 | GREEN |
| `TestFromAC_PickDispatchableStatusRanking` | AC5 | 4 | GREEN |
| `TestFromAC_PickDispatchableLimit` | AC6 | 4 | GREEN |
| `TestFromAC_PickDispatchableTagFilter` | AC7 | 5 | GREEN |

**Total:** 37 tests — all pass GREEN (implementation `dispatch.py` already exists via #824).

**AC coverage:** All 9 ACs covered. No gaps.

**RED phase note:** Tests were written RED in a prior cycle. Implementation (#824) subsequently made them GREEN. Re-verified run: 37/37 pass.

**Ruff:** No issues (pre-existing file, no changes made).
[[2026-04-13]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
- Test run: 37/37 passed, 0 failed.
- Ruff: no issues (pre-existing file, no changes made).
- Evidence: `tests/test_pick_dispatchable_823.py` — all 8 TestFromAC_* classes GREEN.
[[2026-04-13]]
## Review Evidence

**pytest:** 37 passed, 0 failed — exit 0  
**ruff:** clean — exit 0  
**Coverage:** `owlbear_kanban.dispatch` 95% (threshold 90% ✓)

### AC Compliance
| AC | Class | Assertion Quality |
|----|-------|-------------------|
| AC1 list[Task] | TestFromAC_PickDispatchableSignature | STRONG |
| AC2 TDD gate | TestFromAC_PickDispatchableTDDGate | STRONG |
| AC3 Clarity gate | TestFromAC_PickDispatchableClarityGate | STRONG |
| AC4 Priority rank | TestFromAC_PickDispatchablePriorityRanking | STRONG |
| AC5 Status rank | TestFromAC_PickDispatchableStatusRanking | STRONG |
| AC6 Limit cap | TestFromAC_PickDispatchableLimit | STRONG |
| AC7 Tag filter | TestFromAC_PickDispatchableTagFilter | ADEQUATE (order-of-ops test weak) |
| AC8 MCP import | TestFromAC_PickDispatchableImport | ADEQUATE (vars() check misses aliased imports) |
| AC9 RED phase | Meta-condition; docstring-documented; prior cycle validated | N/A |

All 8 TestFromAC_ classes intact — no modifications detected.

**Non-AC informational gap:** dispatch.py:143–145 `blocked` and `claimed_by` gates have zero test coverage. Outside AC scope. Recommended follow-up task to add coverage.

**Minor quality items:** L190 StopIteration risk; L368/L407 sequence assertions would benefit from len guard.

**Deductions:** -.02 AC7 weak order proof, -.02 AC8 narrow detection, -.01 L190 StopIteration, -.01 non-AC gap

**Confidence: .94 → PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test task — no behavior/API added by #823; dispatch.py created by #824 |
| 2 | Module docstrings | Yes | Verified | Module docstring covers all 9 ACs; _make_kanban_dir, _task_content, _add_task each have docstrings; TestFromAC_* classes have no class docstrings per established convention (matches test_kanban_engine_listing.py); dispatch.py public API fully documented |
| 3 | External attribution | No | N/A | All 9 research sources are internal project files — no external repos or articles |
| 4 | CLI changes | No | N/A | Test task — no CLI additions or changes |
| 5 | Research doc | Yes | Verified | .owlbear/research/823-pick-dispatchable-test-design.md exists and is linked from task body |

### Files Updated
- None

### Scratch Files Cleaned
- None found (no .owlbear/scratch/823-* files exist)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — returns list[Task] | TestFromAC_PickDispatchableSignature (5 tests), all PASS | PASS |
| AC2 — TDD gate | TestFromAC_PickDispatchableTDDGate (5 tests), all PASS | PASS |
| AC3 — Clarity gate | TestFromAC_PickDispatchableClarityGate (8 tests), all PASS | PASS |
| AC4 — Priority ranking | TestFromAC_PickDispatchablePriorityRanking (3 tests), all PASS | PASS |
| AC5 — Status ranking | TestFromAC_PickDispatchableStatusRanking (4 tests), all PASS | PASS |
| AC6 — Limit capping | TestFromAC_PickDispatchableLimit (4 tests), all PASS | PASS |
| AC7 — Tag filtering | TestFromAC_PickDispatchableTagFilter (5 tests), all PASS | PASS |
| AC8 — Importable w/o MCP | TestFromAC_PickDispatchableImport (3 tests), all PASS | PASS |
| AC9 — RED before impl | Commit 47f7430f (07:15) precedes 92d30124 (14:30); docstring documents RED intent | PASS |

### Test Results
- pytest (task): 37/37 passed, 0 failed
- pytest (full suite): 4133 passed, 380 failed, 8 skipped — 0 failures in task scope
- ruff: clean

### Reviewer Evidence
Present, detailed, PASS at .94. Minor quality items flagged (AC7 order proof, AC8 detection narrowness) — non-blocking, evidence exists for both.

### Architect Quality: 5/5
Exact function signature specified, return type, gate behaviors, ranking orders, limit semantics, tag filtering — all precise enough to write tests from directly. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: none (-.00)
- AC quality ≤ 3: no, score 5 (-.00)
- Missing reviewer evidence: no, present and detailed (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: 1.00
### Action: archive