---
id: 714
title: 'P3-02: GREEN — Pydantic models for BoardConfig and TaskRecord'
status: archived
priority: medium
created: 2026-04-09T03:24:35.9375742+02:00
updated: 2026-04-09T08:39:19.8800999+02:00
started: 2026-04-09T08:39:19.8800999+02:00
completed: 2026-04-09T08:39:19.8800999+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 713
class: standard
---

## Objective
Implement internal Pydantic models for `BoardConfig` and `TaskRecord` inside `serve/mcp-kanban/src/owlbear_mcp_kanban/`.

Brief: see parent #712

## AC
- [ ] `BoardConfig` model matches config.yml schema (version, board.name, tasks_dir, statuses as list of dicts, priorities, defaults, claim_timeout, next_id, tui — preserved)
- [ ] `TaskRecord` model matches task file frontmatter spec (all fields including claimed_by, claimed_at, started, completed, class — preserved via extra='allow' or equivalent)
- [ ] Unknown fields preserved via model config
- [ ] Timestamps stored as strings (ISO 8601), not datetime objects
- [ ] All T01 (#713) tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (new)

[[2026-04-09]] Thu 06:20
## Architecture Review

### Context
GREEN implementation task for `engine_models.py`. **Critical finding: the deliverable already exists.** #713's builder created `engine_models.py` (86 lines, 4 models) during the RED task's pipeline lifecycle — 44 tests pass, 100% coverage. All AC for #714 is already satisfied.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `BoardConfig` matches config.yml schema (version, board.name, tasks_dir, statuses, priorities, defaults, claim_timeout, next_id, tui) | SATISFIED — `engine_models.py` L40-57: `BoardConfig` with all fields, `BoardInfo`/`BoardDefaults` sub-models. Verified against `.owlbear/kanban/config.yml` (version=10, claim_timeout="1h", next_id=734, tui section present). | None — already implemented |
| `TaskRecord` matches task file frontmatter (all fields incl. claimed_by, claimed_at, started, completed, class — preserved via extra='allow') | SATISFIED — `engine_models.py` L59-86: 13 explicit fields + `extra="allow"` for `class`, `started`, `completed`. Verified against task files (e.g. task #2 has `started`, `completed`, `class`). | None — already implemented |
| Unknown fields preserved via model config | SATISFIED — `ConfigDict(extra="allow")` on all 4 model classes | None |
| Timestamps stored as strings (ISO 8601), not datetime | SATISFIED — `created: str`, `updated: str`, `claimed_at: str \| None` | None |
| All T01 (#713) tests pass | SATISFIED — 44/44 pass per #713 reviewer (confidence .98) | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine-internal data models only |
| Interface clarity | PASS | 4 models with clear field types and docstrings |
| Dependency correctness | PASS | #713 (RED) is `done` |
| Module layering | PASS | `engine_models.py` inside `owlbear_mcp_kanban` package, separate from MCP-boundary `models.py` |
| TDD compliance | PASS | RED task #713 completed first |
| KISS/YAGNI | PASS | Minimal models with `extra="allow"` — no over-engineering |
| Premise challenge | PASS (redundant) | Deliverable already exists from #713 builder. Task is effectively a pipeline pass-through. Not rejecting because the file does need to exist — the duplicate work arose from RED/GREEN task split where the builder in RED already delivered the GREEN work. |
| Pattern consistency | PASS | Follows existing `models.py` patterns: `ConfigDict`, `Field(default_factory=list)`, `str` timestamps |
| Security surface | N/A | Engine-internal models reading local YAML files — no new system boundary |
| Single domain | PASS | Kanban engine domain only |

### Architecture Notes

1. **Redundancy origin**: The planner created RED/GREEN task pairs (#713/#714), but the pipeline processes each task through test-writer → builder → reviewer → docs. The builder in #713 implemented `engine_models.py` to make the tests pass — which is exactly what #714 asks for. All downstream agents should treat this as a pass-through.
2. **Model design verified**: `BoardInfo`/`BoardDefaults` sub-models correctly decompose nested config.yml structure. `extra="allow"` on all models preserves vendor fields (`tui`, `class`, `started`, `completed`). Timestamp-as-string strategy avoids Go nanosecond drift.
3. **File location**: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` — correct per parent #712 brief (D6: engine inside mcp-kanban).

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation confirms all AC already satisfied. Redundancy is a planning artifact, not a quality concern.

### Verdict: APPROVE
### Action Taken: Approved #714 to todo as pipeline pass-through. All AC already satisfied by #713's builder implementation (`engine_models.py`, 86 lines, 44 tests, 100% coverage). Downstream agents should confirm existing deliverables and pass through.

[[2026-04-09]] Thu 07:42
## Test-Writer Notes
- **Pass-through — pre-existing implementation**
- Test file: `tests/test_kanban_engine_models.py` (written by test-writer for #713)
- Existing coverage: `TestFromAC_BoardConfig` (16 tests) + `TestFromAC_TaskRecord` (28 tests) = **44 tests, all PASS**
- Implementation: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (86 lines, 4 models, 100% coverage) — delivered by #713's builder

### AC Coverage (all satisfied by existing tests)
| AC Line | Test(s) | Status |
|---------|---------|--------|
| `BoardConfig` matches config.yml schema (version, board.name, tasks_dir, statuses, priorities, defaults, claim_timeout, next_id, tui) | `test_version_is_int`, `test_board_name_is_str`, `test_tasks_dir_is_str`, `test_statuses_is_list_of_dicts_with_name_key`, `test_priorities_is_list_of_strings`, `test_defaults_*` (×3), `test_next_id_is_int`, `test_claim_timeout_is_str`, `test_tui_section_preserved_in_dump`, `test_unknown_top_level_field_preserved` | PASS |
| `TaskRecord` matches frontmatter spec (all fields incl. claimed_by, claimed_at, started, completed, class — via extra='allow') | Full field coverage + defaults tests (×7) + error tests (×4) + round-trip (×3) | PASS |
| Unknown fields preserved via model config | `test_unknown_top_level_field_preserved`, `test_tui_section_preserved_in_dump`, `test_class_field_preserved_in_round_trip` | PASS |
| Timestamps stored as strings (ISO 8601), not datetime | `test_created_is_str_not_datetime`, `test_updated_is_str_not_datetime`, `test_claimed_at_is_str_not_datetime`, `test_go_nanosecond_precision_preserved_verbatim` | PASS |
| All T01 (#713) tests pass | 44/44 pass — confirmed | PASS |

### Pass-Through Justification
Architecture review (2026-04-09 06:20) explicitly classified #714 as "pipeline pass-through": the deliverable was pre-built by #713's builder during its GREEN execution. No new failing tests can be written — implementation exists, coverage is 100%, all AC satisfied. Builder should confirm existing deliverables only.

[[2026-04-09]] Thu 07:58
## Builder Notes

### Pass-Through Confirmation

Architecture review and test-writer both classified #714 as a pipeline pass-through. `engine_models.py` was delivered by #713's builder during the RED task execution.

### Files Changed
- None — deliverable already existed: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (86 lines, 4 models)

### Evidence

| Check | Result |
|-------|--------|
| `engine_models.py` exists | ✓ confirmed |
| `test_kanban_engine_models.py` exists | ✓ confirmed |
| Tests pass | 44/44 PASS |
| Coverage on `engine_models.py` | 100% (36/36 statements) |
| Ruff lint | Clean (exit 0) |

### AC Verification

| AC | Status |
|----|--------|
| `BoardConfig` matches config.yml schema (version, board.name, tasks_dir, statuses, priorities, defaults, claim_timeout, next_id, tui) | ✓ PASS — L40-57, all fields present, `extra="allow"` |
| `TaskRecord` matches frontmatter spec (all fields incl. claimed_by, claimed_at, started, completed, class) | ✓ PASS — L59-86, 13 explicit fields + `extra="allow"` |
| Unknown fields preserved via model config | ✓ PASS — `ConfigDict(extra="allow")` on all 4 models |
| Timestamps stored as strings (ISO 8601) | ✓ PASS — `created: str`, `updated: str`, `claimed_at: str | None` |
| All T01 (#713) tests pass | ✓ 44/44 PASS |

### No Builder-Discovered Issues
Implementation is clean, minimal, and correct. No edge cases found beyond what existing tests cover.

[[2026-04-09]] Thu 08:15
## Review Evidence

### Test Results
- pytest (quality-runner, independent): **44 passed, 0 failed, 0 skipped**
- `TestFromAC_BoardConfig`: 16/16 pass
- `TestFromAC_TaskRecord`: 28/28 pass

### Lint
- ruff: **clean** (exit 0) on `engine_models.py` and `test_kanban_engine_models.py`

### Coverage
- `owlbear_mcp_kanban.engine_models`: **100%** (all statements covered)

### Source Control
Builder made no code changes — deliverable pre-existed from #713's builder. No `TestFromAC_*` modifications possible or detected.

### Pass 1 — CRITICAL

#### AC Compliance

| AC Line | Evidence | Mapped Tests | Would Fail If AC Violated? | Status |
|---------|----------|-------------|--------------------------|--------|
| `BoardConfig` matches config.yml schema (version, board.name, tasks_dir, statuses, priorities, defaults, claim_timeout, next_id, tui — preserved) | `engine_models.py` L40-57: all fields present; `BoardInfo.name: str`, `statuses: list[dict[str, Any]]`, `defaults: BoardDefaults`, `claim_timeout: str`, `extra="allow"` for tui | `test_version_is_int`, `test_board_name_is_str`, `test_tasks_dir_is_str`, `test_statuses_is_list_of_dicts_with_name_key`, `test_priorities_is_list_of_strings`, `test_defaults_*` (×3), `test_next_id_is_int`, `test_claim_timeout_is_str`, `test_tui_section_preserved_in_dump`, `test_unknown_top_level_field_preserved` | Yes — removing any field → ValidationError in tests; removing `extra="allow"` → tui dump test fails | **PASS** |
| `TaskRecord` matches frontmatter spec (all fields incl. claimed_by, claimed_at, started, completed, class — via extra='allow') | `engine_models.py` L59-86: 13 explicit fields; `extra="allow"` on model; `class`, `started`, `completed` preserved as extra fields | `test_class_field_preserved_in_round_trip`, `test_started_field_preserved_in_round_trip`, `test_completed_field_preserved_in_round_trip`, `test_claimed_by_stored_as_str`, full field coverage suite | Yes — removing `extra="allow"` → round-trip preservation tests fail | **PASS** |
| Unknown fields preserved via model config | `ConfigDict(extra="allow")` on all 4 model classes (`BoardInfo`, `BoardDefaults`, `BoardConfig`, `TaskRecord`) | `test_unknown_top_level_field_preserved`, `test_tui_section_preserved_in_dump`, `test_class_field_preserved_in_round_trip` | Yes — removing `extra="allow"` from any model → preservation assertion fails | **PASS** |
| Timestamps stored as strings (ISO 8601), not datetime | `engine_models.py` L74: `created: str`, `updated: str`; L84: `claimed_at: str \| None` — no datetime type hints, no validator coercion | `test_created_is_str_not_datetime`, `test_updated_is_str_not_datetime`, `test_claimed_at_is_str_not_datetime`, `test_go_nanosecond_precision_preserved_verbatim` | Yes — adding `datetime` type → Pydantic coercion, `isinstance(task.created, str)` fails for datetime object | **PASS** |
| All T01 (#713) tests pass | 44/44 pass in quality-runner independent run | All 44 tests in `TestFromAC_BoardConfig` and `TestFromAC_TaskRecord` | — | **PASS** |

#### Security Review
- Engine-internal Pydantic models; no new system boundary
- Data sourced from local YAML task files, not user request input — no injection surface
- `extra="allow"` is standard field preservation pattern; no untrusted data escaping schema
- No hardcoded secrets, no path traversal, no external I/O added
- **Clean**

#### Test Integrity — TestFromAC Comparison
Builder made zero file changes. No `TestFromAC_*` class modification was possible. All 44 tests preserved exactly as written by the test-writer for #713. **No weakening detected.**

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | **STRONG** | `isinstance(task.created, str)` type checks; exact value assertions (`config.version == 10`, `config.board.name == "OwlBear"`); `dumped.get("extra_vendor_field") == "preserved"` |
| Negative/error-path coverage | **STRONG** | 4 `pytest.raises(ValidationError)` tests in BoardConfig; 4 in TaskRecord — missing required fields |
| Mutation resistance | **STRONG** | Removing `extra="allow"` → preservation tests fail; changing`created: str` to `datetime` → timestamp type tests fail; removing `claims_by` field → defaults test fails |
| Test independence | **STRONG** | Module-level data fixtures only (`_MINIMAL_BOARD`, `_FULL_BOARD`, `_MINIMAL_TASK`, `_FULL_TASK`); no shared mutable state |
| Descriptive names | **STRONG** | All names are AC-referenced and semantically precise |

#### Builder Process Quality
Single pipeline cycle (pass-through). Architecture review and test-writer both explicitly documented the redundancy artifact. No loop violations. **CLEAN.**

### Pass 2 — Informational
None identified.

### Deductions
None.

### Verdict
**Confidence: 0.98 → PASS → docs**

[[2026-04-09]] Thu 08:21
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `engine_models.py` is engine-internal only; MCP boundary (`models.py`) unchanged. `copilot-instructions.md` is branch table only — no module-level API docs to update. |
| 2 | Module docstrings | Yes | Verified | All 4 public classes have accurate docstrings: `BoardInfo` (identity sub-section), `BoardDefaults` (defaults sub-section with extra='allow' note), `BoardConfig` (full config.yml schema with vendor-field preservation note), `TaskRecord` (frontmatter schema with timestamp string rationale). Module-level docstring present (lines 1–9). |
| 3 | External attribution | No | N/A | Pattern used: `extra="allow"` on `ConfigDict` — matches existing codebase pattern already attributed at `sources/overview.md` L752 (Pydantic v2 Models docs). No new external source. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` slug for this task. Architecture research was inline in task body; parent #712 brief covers broader context. |

### Files Updated
None — all existing docs are accurate; docstrings already complete and correct.

### Scratch Files
No `.owlbear/scratch/714-*` files found — nothing to clean.

### Summary
Pipeline pass-through confirmed. `engine_models.py` (86 lines, 4 models, 100% coverage) was pre-delivered by #713's builder. All 5 checklist items evaluated with evidence; no documentation updates required.

[[2026-04-09]] Thu 08:39
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `BoardConfig` matches config.yml schema | `engine_models.py` L40-57: all fields, `extra="allow"`, sub-models. 16 tests PASS | PASS |
| `TaskRecord` matches frontmatter spec | `engine_models.py` L59-86: 13 fields + `extra="allow"`. 28 tests PASS | PASS |
| Unknown fields preserved via model config | `ConfigDict(extra="allow")` on all 4 models. Preservation tests PASS | PASS |
| Timestamps stored as strings (ISO 8601) | `created: str`, `updated: str`, `claimed_at: str | None`. Type + precision tests PASS | PASS |
| All T01 (#713) tests pass | 44/44 pass, 0 fail | PASS |

### Test Results
- pytest (task scope): 44 passed, 0 failed
- pytest (full suite): 3763 passed, 380 failed — no failures in task scope; all pre-existing
- ruff (deliverables): clean (exit 0)

### Architect Quality: 5/5
AC was specific, verifiable, covered edge cases (Go nanosecond precision, `class` reserved word). No builder improvisation needed.

### Deduction Breakdown
None applied.

### Confidence: 1.00
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a5106b7 | feat | engine_models.py | #713 |
| 2de7c8c | test | test_kanban_engine_models.py | #713 |
Pipeline pass-through — deliverables committed under #713 (RED/GREEN overlap). Clean in working tree.
