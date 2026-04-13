---
id: 801
title: Tests — TaskSummary model
status: review
priority: needed
created: '2026-04-10T21:20:41.798290+00:00'
updated: '2026-04-13T22:10:02.508232+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 800
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `TaskSummary` schema: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on
- Tests verify `TaskSummary` excludes: body, created, updated, claimed_by, claimed_at, file
- Tests verify `list_tasks` returns `TaskSummary` projections instead of hand-built dicts
- Tests verify `TaskSummary` can be constructed from `Task` instance
- Tests fail RED before implementation

## Context

Phase 1, Chain 1 step 3. Depends on #800 (Task rename complete).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/tasksummary-model-tests-801.md
- Sources: 6 studied, 3 high-relevance (S1–S3: engine models, server.py, brief)
- Recommendation: 4 test classes in tests/test_tasksummary_model_801.py — schema inclusion (10 fields), schema exclusion (6 fields), from_task construction with claimed coercion, list_tasks return type. 9+ tests fail RED. (confidence: 0.92)
- Follow-up tasks created: none — #801 itself advances; #802 (GREEN) already exists
- Decision requests: none

## Challenge Results
- Challenge: skipped — test design for planned model, no design decision
- Tier: T1 — Autonomous

## Reflection
- Current TaskSummary has extra="allow" which silently accepts excluded fields during construction — tests must verify at both schema AND instance level for proper RED coverage
- 5 schema-level and 4+ instance-level tests will fail RED, providing solid coverage for the GREEN phase (#802)
- Dependency #800 is unblocked (Task alias already in place)
[[2026-04-11]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for TaskSummary model only |
| Interface clarity | PASS | 10 inclusion fields, 6 exclusion fields enumerated; construction and list_tasks return type specified |
| Dependency correctness | PASS | depends_on=[800] correct — TaskSummary tests need Task class which #800 canonicalizes. #800 in backlog (orchestrator handles dispatch order) |
| Module layering | PASS | Test file imports from owlbear_kanban.models — valid |
| TDD compliance | PASS | This IS the RED test task; #802 (GREEN) depends on it |
| KISS/YAGNI | PASS | Minimal scope: 4 test classes, ~9 RED failures |
| Premise challenge | PASS | TaskSummary needed per brief O2 (replace hand-built dicts in server.py) |
| Pattern consistency | PASS | Follows test_kanban_engine_models.py and test_engine_package_boundary_817.py patterns; uses Pydantic model_fields introspection |
| Security surface | N/A | Test file, no new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Codebase Evidence
- Current TaskSummary (models.py:93-101): has id, title, status, priority, tags, blocked, claimed_by. Missing: block_reason, claimed (bool), parent, depends_on
- server.py list_tasks (lines 134-155): hand-built dict stripping with manual `claimed = record.claimed_by is not None` — confirms TaskSummary projection is needed
- extra="allow" on current TaskSummary means construction from Task.model_dump() leaks excluded fields — instance-level exclusion tests will properly fail RED
- Research doc analysis (confidence 0.92) correctly identifies 9+ RED failures across 4 test classes

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in session
- Architect response: Proceeding — straightforward test task with clear AC, no design decisions, tagged type:test

### Verdict: APPROVE
### Action Taken: Advanced #801 to todo. AC is precise and verifiable. All fields enumerated. RED failure coverage confirmed via codebase analysis of current TaskSummary schema gaps.
[[2026-04-11]]
## Test-Writer Notes

**Test file:** `tests/test_tasksummary_model_801.py`

### Test classes

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_TaskSummarySchema` | schema inclusion | 5 |
| `TestFromAC_TaskSummaryExcludes` | schema exclusion + construction | 5 |
| `TestFromAC_TaskSummaryFromTask` | from-Task construction + claimed coercion | 3 |
| `TestFromAC_ListTasksProjection` | list_tasks return type | 1 |

**Total: 14 tests — all 14 FAIL (verified: `14 failed, 0 passed`)**

### Failure types
- `AssertionError` — schema checks: missing `claimed`, `block_reason`, `parent`, `depends_on`; `claimed_by` present in schema; `extra="allow"` leaks `body`, `created`, `updated`, `claimed_by` into `model_dump()`
- `AttributeError` — `TaskSummary` has no `.claimed` attribute
- `AssertionError` — `list_tasks` return type is `list[dict]`, not `list[TaskSummary]`

### AC coverage

| AC line | Tests |
|---------|-------|
| TaskSummary schema — 10 inclusion fields | `test_inclusion_fields_all_present`, `test_claimed_is_bool_not_optional_string`, `test_block_reason_field_present`, `test_parent_field_present`, `test_depends_on_field_present` |
| TaskSummary excludes 6 fields | `test_excluded_fields_absent_from_schema`, `test_claimed_by_not_in_schema`, `test_body_not_in_construction_output`, `test_temporal_fields_not_in_construction_output`, `test_claimed_by_not_in_construction_output` |
| list_tasks returns TaskSummary projections | `test_list_tasks_return_type_is_list_of_tasksummary` |
| TaskSummary constructed from Task | `test_from_task_instance_construction_succeeds`, `test_claimed_true_when_task_has_claimed_by`, `test_claimed_false_when_task_unclaimed` |

### Quality check
- `ruff check`: clean (0 errors)
[[2026-04-11]]
## Builder Notes

### Files changed
- `serve/kanban/src/owlbear_kanban/models.py` — Updated `TaskSummary`:
  - `extra="allow"` → `extra="ignore"` (prevents excluded field leakage)
  - Removed `claimed_by: str | None`
  - Added `block_reason: str | None = None`, `claimed: bool = False`, `parent: int | None = None`, `depends_on: list[int]`
  - Added `_coerce_claimed` `model_validator(mode="before")` — converts `claimed_by` string → `claimed` bool (mirrors `KanbanTask` pattern)
  - Added `model_validator` to pydantic import
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — Updated `list_tasks`:
  - Added `from owlbear_kanban.models import TaskSummary` (runtime import)
  - Return type: `list[dict]` → `list[TaskSummary]`
  - Replaced hand-built `_strip`/`lean` loop with `[TaskSummary.model_validate(record.model_dump()) for record in records]`

### Test results
- **14 passed, 0 failed** (all `TestFromAC_*` classes green)
- RED verified by test-writer: 14 failed before implementation

### Lint
- `ruff check models.py server.py`: clean (0 errors)
- Fixed ANN401 by typing `_coerce_claimed` as `object → object` instead of `Any → Any`

### Evidence
- `test_claimed_is_bool_not_optional_string`: `TaskSummary.model_fields["claimed"].annotation is bool` ✓
- `test_excluded_fields_absent_from_schema`: no body/created/updated/claimed_by/claimed_at/file in `model_fields` ✓
- `test_body_not_in_construction_output`, `test_temporal_fields_not_in_construction_output`: `extra="ignore"` drops them ✓
- `test_claimed_true/false_when_task_*`: `_coerce_claimed` validator correctly converts `claimed_by` → bool ✓
- `test_list_tasks_return_type_is_list_of_tasksummary`: return annotation resolves to `list[TaskSummary]` ✓
[[2026-04-12]]
## Review Evidence

### Execution Summary
- Reviewer claimed task, dispatched quality-runner + code-reader fan-out (Step 2.5)
- **quality-runner**: FATAL EXECUTION ERROR — WMI deadlock in Python 3.12.13 during pytest-xdist worker spawn (textwrap import in execnet gateway initialization). 2+ internal retry attempts all failed. Cannot run pytest, ruff, or coverage.
- **code-reader (Explore fallback)**: returned full file content — used for static analysis
- Fallback sequential workflow also depends on quality-runner for Steps 3–4 → block per protocol

### Changed Files (Step 1)
- `serve/kanban/src/owlbear_kanban/models.py` — confirmed in git diff
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — confirmed in git diff
- `tests/test_tasksummary_model_801.py` — test-writer artifact (committed prior, not in current diff)

### Test Execution (Step 2)
**BLOCKED** — quality-runner returned fatal execution error (WMI deadlock). Builder self-report: 14 passed, 0 failed. Not verified independently. Cannot issue verdict.

### Static Analysis (Steps 5–7 partial — for when review is re-run)

**AC compliance table:**

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| TaskSummary schema: 10 inclusion fields | `test_inclusion_fields_all_present`, `test_claimed_is_bool_not_optional_string`, `test_block_reason_field_present`, `test_parent_field_present`, `test_depends_on_field_present` | Yes — `model_fields` membership + annotation type check | COVERED |
| TaskSummary excludes 6 fields | `test_excluded_fields_absent_from_schema`, `test_claimed_by_not_in_schema`, `test_body_not_in_construction_output`, `test_temporal_fields_not_in_construction_output`, `test_claimed_by_not_in_construction_output` | Yes — schema-level AND model_dump() output verified | COVERED |
| list_tasks returns TaskSummary projections | `test_list_tasks_return_type_is_list_of_tasksummary` | Yes — inspect.unwrap + get_type_hints checks args[0] is TaskSummary | COVERED |
| TaskSummary constructed from Task | `test_from_task_instance_construction_succeeds`, `test_claimed_true_when_task_has_claimed_by`, `test_claimed_false_when_task_unclaimed` | Yes — isinstance check + bool coercion both paths | COVERED |
| Tests fail RED before implementation | Not verifiable from static analysis; test-writer notes confirm 14 failed | N/A (pre-condition) | REPORTED |

**TestFromAC integrity:** No modifications detected. All 14 tests have tight, specific assertions. No lazy checks.

**Implementation quality (static):**
- `extra="ignore"` correctly prevents excluded field leakage
- `_coerce_claimed` validator: pops `claimed_by`, sets `claimed = claimed_by is not None`. Both None and non-None paths covered by tests. No conflicting key risk since `Task.model_dump()` has `claimed_by` but never `claimed`.
- `list_tasks` return: `[TaskSummary.model_validate(record.model_dump()) for record in records]` replaces hand-built dict loop correctly
- `from __future__ import annotations` + `typing.get_type_hints` in test: resolves against server module namespace which imports `TaskSummary` — `args[0] is TaskSummary` identity check valid

**Security (static):** No issues. `extra="ignore"` reduces attack surface vs prior `extra="allow"`. No injection, hardcoded secrets, path traversal, or deserialization risks.

**Lint (static):** Code appears clean. Cannot independently verify with ruff.

### Verdict
**BLOCK** — Cannot independently execute tests. Static analysis suggests implementation is correct, but protocol requires independent test execution. Re-run review after resolving WMI/Python 3.12.13 environment issue or ensuring quality-runner can spawn pytest workers on this Windows machine.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational — independently verified with scoped run on #801: 14/14 passed, ruff clean. Unblocked for review continuation.