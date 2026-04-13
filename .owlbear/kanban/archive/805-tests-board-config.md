---
id: 805
title: Tests — board_config
status: done
priority: needed
created: '2026-04-10T21:21:09.498916+00:00'
updated: '2026-04-12T04:43:04.875457+00:00'
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

- Tests verify `board_config()` returns config with valid statuses and display order
- Tests verify `board_config()` returns config with valid priorities and display order
- Tests verify returned object is a copy (mutation doesn't affect engine internal state)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/board-config-tests-805.md
- Sources: 5 studied, 3 high-relevance (all internal)
- Recommendation: Write 5 tests; 3 will be RED due to shallow `model_copy()` defect (confidence: 0.95)
- Follow-up tasks created: none needed — task #805 itself is the test-writing vehicle
- Decision requests: none

## Key Findings

1. `board_config()` uses `model_copy()` (shallow) — nested lists/dicts share references with engine's internal `_config`. Empirically verified: appending to returned `priorities` corrupts engine state.
2. AC1-AC2 tests (statuses/priorities content and order) will pass GREEN immediately.
3. AC3 tests (defensive copy) will fail RED — the shallow copy doesn't prevent mutation leakage. Fix is `model_copy(deep=True)`.
4. Existing fixture pattern from `test_config_staleness_fix_828.py` should be reused.

## Challenge Results
- Challenger: FALLBACK — trivial T1 finding with empirical verification
- Confidence in original: 0.95
- Tier: T1 — bug fix (shallow copy → deep copy)
[[2026-04-11]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single method (`board_config()`) under test |
| Interface clarity | PASS | AC lines map directly to testable assertions: content+order, mutation isolation |
| Dependency correctness | PASS | `depends_on: []` — method exists, no deps needed |
| Module layering | PASS | `tests/` → `owlbear_kanban` — correct direction |
| TDD compliance | PASS | This IS the test task; AC4 requires RED |
| KISS/YAGNI | PASS | 5 tests for 3 AC lines, no speculative coverage |
| Premise challenge | PASS | Research empirically verified shallow-copy defect; tests expose real bug |
| Pattern consistency | PASS | Reuses `test_config_staleness_fix_828.py` fixture pattern |
| Security surface | N/A | Test-only, no new system boundaries |
| Single domain | PASS | `scope:mcp-kanban` only |

### Failure Mode Map
N/A — test-only task, no codepath changes.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Architect response: Proceeding — T1 test task with empirically verified research (confidence 0.95), all AC lines verifiable

### Codebase Evidence
- `engine.py` L92-98: `board_config()` returns `self._config.model_copy()` (shallow)
- `models.py` L39-57: `BoardConfig.statuses` is `list[dict[str, Any]]` — shallow copy shares nested refs
- `test_config_staleness_fix_828.py`: fixture pattern (`_BASE_CONFIG_YAML`, `kanban_dir`, `engine`) available for reuse
- Research doc empirically verified: `copy.statuses is original.statuses` → `True` with shallow copy

### Non-impl tagging
Already tagged `type:test` — pass-through tag present.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. Test-writer can derive 5 tests mechanically from AC + research findings.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_board_config_805.py
- Classes: `TestFromAC_BoardConfig`
- Tests per category: happy 0, edge 2 (AC1/AC2 — content+order via consumer-mutation probe), error 0, boundary 3 (AC3a/AC3b/AC3c — append + nested dict mutation)
- Total: 5 tests, all FAIL ✓
- ruff: clean ✓

### AC coverage

| AC | Test(s) | RED? |
|----|---------|------|
| AC1 — statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation` | FAIL ✓ |
| AC2 — priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation` | FAIL ✓ |
| AC3 — returned object is a copy | `test_board_config_statuses_append_does_not_leak_to_engine`<br>`test_board_config_priorities_append_does_not_leak_to_engine`<br>`test_board_config_nested_status_dict_mutation_does_not_leak_to_engine` | FAIL ✓ |
| AC4 — tests fail RED | All 5 fail | ✓ |

### Design notes
- AC1/AC2 tests are designed RED: they prove the "order survives" guarantee by calling `board_config()` a second time after a consumer clears a prior copy's list. With shallow `model_copy()`, the clear propagates into engine state, so the second call returns `[]`. Fix: `model_copy(deep=True)`.
- AC3 tests cover three mutation shapes: append to top-level list (statuses, priorities), and mutate a nested dict (statuses[0]).
- Root cause confirmed empirically: `model_copy()` (shallow) shares list/dict references. Fix is one character: `model_copy()` → `model_copy(deep=True)` at engine.py L98.
- Fixture reused from `test_config_staleness_fix_828.py`: `_BASE_CONFIG_YAML`, `kanban_dir`, `engine`.
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/kanban/src/owlbear_kanban/engine.py` — L98: `model_copy()` → `model_copy(deep=True)`

### Implementation
Single-character fix. `model_copy()` (Pydantic shallow copy) shares nested list/dict references with engine's internal `_config`. Changed to `model_copy(deep=True)` so all returned `BoardConfig` objects are fully isolated from engine state.

### Test Results
- 5 `TestFromAC_BoardConfig` tests: **5 passed** (all 5 were RED before fix)
- No `TestBuilderDiscovered` tests needed — all edge cases (append, clear, nested dict mutation) already covered by test-writer

### Lint
- ruff: **clean** on `engine.py`

### Coverage
- `owlbear_kanban.engine` module: 17% — expected. These 5 tests target only `board_config()` out of 243 statements. The changed line is fully exercised.

### Evidence
- RED verification: 5 FAIL (assertion errors showing list mutation leakage)
- GREEN verification: 5 PASS
- Diff: 1 file, 1 line changed
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest: **5 passed, 0 failed** (exit 0)
- Ran independently via quality-runner — builder self-report not trusted

### Lint
- ruff: **clean** on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_board_config_805.py` (exit 0)

### Coverage
- `owlbear_kanban.engine`: 17% — expected. 5 tests cover only `board_config()` out of 243 statements; the changed line (L98) is fully exercised.

### AC Compliance

| AC Line | Test(s) | Evidence | Status |
|---------|---------|----------|--------|
| AC1 — statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation` | Clears copy1.statuses; asserts copy2 returns full 7-item ordered list. Would fail with shallow copy. | PASS |
| AC2 — priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation` | Clears copy1.priorities; asserts copy2 returns full 5-item ordered list. Would fail with shallow copy. | PASS |
| AC3 — returned object is a copy | `test_board_config_statuses_append_does_not_leak_to_engine`, `test_board_config_priorities_append_does_not_leak_to_engine`, `test_board_config_nested_status_dict_mutation_does_not_leak_to_engine` | Three mutation vectors: append to statuses, append to priorities, mutate nested dict. All proved isolation. AC3c (nested dict) is the deepest proof — requires `deep=True`. | PASS |
| AC4 — tests fail RED before implementation | Test-writer confirmed all 5 RED; code-reader verified each test would fail with `model_copy()` shallow | Assertions are specific enough that reverting `deep=True` would cause failures on all 5. | PASS |

### Test Integrity
- No `TestFromAC_*` tests removed, weakened, or replaced by builder.
- All 5 original RED-phase tests intact and unchanged.
- Builder added 0 new tests — none needed (test-writer covered all mutation vectors).

### Implementation Review
- `engine.py` L98: `self._config.model_copy(deep=True)` — standard Pydantic v2 deep copy idiom.
- Change scope: 1 parameter added (`deep=True`). No API changes, no new imports, no restructuring.
- Security: no concerns. Public method, on-demand copy, no access control surface.

### Deductions
- 0 deductions.

### Verdict
- Confidence: **.97** → **PASS**
- Action: Advance to docs.
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `board_config()` signature unchanged; copy-depth is an implementation detail. `.github/copilot-instructions.md` has no reference to `KanbanEngine` or `board_config` — no update needed. |
| 2 | Module docstrings | Yes | Updated | `engine.py` `board_config()` docstring said `model_copy()` but code uses `model_copy(deep=True)`. Updated prose to "deep `model_copy(deep=True)`" and added "including nested lists and dicts". Commit `7ce1edac`. |
| 3 | External attribution | No | N/A | All research sources were internal (engine.py, models.py, test fixture, Pydantic empirical test, brief). No external articles or repos cited. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/board-config-tests-805.md` exists and is linked in task body. Follow-up tasks noted as "none needed" — task #805 itself was the test vehicle; the fix was bundled. |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — docstring on `board_config()` (commit `7ce1edac`)

### Scratch Files Cleaned
- None (no `.owlbear/scratch/805-*` files found)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: statuses content and display order | test_board_config_statuses_display_order_survives_consumer_mutation PASS | PASS |
| AC2: priorities content and display order | test_board_config_priorities_display_order_survives_consumer_mutation PASS | PASS |
| AC3: returned object is a copy | 3 tests PASS: statuses append, priorities append, nested dict mutation | PASS |
| AC4: tests fail RED before implementation | Test-writer confirmed 5 RED; reviewer verified assertions require deep=True | PASS |

### Test Results
- pytest (full suite): 3656 passed, 352 failed, 6 errors. All 352 failures and 6 errors are pre-existing and unrelated to task scope (AppContext signature changes, missing lint-changed.ps1, knowledge integration issues, etc.). All 5 task-scoped tests PASS.
- ruff: clean on task files (engine.py, test_board_config_805.py). 2 violations in unrelated test_valid_transitions_807.py.

### Architect Quality: 5/5
AC lines are specific, directly testable, and complete. Three mutation vectors cover the defect surface thoroughly. Research empirically verified the shallow-copy defect before tests were written. No builder improvisation needed.

### Deduction Breakdown
- 0 deductions. All 4 AC lines have specific test evidence. Reviewer evidence present and detailed (.97 PASS). Lint clean on task scope. No task-scope failures.

### Confidence: 1.00
### Action: archive

### Notes
- Test file (test_board_config_805.py) and research doc (board-config-tests-805.md) were both untracked/uncommitted by upstream agents. Committed as leftovers in 6b76cee5.

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6b76cee5 | test | tests/test_board_config_805.py, .owlbear/research/board-config-tests-805.md | #805 |