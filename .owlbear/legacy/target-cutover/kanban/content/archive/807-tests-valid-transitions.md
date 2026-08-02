---
id: 807
title: Tests — valid_transitions
status: archived
priority: medium
created: '2026-04-10T21:21:18.809894+00:00'
updated: '2026-04-13T12:30:39.113310+00:00'
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

- Tests verify `valid_transitions(status)` returns set of all configured statuses except the given one
- Tests verify invalid status input raises `ValueError`
- Tests verify transitions match config-defined statuses
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/valid-transitions-tests-807.md (validation pass — doc already existed)
- Sources: 4 studied, 4 high-relevance
- Validation: Implementation at engine.py L162–180 (moved from L113 since doc was written; behavior unchanged). All 25 tests in test_valid_transitions_807.py pass GREEN (confirmed GREEN-on-arrival as expected).
- Recommendation: Option A accepted — tests verify correctness despite GREEN-on-arrival (confidence: 0.90)
- Follow-up tasks created: none (paired task #808 already exists)
- Decision requests: none (T1 — standard test task)
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only `valid_transitions()` on `KanbanEngine` |
| Interface clarity | PASS | AC specifies return type (set), error behavior (ValueError), config-driven verification |
| Dependency correctness | PASS | No dependencies listed; Phase 1 independent pair confirmed |
| Module layering | PASS | Tests import only `KanbanEngine` from `owlbear_kanban`; no upward imports |
| TDD compliance | PASS | This IS the RED-phase test task; paired with #808 (GREEN) |
| KISS/YAGNI | PASS | 25 focused tests, no overengineering |
| Premise challenge | PASS | Tests verify essential engine behavior for GUI-ready data contract (O5) |
| Pattern consistency | PASS | Follows `_BASE_CONFIG_YAML`/`kanban_dir`/`engine` fixture pattern from test_refresh_config_803.py |
| Security surface | N/A | Pure test task |
| Single domain | PASS | `scope:mcp-kanban` only |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: returns set except given | Verifiable — parametrized tests cover all 7 statuses, type check, exclusion check | None |
| AC2: invalid raises ValueError | Verifiable — unknown, empty, case-mismatch all tested with `pytest.raises(ValueError)` | None |
| AC3: transitions match config | Verifiable — custom 2-status config proves config-driven behavior, no hardcoding | None |
| AC4: tests fail RED | Not satisfiable as written — implementation predates tests (GREEN-on-arrival) | Noted; research doc Option A accepted, docstring documents it; standard pipeline handling |

### Codebase Evidence

- Implementation: `serve/kanban/src/owlbear_kanban/engine.py` L162-180
- Test file: `tests/test_valid_transitions_807.py` (231 lines, 25 tests, all GREEN)
- Paired task: #808 (GREEN implementation) — no test duplication
- Import: `from owlbear_kanban import KanbanEngine` — correct package

### Challenge Results

- Challenger: FALLBACK — challenger agent not available
- Architect response: Proceeded with approval; no architectural risk (pure test task, well-researched, tests exist and pass)

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable (AC4 GREEN-on-arrival documented per pipeline convention). Tests follow established patterns. `type:test` pass-through tag present.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_valid_transitions_807.py
- Classes: `TestFromAC_ValidTransitions`
- Tests per category: happy 4 (parametrized ×7 each = 14 runs), edge 2, error 4, boundary 5
- Total: 25 tests
- ruff: clean
- Commit: a0302e7f (committed by builder — pre-existing on arrival)

**GREEN-on-arrival (pre-approved):** Implementation existed at engine.py L162–180 before this test task. All 25 tests pass. Architecture review explicitly accepted Option A — tests verify correctness of the existing contract. AC4 ("tests fail RED") is the only AC not satisfiable; documented in task body and research doc. `type:test` pass-through tag present.

**AC Coverage:**
| AC | Tests | Status |
|----|-------|--------|
| AC1: returns set except given | test_returns_all_statuses_except_given ×7, test_given_status_excluded ×7, test_return_type_is_set, test_hyphenated_status | COVERED |
| AC2: invalid raises ValueError | test_unknown_status_raises_value_error, test_empty_string, test_case_mismatch, test_value_error_message_names_invalid | COVERED |
| AC3: config-driven transitions | test_custom_config_two_statuses, test_custom_config_subset, test_custom_config_excludes_defaults, test_result_count_custom, test_result_count_default | COVERED |
| AC4: tests fail RED | Not satisfiable — GREEN-on-arrival, pre-approved by arch review | WAIVED |
[[2026-04-13]]
## Builder Notes
- Task type: `type:test` — GREEN-on-arrival pass-through (pre-approved by arch review)
- Files changed: none — implementation and tests pre-existed
- Test results: 25 passed, 0 failed (`tests/test_valid_transitions_807.py`)
- Lint: ruff clean
- Coverage: N/A (no new implementation code)
- Evidence: All TestFromAC_ValidTransitions tests pass against existing `valid_transitions()` at engine.py L162–180
- AC4 ("tests fail RED") waived — GREEN-on-arrival, explicitly pre-approved by architecture review
[[2026-04-13]]
## Review Evidence

### Test Results
pytest: **25 passed, 0 failed** (`tests/test_valid_transitions_807.py`) — run independently via quality-runner.

### Lint
ruff: **clean** — no violations.

### Coverage
`owlbear_kanban.engine`: 17% overall (expected — only `valid_transitions()` is in scope; all branches of the target function are exercised by the tests).

### AC Compliance Table

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| AC1: returns set of all configured statuses except the given one | `engine.py L180`: `return valid_statuses - {status}`; `test_returns_all_statuses_except_given` ×7 asserts exact set equality; `test_return_type_is_set` asserts `isinstance(result, set)` | test_returns_all_statuses_except_given, test_given_status_excluded_from_result, test_return_type_is_set, test_hyphenated_status_returns_correct_set | PASS |
| AC2: invalid status raises ValueError | `engine.py L177–178`: `if status not in valid_statuses: raise ValueError(msg)` with message `"Invalid status {status!r}. Valid options: …"` | test_unknown_status_raises_value_error, test_empty_string_raises_value_error, test_case_mismatch_raises_value_error, test_value_error_message_names_invalid_status | PASS |
| AC3: transitions match config-defined statuses | `engine.py L176`: `{s["name"] for s in self._config.statuses}` — custom 2-status config fixture proves no hardcoding; `test_custom_config_two_statuses_returns_one` asserts `== {"closed"}` | test_custom_config_*, test_result_count_* | PASS |
| AC4: tests fail RED before implementation | GREEN-on-arrival — implementation pre-existed. Pre-approved by arch review; `type:test` pass-through tag present. | N/A | WAIVED |

### TestFromAC Audit (Step 5.0/5.2)

Builder reports "Files changed: none." Test class `TestFromAC_ValidTransitions` is the test-writer's original intact. No comparison needed; nothing was modified.

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | test_returns_all_statuses_except_given (set equality) | Yes — wrong members fail exact `==` | COVERED |
| AC1 | test_return_type_is_set | Yes — list/tuple fails `isinstance(…, set)` | COVERED |
| AC2 | test_unknown_status_raises_value_error, test_empty_string, test_case_mismatch | Yes — no ValueError = fail | COVERED |
| AC2 | test_value_error_message_names_invalid_status (match="Invalid status") | Yes — wrong message fails `match=` | COVERED |
| AC3 | test_custom_config_two_statuses_returns_one (exact set equality) | Yes — hardcoded defaults would break this | COVERED |

### Test Quality (Step 5.3)
- **Assertion specificity** — STRONG: all assertions use exact set equality, `isinstance`, disjointness, or `pytest.raises(match=…)`. No lazy `assert result` patterns.
- **Error-path coverage** — STRONG: 4 tests for invalid inputs (unknown, empty, case-mismatch, message format).
- **Mutation resistance** — STRONG: self-exclusion removal caught by `test_given_status_excluded_from_result`; return type change caught by `test_return_type_is_set`; hardcoded values caught by custom-config tests.
- **Test independence** — STRONG: each test uses isolated `tmp_path`-based fixtures; no shared mutable state.
- **Descriptive names** — STRONG: all test names clearly describe the contract being verified.

### Security Review (Step 5.1)
No new code added. `valid_transitions()` reads from config (no user-controlled persistence), validates input and raises on invalid, no I/O or injection vectors. Clean.

### Builder Process Quality (Step 5.7)
One `## Builder Notes` section. CLEAN.

### Deductions
None.

### Confidence
.96 → PASS

### Verdict: PASS #807 → docs | confidence .96
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` task; Builder reports "Files changed: none" — no application code modified |
| 2 | Module docstrings | No | N/A | No implementation modules created or modified; test file has module-level docstring and `TestFromAC_ValidTransitions` class docstring — both accurate |
| 3 | External attribution | No | N/A | All 4 research sources are internal workspace files (engine.py, models.py, test_refresh_config_803.py, brief.md); no external repos or articles |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/valid-transitions-tests-807.md` exists; linked in task body under `## Research` |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/807-*` files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: returns set of all configured statuses except the given one | `test_returns_all_statuses_except_given` ×7, `test_given_status_excluded` ×7, `test_return_type_is_set`, `test_hyphenated_status` — all PASS; impl at engine.py L163–180 | PASS |
| AC2: invalid status input raises ValueError | `test_unknown_status_raises_value_error`, `test_empty_string`, `test_case_mismatch`, `test_value_error_message_names_invalid_status` — all PASS; engine.py L177–178 | PASS |
| AC3: transitions match config-defined statuses | `test_custom_config_two_statuses`, `test_custom_config_subset`, `test_custom_config_excludes_defaults`, `test_result_count_*` — all PASS; custom config fixtures prove no hardcoding | PASS |
| AC4: tests fail RED before implementation | WAIVED — GREEN-on-arrival; documented in research doc, arch review (Option A accepted), test-writer notes, builder notes, reviewer evidence. Full pipeline chain acknowledges unsatisfiability. | WAIVED |

### Test Results
- pytest (task scope): 25 passed, 0 failed
- pytest (full suite): 4083 passed, 335 failed, 8 skipped — 0 failures in task scope, no `valid_transitions` in any failure trace
- ruff: clean (serve/ tests/)

### Architect Quality: 4/5
AC1–3 are specific, verifiable, and led to clean implementation. AC4 ("tests fail RED") was structurally unsatisfiable since implementation predated the test task — architect should have written this AC with awareness of GREEN-on-arrival. Pipeline handled the gap correctly (research → arch review → waiver chain), but the AC itself was flawed.

### Deduction Breakdown
- AC lines with no specific evidence: AC4 waived with full documentation chain — .02 deduction (waiver is evidence but not verification)
- Lint violations: none
- AC quality ≤ 3: no (4/5)
- Missing reviewer evidence: no (present, detailed, .96 PASS)
- Full-suite failures in task scope: none

### Confidence: .98
### Action: archive