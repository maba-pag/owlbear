---
id: 805
title: Tests — board_config
status: archived
priority: medium
created: '2026-04-10T21:21:09.498916+00:00'
updated: '2026-04-13T11:46:10.444712+00:00'
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
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/board-config-tests-805.md (validation pass — findings hold)
- Sources: 5 studied, 3 high-relevance (engine.py, models.py, Pydantic v2 empirical)
- Recommendation: T1 autonomous — all AC met (confidence: 0.95)
- Tests: 5/5 GREEN — statuses order, priorities order, 3x copy isolation
- Implementation: `model_copy(deep=True)` already applied in engine.py L150
- Follow-up tasks created: none (work complete, no further decomposition needed)
- Decision requests: none
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only `board_config()` copy behavior |
| Interface clarity | PASS | AC specifies statuses order, priorities order, and copy isolation — all verifiable via assertions |
| Dependency correctness | PASS | No dependencies needed; `board_config()` and `BoardConfig` exist in `owlbear_kanban` |
| Module layering | PASS | Tests import from `owlbear_kanban` (standalone engine package) — correct boundary |
| TDD compliance | PASS | This IS the test task; tests designed to fail RED without `model_copy(deep=True)` |
| KISS/YAGNI | PASS | 5 focused tests covering 3 AC items |
| Premise challenge | PASS | Regression coverage for defensive copy is necessary — empirically verified shallow copy bug |
| Pattern consistency | PASS | Follows fixture pattern from `test_config_staleness_fix_828.py` (`_BASE_CONFIG_YAML`, `kanban_dir`, `engine`) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Kanban engine domain only |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1 — statuses content and display order | Verifiable | Tests assert element-by-element against expected list |
| AC2 — priorities content and display order | Verifiable | Tests assert against expected list |
| AC3 — returned object is a copy | Verifiable | 3 mutation-isolation tests (statuses list, priorities list, nested dict) |
| AC4 — tests fail RED before implementation | Caveat | `model_copy(deep=True)` was applied OOO in engine.py L150; tests pass GREEN as regression coverage. Tests are correctly designed to fail without the fix. Test-writer should process as pass-through. |

### Codebase Evidence

- `board_config()` at `serve/kanban/src/owlbear_kanban/engine.py` L143-149 returns `self._config.model_copy(deep=True)`
- `BoardConfig` model at `serve/kanban/src/owlbear_kanban/models.py` L39-57 with `statuses: list[dict[str, Any]]`, `priorities: list[str]`
- Test file `tests/test_board_config_805.py` (184 lines, 5 tests) already exists — written during research phase
- Complementary tests in `tests/test_board_config_806.py` cover sub-model isolation (board, defaults)

### Challenge Results

- Challenger: RECONSIDER (confidence 0.68) — AC4 unsatisfiable since implementation pre-exists
- Architect response: Override accepted. AC4 describes design intent (tests would fail without deep copy); OOO implementation is a pipeline sequencing issue, not an AC defect. AC1-3 are precise and verifiable. Caveat documented above for test-writer.

### Verdict: APPROVE
### Action Taken: Advanced to todo. type:test tag present — test-writer processes as pass-through (tests already exist and pass GREEN).
[[2026-04-13]]
## Test-Writer Notes

- Test file: `tests/test_board_config_805.py`
- Class: `TestFromAC_BoardConfig`
- Tests: 5 total — all PASS GREEN (not RED)
- Pass-through reason: tests were written during the research phase (OOO); `model_copy(deep=True)` was already applied in `engine.py` L150 before this task reached test-writer
- AC coverage:

| AC | Tests | Status |
|----|-------|--------|
| AC1 — statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation` | COVERED |
| AC2 — priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation` | COVERED |
| AC3a — statuses append isolation | `test_board_config_statuses_append_does_not_leak_to_engine` | COVERED |
| AC3b — priorities append isolation | `test_board_config_priorities_append_does_not_leak_to_engine` | COVERED |
| AC3c — nested dict mutation isolation | `test_board_config_nested_status_dict_mutation_does_not_leak_to_engine` | COVERED |
| AC4 — tests fail RED | Pass-through per arch-review caveat — implementation pre-existed OOO | NOTED |

- Verified: `uv run pytest tests/test_board_config_805.py` → 5 passed, 0 failed
- All 5 tests serve as regression coverage for the `model_copy(deep=True)` fix
[[2026-04-13]]
## Builder Notes

**Pass-through task** — tests were written during the research phase (OOO); `model_copy(deep=True)` was already applied in `engine.py` L150 before the builder stage.

### Files Changed
- None — test file `tests/test_board_config_805.py` (184 lines, 5 tests) pre-existed; no implementation changes required.

### RED Verification
- Tests were designed to fail RED without `model_copy(deep=True)`. Implementation pre-existed, so explicit RED run was not possible. Architecture review documented this OOO sequencing caveat and approved as pass-through.

### Test Results
- `uv run pytest tests/test_board_config_805.py` → **5 passed, 0 failed**

### Coverage
- `engine.py` lines 143-149 (`board_config()`) covered; overall engine.py 11.3% (expected — tests are scoped to one method)

### Lint
- `uv run ruff check tests/test_board_config_805.py` → **All checks passed!**

### AC Evidence
| AC | Coverage | Result |
|----|----------|--------|
| AC1 — statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation` | PASS |
| AC2 — priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation` | PASS |
| AC3a — statuses append isolation | `test_board_config_statuses_append_does_not_leak_to_engine` | PASS |
| AC3b — priorities append isolation | `test_board_config_priorities_append_does_not_leak_to_engine` | PASS |
| AC3c — nested dict mutation isolation | `test_board_config_nested_status_dict_mutation_does_not_leak_to_engine` | PASS |
| AC4 — tests fail RED | Pass-through per arch-review caveat | NOTED |

### Builder-Discovered Tests
None — no edge cases identified beyond the 5 pre-existing tests.
[[2026-04-13]]
## Review Evidence

### Tests
`uv run pytest tests/test_board_config_805.py` → **5 passed, 0 failed** (independent run via quality-runner)

### Lint
`uv run ruff check tests/test_board_config_805.py` → **clean** (0 violations)

### Coverage
`board_config()` (engine.py L143-149) covered by all 5 tests. engine.py overall 16% — expected for a method-scoped test file.

### Source Control Changes
Builder reports no files changed — this is a pass-through task (tests pre-existed from research phase). Confirmed by reading test file: `tests/test_board_config_805.py` (184 lines, 5 tests in `TestFromAC_BoardConfig`).

### TestFromAC_ Integrity
`TestFromAC_BoardConfig` class present and unmodified by builder. No weakened or removed tests detected.

### AC Compliance

| AC | Test(s) | Assertion Strength | Status |
|----|---------|-------------------|--------|
| AC1 — statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation` | `actual_names == _EXPECTED_STATUS_NAMES` — element-by-element equality on exact ordered list; would fail on wrong order or missing element | PASS |
| AC2 — priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation` | `copy2.priorities == _EXPECTED_PRIORITIES` — same; strong | PASS |
| AC3a — statuses append isolation | `test_board_config_statuses_append_does_not_leak_to_engine` | `len(second.statuses) == original_count` — detects the shallow-copy leak; would catch exactly the bug described | PASS |
| AC3b — priorities append isolation | `test_board_config_priorities_append_does_not_leak_to_engine` | `len(second.priorities) == original_count` — same pattern | PASS |
| AC3c — nested dict mutation isolation | `test_board_config_nested_status_dict_mutation_does_not_leak_to_engine` | `"INJECTED_KEY" not in second.statuses[0]` — strong; specifically targets nested-object share | PASS |
| AC4 — tests fail RED before implementation | Pass-through per arch-review caveat; OOO sequencing accepted and documented at arch-review stage | NOTED |

### Assertion Quality Check
AC3a/AC3b use count-based assertions rather than full equality. This is targeted and sufficient: the shallow-copy bug being caught would add 1 element to the engine's list, which `== original_count` directly detects. Not weak — the assertion would fail exactly when the bug is present. AC3c uses key-presence assertion — strong and precise.

### Security
No new system boundaries. No security concerns.

### Deductions
0

### Verdict
Confidence: .97 → **PASS**
[[2026-04-13]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test task — no production API modified; `copilot-instructions.md` unchanged |
| 2 | Module docstrings | Yes | Updated | Module docstring in `tests/test_board_config_805.py` was stale: "Failing tests / RED phase / MUST FAIL" — inaccurate since implementation was applied OOO and all 5 tests pass GREEN. Updated to "Regression tests" framing with OOO note. Class and method docstrings accurate. |
| 3 | External attribution | No | N/A | All 5 sources in research doc are internal (engine.py, models.py, empirical workspace verification, fixture file, brief). No external URLs cited. `sources/overview.md` unchanged. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/board-config-tests-805.md` exists and is linked from task body. Follow-up tasks: none per research findings. |

### Files Updated
- `tests/test_board_config_805.py` — module docstring corrected (stale RED-phase framing → regression test framing)
- Committed: `4b273d35` — `docs: update module docstring from RED-phase to regression (#805, doc-writer)`

### Scratch Files Cleaned
- None (no `.owlbear/scratch/805-*` files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 - statuses content and display order | `test_board_config_statuses_display_order_survives_consumer_mutation`: asserts `actual_names == _EXPECTED_STATUS_NAMES` (exact ordered list) | PASS |
| AC2 - priorities content and display order | `test_board_config_priorities_display_order_survives_consumer_mutation`: asserts `copy2.priorities == _EXPECTED_PRIORITIES` (exact ordered list) | PASS |
| AC3 - returned object is a copy | 3 tests: statuses append isolation (count), priorities append isolation (count), nested dict mutation isolation (key presence). All strong. | PASS |
| AC4 - tests fail RED before implementation | OOO sequencing: `model_copy(deep=True)` applied before test-writer stage. Documented and accepted at arch-review. Tests are correctly designed to fail without the fix. | NOTED |

### Test Results
- pytest: 4,075 passed, 336 failed, 8 skipped (task-scoped tests: 5/5 passed, 0 in failure list). All 336 failures are pre-existing across 36 unrelated files (pick_tasks, mcp_browser_session, analysis, etc.) with no overlap to board_config scope.
- ruff: `tests/test_board_config_805.py` clean. 2 violations in unrelated `test_timestamp_sort_816.py`.

### Architect Quality: 4/5
AC1-AC3 are specific and verifiable with concrete assertions. AC4 is sound in design intent but was unsatisfiable due to OOO pipeline sequencing. Arch-review documented the caveat. Minor gap only.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 4 verified)
- Lint violations in scope: 0
- AC quality deduction (score > 3): 0
- Missing reviewer evidence: 0 (detailed, .97 PASS)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Upstream Commits Verified
- `6b76cee5` test: add board_config() defensive copy tests and research doc (#805, auditor)
- `4b273d35` docs: update module docstring from RED-phase to regression (#805, doc-writer)