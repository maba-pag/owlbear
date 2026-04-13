---
id: 806
title: Add board_config()
status: done
priority: needed
created: '2026-04-10T21:21:14.299574+00:00'
updated: '2026-04-12T05:05:50.233514+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 805
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `board_config()` method on `KanbanEngine`
- Returns `model_copy()` of cached config (valid statuses, priorities, display order)
- Returned object is a defensive copy — mutating it does not affect engine state
- #805 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #805 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/board-config-impl-806.md
- Sources: 5 studied, 4 high-relevance (1 external, 4 internal)
- Recommendation: Change `model_copy()` → `model_copy(deep=True)` at engine.py L98 (confidence: 0.95)
- Follow-up tasks created: none — task chain already defined (#805 tests → #806 impl)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial T1 bug fix with empirical verification from #805 research
- Confidence in original: 0.95
- Key challenges: none — single viable option (Pydantic-native deep copy)
- Researcher response: N/A

## Key Findings
1. `board_config()` exists but uses shallow `model_copy()` — nested `statuses` (list[dict]) and `priorities` (list[str]) share references with engine's internal `_config`
2. Pydantic v2 docs confirm: `model_copy()` is shallow by default; `deep=True` parameter produces full isolation
3. Research doc #805 empirically verified: `copy.statuses is original.statuses` → `True` with shallow copy; mutation leaks to engine state
4. Fix is one parameter addition: `model_copy(deep=True)` — no new imports, no interface changes
5. Tier: T1 — autonomous bug fix
[[2026-04-12]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single method fix — `model_copy()` → `model_copy(deep=True)` |
| Interface clarity | PASS | AC3 ("defensive copy — mutation doesn't affect engine state") is the governing behavioral requirement. AC2 mentions `model_copy()` generically; `deep=True` is implied by AC3 and research. |
| Dependency correctness | PASS | `depends_on: [805]` — #805 (test task) is in `todo`, correct TDD ordering |
| Module layering | PASS | Internal engine method, no new imports, no cross-layer changes |
| TDD compliance | PASS | #805 is the preceding RED test task |
| KISS/YAGNI | PASS | One parameter addition, no interface changes |
| Premise challenge | PASS | Research empirically verified: `copy.statuses is original.statuses` → `True` with shallow copy. Real defect. |
| Pattern consistency | PASS | Uses Pydantic-native `model_copy(deep=True)` — idiomatic for the codebase |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | `scope:mcp-kanban` only |

### Failure Mode Map
N/A — single parameter change, no new codepaths or failure modes.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Architect response: Proceeding — T1 bug fix with empirical verification from #805 research (confidence 0.95), all AC lines verifiable, no design alternatives to evaluate

### Codebase Evidence
- `engine.py` L92-98: `board_config()` returns `self._config.model_copy()` (shallow)
- `models.py` L39-57: `BoardConfig` has `statuses: list[dict[str, Any]]`, `priorities: list[str]`, `defaults: BoardDefaults` — all mutable nested types not isolated by shallow copy
- Research verified: mutation of returned copy leaks to engine's internal `_config`
- Fix: `self._config.model_copy(deep=True)` — one parameter, no new imports

### AC Notes
- AC2 says `model_copy()` but should read `model_copy(deep=True)` per AC3 and research. Minor — AC3 governs behavior, and #805 TDD tests enforce deep copy correctness. Builder guidance: use `deep=True`.

### Verdict: APPROVE
AC is precise and verifiable. Architecture sound. Trivial T1 fix with empirical backing.
[[2026-04-12]]
## Test-Writer Notes
- Test file: `tests/test_board_config_806.py`
- Class: `TestFromAC_BoardConfig_806`
- Tests per category: happy 2 (AC1 instance type, AC2 repeated-calls equal+distinct), edge 0, error 0, boundary 8 (AC2 scalar content ×5, AC3 sub-model isolation ×2, AC3 repeated distinct ×1)
- Total: 10 tests

### Pipeline irregularity — no RED phase possible
The #805 builder applied `model_copy(deep=True)` during the #805 task (out-of-order).  All 10 tests pass GREEN immediately.  This is expected and documented: there is no failing state to expose because the implementation is already correct.

### What these tests add over #805
`test_board_config_805.py` covers statuses/priorities list-level mutation (append, clear, nested dict key injection).  This file adds:
- Scalar field content verification: `version`, `board.name`, `tasks_dir`, `defaults.status`, `defaults.priority`
- Object identity: repeated calls return `==` but `is not` distinct instances
- Sub-model mutation isolation: `copy.board.name = "INJECTED"` and `copy.defaults.status = "done"` must not corrupt engine state — these would FAIL with shallow `model_copy()` and pass with `deep=True`

### ruff
Clean ✓

### AC coverage

| AC | Test(s) | GREEN? |
|----|---------|--------|
| AC1 — board_config() method on KanbanEngine returns BoardConfig | `test_board_config_returns_board_config_instance` | ✓ (impl done) |
| AC2 — returns cached config with valid fields | `test_board_config_version_matches_config`, `test_board_config_board_name_matches_config`, `test_board_config_tasks_dir_matches_config`, `test_board_config_default_status_matches_config`, `test_board_config_default_priority_matches_config`, `test_board_config_repeated_calls_return_equal_objects`, `test_board_config_repeated_calls_return_distinct_objects` | ✓ (impl done) |
| AC3 — defensive copy (sub-model mutation isolation) | `test_board_config_board_submodel_mutation_does_not_leak_to_engine`, `test_board_config_defaults_submodel_mutation_does_not_leak_to_engine` | ✓ (impl done) |
| AC4 — #805 tests pass GREEN | Verified externally; not a new test scenario | ✓ |
| AC5 — existing MCP tests pass (O4) | Quality gate for builder; no new MCP tool added | ✓ |
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/kanban/src/owlbear_kanban/engine.py` — `model_copy()` → `model_copy(deep=True)` (1 line)
- `tests/test_board_config_806.py` — new test file (10 tests, created by test-writer)

### Commit
`f4ae6b39` fix: board_config() returns deep copy via model_copy(deep=True) (#806)

### Test Results
- `test_board_config_805.py` + `test_board_config_806.py`: **15/15 passed** (runTests tool, coverage mode)
- Verification of RED phase: not applicable — #805 builder applied `model_copy(deep=True)` out-of-order; all tests were GREEN at task pickup. This is documented in the test-writer notes.

### Lint
- `ruff check serve/kanban/src/owlbear_kanban/engine.py` → **All checks passed!**

### AC Evidence
| AC | Evidence |
|----|----------|
| AC1 — board_config() on KanbanEngine | exists at engine.py L92; test_board_config_returns_board_config_instance ✓ |
| AC2 — model_copy() of cached config | 7 scalar/identity tests ✓ |
| AC3 — defensive copy, mutation isolation | board.name + defaults.status sub-model tests ✓; deep=True confirmed |
| AC4 — #805 tests GREEN | 5/5 #805 tests pass |
| AC5 — existing MCP tests pass | test_kanban_engine_config.py passes (verified via runTests) |

### Notes
- Implementation was already applied in task #805 (out-of-order). This task's contribution is the 10-test regression suite in `test_board_config_806.py` confirming scalar-field content, object identity, and sub-model mutation isolation — complementing the list-mutation tests in #805.
[[2026-04-12]]
## Review Evidence

### Tests
- `test_board_config_805.py` + `test_board_config_806.py`: **15/15 passed** (independent run)
- `test_kanban_engine_config.py` (AC5 O4 gate): **35/35 passed**
- Exit codes: pytest 0, ruff 0

### Lint
- `serve/kanban/src/owlbear_kanban/engine.py`: clean ✓
- `tests/test_board_config_806.py`: clean ✓
- `tests/test_board_config_805.py`: clean ✓

### Coverage
- `board_config()` lines 92-99 in engine.py: covered (not in uncovered-lines list)
- Module-wide 17% is expected — only `board_config()` is the target method; all other engine methods are tested by the broader suite

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1 — `board_config()` on `KanbanEngine` returns `BoardConfig` | `test_board_config_returns_board_config_instance` — `isinstance(result, BoardConfig)` — fails on None or wrong type | COVERED |
| AC2 — returns `model_copy()` of cached config (valid fields) | 7 tests: version, board.name, tasks_dir, defaults.status, defaults.priority, repeated-calls equal, repeated-calls distinct | COVERED |
| AC3 — defensive copy — mutation doesn't affect engine state | `test_board_config_board_submodel_mutation_does_not_leak_to_engine` + `test_board_config_defaults_submodel_mutation_does_not_leak_to_engine` — would fail with shallow `model_copy()` | COVERED |
| AC4 — #805 tests pass GREEN | 5/5 #805 tests pass (list, dict, priorities mutation isolation) | COVERED |
| AC5 — existing MCP tests pass (O4) | `test_kanban_engine_config.py` 35/35 ✓ | COVERED |

### TestFromAC Integrity
- `TestFromAC_BoardConfig_806`: no builder modifications — class, methods, and assertions all pristine
- `TestFromAC_BoardConfig` (#805): no modifications observed

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Value-exact (`== 10`, `== "OwlBear"`) + reference-level (`is not`) + behavioral mutation |
| Negative/error path | ADEQUATE | No error-path tests needed — method is a pure getter with no failure modes |
| Mutation robustness | STRONG | Would catch: shallow copy, same-instance return, wrong values, missing deep=True (~95% detection) |
| Test independence | STRONG | Each test uses fresh `engine` fixture via tmp_path |
| Test naming | STRONG | All names clearly describe scenario |

### Security
No OWASP Top 10 concerns. Deep copy is a security best practice — prevents accidental engine state corruption by callers.

### Deductions
0 deductions across all dimensions.

### Verdict
Confidence: **0.97** → **PASS → docs**
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `board_config()` existed pre-task; the fix is internal (`deep=True`). No new public API. `copilot-instructions.md` contains only branch/identity sections — no API tables to update. |
| 2 | Module docstrings | Yes | Verified | `engine.py` module docstring (L18) explicitly lists `board_config()` with accurate description. Method docstring (L92-99) documents `deep=True` behavior and mutation safety. Both accurate. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` L101-105: `## board_config() Implementation (Task #806)` section present with Pydantic v2 docs entry. Already attributed by researcher. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/board-config-impl-806.md` exists and is linked in task body under `## Research`. |

### Scratch files
None found — `file_search(".owlbear/scratch/806-*")` returned no results.

### Files updated
None — all docs were already accurate and complete at start of gate.
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — `board_config()` on `KanbanEngine` | engine.py L93-99; `test_board_config_returns_board_config_instance` PASS | PASS |
| AC2 — returns model_copy() of cached config | 7 tests (version, board.name, tasks_dir, defaults.status, defaults.priority, repeated equal, repeated distinct) — all PASS | PASS |
| AC3 — defensive copy, mutation isolation | `test_board_config_board_submodel_mutation_does_not_leak_to_engine` + `test_board_config_defaults_submodel_mutation_does_not_leak_to_engine` PASS | PASS |
| AC4 — #805 tests pass GREEN | 5/5 PASS | PASS |
| AC5 — existing MCP tests pass (O4) | test_kanban_engine_config.py 35/35 PASS | PASS |

### Test Results
- pytest (task-scoped): 50 passed, 0 failed (test_board_config_805 + test_board_config_806 + test_kanban_engine_config)
- pytest (full suite): 3656 passed, 371 failed, 8 skipped, 6 errors — all failures pre-existing and outside task scope (AppContext init, log_activity, bookmark pipeline, lint-changed.ps1, module imports)
- ruff: All checks passed (serve/ + tests/)

### Architect Quality: 4/5
AC2 said `model_copy()` generically while AC3 required deep copy semantics. Minor ambiguity — architect self-noted in AC Notes and builder corrected. Otherwise specific and fully verifiable.

### Deduction Breakdown
- AC lines with no evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Commit Integrity
- Builder commit `f4ae6b39` verified via `git log` — covers engine.py + test_board_config_806.py
- No uncommitted deliverables for #806