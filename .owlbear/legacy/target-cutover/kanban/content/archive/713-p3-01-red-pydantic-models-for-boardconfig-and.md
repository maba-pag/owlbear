---
id: 713
title: 'P3-01: RED — Pydantic models for BoardConfig and TaskRecord'
status: archived
priority: medium
created: 2026-04-09T03:24:26.6974428+02:00
updated: 2026-04-09T06:32:07.968443+02:00
started: 2026-04-09T06:32:07.968443+02:00
completed: 2026-04-09T06:32:07.968443+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
class: standard
---

## Objective
Write failing tests for internal Pydantic models: `BoardConfig` (config.yml schema) and `TaskRecord` (task file schema with all frontmatter fields).

Brief: see parent #712 and `.owlbear/briefs/draft-kanban-native/brief.md`

## AC
- [ ] Tests for BoardConfig covering: statuses list (list of dicts with `name` key), priorities list, defaults, next_id, claim_timeout, unknown-field preservation
- [ ] Tests for TaskRecord covering: all frontmatter fields (id, title, status, priority, created, updated, tags, parent, depends_on, blocked, block_reason, claimed_by, claimed_at), markdown body, unknown-field round-trip
- [ ] Tests validate ISO 8601 timestamp strings (not datetime objects — avoids Go nanosecond precision drift)
- [ ] All tests fail (no implementation yet)

## Files
- `tests/test_kanban_engine_models.py` (new)

[[2026-04-09]] Thu 03:41
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| BoardConfig tests (statuses, priorities, defaults, next_id, claim_timeout, unknown-field) | PARTIAL — missing version, board.name, tasks_dir, tui | REFINED below |
| TaskRecord tests (all frontmatter fields + body + unknown round-trip) | PASS — explicitly names all fields | None |
| ISO 8601 timestamp strings (not datetime) | PASS — clear testable condition | None |
| All tests fail (no implementation) | PASS — standard RED | None |

### AC Refinement (binding for test-writer)

AC line 1 must be read as: "Tests for BoardConfig covering: **version (int), board name (string), tasks_dir (string),** statuses list (list of dicts with `name` key), priorities list, defaults **(status, priority, class — class preserved)**, next_id, claim_timeout (duration string), **tui section preserved via extra-fields**, unknown-field preservation." These fields are all present in config.yml and listed in GREEN #714 AC.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two cohesive models for the same engine data layer |
| Interface clarity | PASS (with refinement) | All config.yml and task file fields now covered |
| Dependency correctness | PASS | No deps; first task in P3 chain |
| Module layering | PASS | Tests in root `tests/`, models in `owlbear_mcp_kanban` package |
| TDD compliance | PASS | This IS the RED phase; GREEN #714 depends on this |
| KISS/YAGNI | PASS | Models and tests only, minimal scope |
| Premise challenge | PASS | Engine-internal models needed; existing KanbanTask is MCP boundary, not engine internal |
| Pattern consistency | PASS | Follows existing Pydantic ConfigDict patterns in models.py |
| Security surface | N/A | Test-only task |
| Single domain | PASS | Kanban engine domain only |

### Architecture Notes

1. **Model distinction**: BoardConfig/TaskRecord are engine-internal models in `engine_models.py`, separate from MCP boundary `KanbanTask` in `models.py`. Correct separation.
2. **Timestamp strategy**: ISO 8601 strings avoid Go nanosecond → Python microsecond drift. Tests should assert `isinstance(field, str)` for all timestamp fields.
3. **Unknown-field preservation**: Tests must verify fields like `class`, `started`, `completed` survive round-trip. Pydantic `extra='allow'` is the GREEN-phase mechanism.
4. **Import path**: `from owlbear_mcp_kanban.engine_models import BoardConfig, TaskRecord` — will ImportError in RED phase as expected.

### Challenge Results
- Challenger: FALLBACK — agent not available in current tool set
- Architect response: independent evaluation conducted; no concerns requiring challenge

### Verdict: APPROVE
### Action Taken: Refined BoardConfig AC to include all config.yml fields. Approved to todo with `type:test` pass-through tag already present.

[[2026-04-09]] Thu 04:56
## Test-Writer Notes
- Test file: tests/test_kanban_engine_models.py
- Classes: `TestFromAC_BoardConfig`, `TestFromAC_TaskRecord`
- Tests per category:
  - **BoardConfig** — happy: 5, edge/boundary: 4, unknown-field: 3, error: 2 = 14 tests
  - **TaskRecord** — happy: 5, defaults: 7, ISO-8601 boundary: 4, unknown-field: 3, error: 4 = 23 tests
- Total: 37 tests, all FAIL (`ModuleNotFoundError: No module named 'owlbear_mcp_kanban.engine_models'`)
- ruff: clean
- Commit: `2de7c8c` on `dev`

### AC Coverage

| AC Line | Tests |
|---------|-------|
| BoardConfig: version (int) | `test_version_is_int` |
| BoardConfig: board name (string) | `test_board_name_is_str` |
| BoardConfig: tasks_dir (string) | `test_tasks_dir_is_str` |
| BoardConfig: statuses (list of dicts with `name` key) | `test_statuses_is_list_of_dicts_with_name_key` |
| BoardConfig: priorities list | `test_priorities_is_list_of_strings` |
| BoardConfig: defaults (status, priority, class preserved) | `test_defaults_status_accessible`, `test_defaults_priority_accessible`, `test_defaults_class_preserved_via_extra_fields` |
| BoardConfig: next_id | `test_next_id_is_int` |
| BoardConfig: claim_timeout (duration string) | `test_claim_timeout_is_str` |
| BoardConfig: tui preserved via extra-fields | `test_tui_section_preserved_in_dump` |
| BoardConfig: unknown-field preservation | `test_unknown_top_level_field_preserved` |
| BoardConfig: error paths | `test_missing_version_raises_validation_error`, `test_missing_statuses_raises_validation_error` |
| TaskRecord: all frontmatter fields | `test_all_required_frontmatter_fields_accessible`, `test_tags_populated_from_data`, `test_parent_stored_as_int`, `test_depends_on_is_list_of_ints`, `test_blocked_stored_as_bool`, `test_claimed_by_stored_as_str` |
| TaskRecord: all optional field defaults | `test_tags_default_to_empty_list`, `test_depends_on_defaults_to_empty_list`, `test_parent_defaults_to_none`, `test_blocked_defaults_to_false`, `test_block_reason_defaults_to_none`, `test_claimed_by_defaults_to_none`, `test_claimed_at_defaults_to_none` |
| TaskRecord: markdown body | `test_body_stored_as_str`, `test_empty_body_accepted` |
| TaskRecord: unknown-field round-trip | `test_class_field_preserved_in_round_trip`, `test_started_field_preserved_in_round_trip`, `test_completed_field_preserved_in_round_trip` |
| ISO 8601 timestamps as strings | `test_created_is_str_not_datetime`, `test_updated_is_str_not_datetime`, `test_claimed_at_is_str_not_datetime`, `test_go_nanosecond_precision_preserved_verbatim` |
| All tests fail | Confirmed — `ModuleNotFoundError` at collection; exit code 1 |

[[2026-04-09]] Thu 05:14
## Builder Notes

### Files Changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (new, 86 lines)

### Implementation
Created four Pydantic models with `extra="allow"` for unknown-field preservation:
- `BoardInfo` — sub-model for `board.name`
- `BoardDefaults` — sub-model for `defaults` section; preserves `class` and other extras
- `BoardConfig` — full config.yml schema; preserves `tui`, vendor fields
- `TaskRecord` — task frontmatter + body; timestamps as `str`, preserves `class`/`started`/`completed`

### Test Results
- **44 passed**, 0 failed (test-writer count of 37 was conservative; file has 44 tests total)
- `TestFromAC_BoardConfig`: 16 tests ✓
- `TestFromAC_TaskRecord`: 28 tests ✓
- No `TestBuilderDiscovered` tests needed — AC tests covered all discovered edges

### Coverage
- `engine_models.py`: **100%** (36/36 statements)

### Lint
- ruff: **clean**

### Commit
- `a5106b7` on `dev`

[[2026-04-09]] Thu 05:46
## Review Evidence

### Test Results
pytest: **44 passed, 0 failed**, 0 skipped — quality-runner confirmed.

### Lint
ruff: **clean** — both `engine_models.py` and `test_kanban_engine_models.py`.

### Coverage
`owlbear_mcp_kanban.engine_models`: **100%** (36/36 statements).

---

### Step 1 — Changed Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (new, 86 lines) — commit `a5106b7`
- `tests/test_kanban_engine_models.py` (new, 386 lines, written by test-writer at `2de7c8c`)

No existing function/class signatures changed; no downstream callers impacted.

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| BoardConfig: version (int), board.name, tasks_dir, statuses, priorities, defaults, next_id, claim_timeout, tui via extra-fields, unknown-field preservation | `TestFromAC_BoardConfig` (16 tests): `test_version_is_int`, `test_board_name_is_str`, `test_tasks_dir_is_str`, `test_statuses_is_list_of_dicts_with_name_key`, `test_priorities_is_list_of_strings`, `test_defaults_*` (×3), `test_next_id_is_int`, `test_claim_timeout_is_str`, `test_tui_section_preserved_in_dump`, `test_unknown_top_level_field_preserved`, error tests (×2) — all pass | PASS |
| TaskRecord: all frontmatter fields, markdown body, unknown-field round-trip | `TestFromAC_TaskRecord` (28 tests): all fields verified with type checks + value equality + defaults + error paths + round-trip for `class`, `started`, `completed` | PASS |
| ISO 8601 timestamps as strings (not datetime) | `test_created_is_str_not_datetime`, `test_updated_is_str_not_datetime`, `test_claimed_at_is_str_not_datetime`, `test_go_nanosecond_precision_preserved_verbatim` (7-digit Go timestamp exact equality) | PASS |
| All tests fail (no implementation yet) | Test-writer commit `2de7c8c` confirmed `ModuleNotFoundError` — RED phase correctly established. Builder `a5106b7` added `engine_models.py`, tests now pass. | PASS |

---

### Pass 1: Critical Checks

#### 5.0 Test-Writer Audit — AC-to-Test Coverage

| AC Line | Mapped Test(s) | Would Fail If Violated? | Verdict |
|---------|---------------|------------------------|---------|
| BoardConfig.version (int) | `test_version_is_int` — `isinstance` + value `== 10` | YES | COVERED |
| BoardConfig.board.name (str) | `test_board_name_is_str` — `isinstance` + `== "OwlBear"` | YES | COVERED |
| BoardConfig.tasks_dir (str) | `test_tasks_dir_is_str` — `isinstance` + `== "tasks"` | YES | COVERED |
| BoardConfig.statuses (list[dict] w/ name key) | `test_statuses_is_list_of_dicts_with_name_key` — `isinstance(list)` + per-item assertion | CONDITIONAL (see 5.3 note) | COVERED / LAX |
| BoardConfig.priorities (list[str]) | `test_priorities_is_list_of_strings` — `all(isinstance(p, str)...)` | YES | COVERED |
| BoardConfig.defaults.status, .priority, .class | `test_defaults_status_accessible`, `test_defaults_priority_accessible`, `test_defaults_class_preserved_via_extra_fields` | YES | COVERED |
| BoardConfig.next_id (int) | `test_next_id_is_int` — value check | YES | COVERED |
| BoardConfig.claim_timeout (str) | `test_claim_timeout_is_str` — `isinstance` + value | YES | COVERED |
| BoardConfig.tui via extra-fields | `test_tui_section_preserved_in_dump` — nested values checked | YES | COVERED |
| BoardConfig unknown-field preservation | `test_unknown_top_level_field_preserved` — round-trip equality | YES | COVERED |
| TaskRecord all frontmatter fields | Field-specific tests with `isinstance` + equality for all 13 declared fields | YES for each | COVERED |
| TaskRecord markdown body | `test_body_stored_as_str` + `test_empty_body_accepted` | YES | COVERED |
| TaskRecord unknown-field round-trip | `test_class_field_preserved_in_round_trip`, `test_started_*`, `test_completed_*` | YES | COVERED |
| ISO 8601 as str, Go nanosecond verbatim | 4 timestamp tests; verbatim equality on `"2026-04-09T03:24:26.6974428+02:00"` | YES | COVERED |

No MISSING AC lines.

#### 5.1 Security Review
No hardcoded secrets, no injection surface, no path traversal. `extra="allow"` on engine-internal models reading from local files — not a data boundary concern. CLEAN.

#### 5.2 TestFromAC Integrity
Builder only added `engine_models.py`. The test file at `tests/test_kanban_engine_models.py` is unchanged from test-writer's commit (`2de7c8c`). No TestFromAC_* methods modified, weakened, or removed. CLEAN.

#### 5.3 Test Quality

**LAX (informational, compensated):** 4 smoke-test methods contain `assert config is not None` / `assert task is not None`:
- `test_full_config_parses_without_error` (line 107)
- `test_minimal_config_parses_without_error` (line 113)
- `test_full_task_parses_without_error` (line 224)
- `test_minimal_task_parses_without_error` (line 229)

These are "no-exception" smoke tests. All structural/type/value assertions are covered by the 40 companion tests. Compensated — no deduction escalation.

**LAX (informational):** `test_statuses_is_list_of_dicts_with_name_key` (line 139) uses `assert "name" in status or hasattr(status, "name")`. The `hasattr` branch is superfluous since dicts don't carry named attributes; however the assertion is functionally correct as Pydantic enforces `list[dict[str, Any]]`. Not a defect.

No WEAK ratings on any dimension. Independence: each test creates fresh instances. Descriptive names throughout.

#### 5.4 Data Safety
No shared mutable state in tests (all fixtures are dict literals). No multi-step mutations. CLEAN.

#### 5.5 Implementation-Aware Gap Analysis
`engine_models.py` has 4 model classes with `ConfigDict(extra="allow")`. All code paths (field access, defaults, extra-field round-trips, validation errors) exercised by tests. 100% coverage confirms no untouched paths.

#### 5.6 Necessity Check
Not applicable (no new dependencies or external integrations).

#### 5.7 Builder Process Quality
One `## Builder Notes` section. One clean implementation in 86 lines. CLEAN.

---

### Pass 2: Informational Findings
- The 4 smoke-test `is not None` assertions could be strengthened to assert one structural property (e.g., `config.version == 10`), but this is style-level.
- `test_statuses_is_list_of_dicts_with_name_key`: explicit `isinstance(status, dict)` assertion would make the intent clearer.
- Error coverage concentrates on `version`/`statuses` for BoardConfig and `id`/`title`/`status`/`priority` for TaskRecord. Other required fields (`tasks_dir`, `created`, `updated`, etc.) not validated for missing-field errors. Acceptable for a RED/GREEN scope.

---

### Deductions
- -0.01 LAX smoke-test assertions (4×, fully compensated)
- -0.01 LAX `hasattr` branch in statuses assertion (superfluous but not defective)

**Confidence: .98 → PASS**

### Verdict
PASS #713 → docs | confidence .98

[[2026-04-09]] Thu 05:58
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `engine_models.py` is engine-internal; not an MCP boundary. `copilot-instructions.md` covers only branch structure — no module tables to update. |
| 2 | Module docstrings | Yes | Verified | Module docstring accurate. All 4 classes have docstrings: `BoardInfo`, `BoardDefaults`, `BoardConfig`, `TaskRecord` — each accurate and complete. No edits needed. |
| 3 | External attribution | No | N/A | Pure Pydantic usage; no external patterns, articles, or repos cited. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced for this task; brief reference is parent #712. |

### Scratch Files
None found — no `.owlbear/scratch/713-*` files exist.

### Files Updated
None — no docs impact identified.

### Commit
No documentation commit needed.

[[2026-04-09]] Thu 06:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| BoardConfig tests (version, board.name, tasks_dir, statuses, priorities, defaults, next_id, claim_timeout, tui, unknown-field) | `TestFromAC_BoardConfig`: 16 tests all pass — `test_version_is_int`, `test_board_name_is_str`, `test_tasks_dir_is_str`, `test_statuses_is_list_of_dicts_with_name_key`, `test_priorities_is_list_of_strings`, `test_defaults_*` (×3), `test_next_id_is_int`, `test_claim_timeout_is_str`, `test_tui_section_preserved_in_dump`, `test_unknown_top_level_field_preserved`, error tests (×2) | PASS |
| TaskRecord tests (all frontmatter fields, body, unknown-field round-trip) | `TestFromAC_TaskRecord`: 28 tests all pass — field access, defaults, body, round-trip for `class`/`started`/`completed`, error paths (×4) | PASS |
| ISO 8601 timestamps as strings (not datetime) | `test_created_is_str_not_datetime`, `test_updated_is_str_not_datetime`, `test_claimed_at_is_str_not_datetime`, `test_go_nanosecond_precision_preserved_verbatim` — all pass | PASS |
| All tests fail (RED phase) | Test-writer commit `2de7c8c` confirmed `ModuleNotFoundError` at collection. Builder commit `a5106b7` added `engine_models.py`, all 44 pass. | PASS |

### Test Results
- pytest (task-scoped): **44 passed**, 0 failed
- pytest (full suite): 3730 passed, 413 failed, 18 skipped, 1 error — **all failures pre-existing**, 0 in task scope
- ruff: **clean** for `engine_models.py` and `test_kanban_engine_models.py`; 5 pre-existing issues in unrelated files

### Architect Quality: 4/5
Original AC1 omitted `version`, `board.name`, `tasks_dir`, and `tui` fields from BoardConfig spec. Architect caught and corrected in refinement — binding addendum. AC2–AC4 were specific and complete. Minor gap self-corrected.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 4 PASS) → no deduction
- Lint violations in task scope: 0 → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed, .98 PASS) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: 1.00
### Action: archive
