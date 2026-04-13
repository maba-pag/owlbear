---
id: 802
title: Add TaskSummary model + server integration
status: done
priority: needed
created: '2026-04-10T21:20:49.680606+00:00'
updated: '2026-04-12T03:49:08.590416+00:00'
tags:
- phase-1
- scope:mcp-kanban
- model
- rigor:thorough
parent: 798
depends_on:
- 801
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `TaskSummary` Pydantic model in `engine_models.py`
- Fields: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on
- `list_tasks` engine method returns `list[TaskSummary]`
- `server.py` `_strip` dict eliminated, replaced by `TaskSummary`
- Adapter `outputSchema` patching updated to match TaskSummary schema
- #801 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, Chain 1 step 4. Depends on #801 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/tasksummary-model-integration-802.md
- Sources: 8 studied, 4 high-relevance (S1-S4: models.py, server.py, KanbanTask pattern, brief)
- Recommendation: Option A — update TaskSummary (extra="ignore", _coerce_claimed validator, 4 new fields), convert at end of engine list_tasks, simplify server _strip→model_dump(), auto-generate outputSchema from model (confidence: 0.88)
- Follow-up tasks created: #839 — update 2 engine listing test assertions broken by return type change
- Decision requests: none

## Challenge Results
- Challenge: FALLBACK — trivial GREEN implementation of planned model, no design decision
- Tier: T1 — Autonomous
- Key risks: 2 engine test assertions break (isinstance TaskRecord, t.claimed_by); mitigated by follow-up #839

## Reflection
- AC references `engine_models.py` but actual file is `models.py` — naming inconsistency from planning, not a blocker
- The `extra="ignore"` + `model_validator` pattern from KanbanTask (S3) is the established project pattern; reuse it
- Internal filter/sort must operate on full TaskRecord before projecting to TaskSummary at return — body needed for search, claimed_by needed for unclaimed filter
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One projection model (TaskSummary) + integration across engine and server — single concern |
| Interface clarity | PASS | 10 inclusion fields enumerated, construction contract clear. AC line 1 says `engine_models.py` but file is `models.py` — already flagged in Reflection, builder must use `serve/kanban/src/owlbear_kanban/models.py` |
| Dependency correctness | PASS | depends_on=[801] correct — RED tests in-progress (14 failing tests written in `tests/test_tasksummary_model_801.py`). Follow-up #839 depends on #802 for engine test assertion fixes |
| Module layering | PASS | TaskSummary in `owlbear_kanban.models`, imported by engine (same package) and server (downstream). No upward imports |
| TDD compliance | PASS | #801 is the preceding RED task with 14 failing tests covering all AC lines |
| KISS/YAGNI | PASS | Minimal changes: update model fields, add validator, change engine return type, simplify server loop, auto-generate outputSchema |
| Premise challenge | PASS | Brief O2 requires replacing hand-built `_strip` dicts; current 12-field exclusion set + manual `claimed` bool coercion in server.py (lines 134-155) is clear tech debt |
| Pattern consistency | PASS | Follows established `KanbanTask` pattern: `extra="ignore"` + `@model_validator(mode="before")` for `_coerce_claimed` (see `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` lines 11, 32-38) |
| Security surface | N/A | No new system boundaries — internal model projection |
| Single domain | PASS | scope:mcp-kanban only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| TaskSummary Pydantic model in `engine_models.py` | File name wrong — actual is `models.py` | Builder note: use `serve/kanban/src/owlbear_kanban/models.py` |
| Fields: 10 enumerated | Verifiable, matches research | None |
| `list_tasks` returns `list[TaskSummary]` | Verifiable; Option A from research (filter on TaskRecord, project at return) is correct | None |
| `_strip` dict eliminated | Verifiable; server loop → `[r.model_dump() for r in records]` | None |
| outputSchema patching updated | Verifiable; `TaskSummary.model_json_schema()` replaces 24-line manual schema | None |
| #801 tests pass GREEN | Verifiable; 14 RED tests in test file | None |
| Existing MCP tests pass (O4) | Verifiable; research §3.4 confirms MCP tests check dict keys, unaffected | None |

### Dependency Analysis
- **#801** (RED tests): `in-progress` — 14 failing tests written, covers all AC. Correct dependency.
- **#839** (engine listing test fixes): `research`, depends_on=[802]. Correctly scoped follow-up for 2 broken assertions (`isinstance TaskRecord` → `TaskSummary`, `t.claimed_by` → `t.claimed`).

### Architecture Notes
- Internal filter/sort MUST operate on full TaskRecord (needs `body` for search, `claimed_by` for unclaimed filter) before projecting to TaskSummary at return boundary — research §3.2 confirms this
- `extra="ignore"` silently drops extra fields from `Task.model_dump()`, making construction safe without explicit field exclusion
- outputSchema wrapper should be `{"type": "array", "items": TaskSummary.model_json_schema()}` per research §3.5 — but verify actual MCP SDK schema wrapping conventions at build time

### Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Architect response: Proceeding — straightforward GREEN implementation of planned model, research confidence 0.88, no design decisions requiring challenge

### Verdict: APPROVE
### Action Taken: Advanced #802 to todo. AC is precise and verifiable. File name correction noted for builder (models.py not engine_models.py). Architecture follows established KanbanTask pattern. Two engine test breakages mitigated by follow-up #839.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_tasksummary_server_integration_802.py
- Classes: TestFromAC_EngineListTasksReturn, TestFromAC_OutputSchemaDerivedFromModel
- Tests per category: happy 2, edge 2, error 1, boundary 2
- Total: 7 tests, all FAIL
- ruff: clean
- Commit: 4141e626

### AC Coverage

| AC Line | Tests | Status |
|---------|-------|--------|
| AC1/AC2 TaskSummary fields/exclusions | Covered by #801 | n/a |
| AC3 engine annotation list[TaskSummary] | test_engine_list_tasks_return_annotation_is_list_of_tasksummary | FAIL |
| AC3 engine runtime TaskSummary instances | test_engine_list_tasks_runtime_returns_tasksummary_instances | FAIL |
| AC3 engine claimed bool attribute | test_engine_list_tasks_claimed_is_bool_not_string_attribute | FAIL |
| AC3 engine body excluded | test_engine_list_tasks_body_not_in_model_dump | FAIL |
| AC4 _strip eliminated | Pre-implemented in prior push — verified absent; no new test applies (AC4 server.py part already done) | pre-GREEN |
| AC5 outputSchema == model_json_schema | test_output_schema_items_equal_tasksummary_model_json_schema | FAIL |
| AC5 outputSchema has Pydantic title | test_output_schema_items_include_pydantic_title_from_model | FAIL |
| AC5 outputSchema has required array | test_output_schema_items_have_required_array_from_model_schema | FAIL |
| AC6 #801 tests pass GREEN | meta — no code test | n/a |
| AC7 Existing MCP tests unaffected | meta — no code test | n/a |

### Notes for Builder
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` already has `_strip` removed and uses `TaskSummary.model_validate(record.model_dump())` — AC4 server.py part is pre-implemented
- `serve/kanban/src/owlbear_kanban/engine.py` `list_tasks` still returns `list[TaskRecord]` — needs annotation change + projection to TaskSummary at return boundary
- `outputSchema` is still manually hardcoded — needs `{"type": "array", "items": TaskSummary.model_json_schema()}` wrapping
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/kanban/src/owlbear_kanban/engine.py` — Added `TaskSummary` to import; changed `list_tasks` return annotation from `list[Task]` to `list[TaskSummary]`; project to `TaskSummary` at return boundary via `model_validate(t.model_dump())`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — Replaced hardcoded 22-line `items` dict in `outputSchema` with `TaskSummary.model_json_schema()`

### Test Results
- `test_tasksummary_server_integration_802.py`: 7/7 passed (was all FAIL in RED)
- `test_tasksummary_model_801.py`: 14/14 passed (AC6 meta-condition confirmed)
- Broader regression run (91 tests across 6 test files): all passed
- 2 files changed, 21 insertions(+), 54 deletions(-)

### Lint
- ruff: clean on both changed files

### Coverage
- N/A — Quality-Runner not available; scoped to changed modules only

### Evidence
- AC3: `list_tasks` annotation is now `list[TaskSummary]`; runtime items verified as `TaskSummary` instances
- AC4: `_strip` already removed prior push (confirmed absent, no new tests needed)
- AC5: `outputSchema.items` now equals `TaskSummary.model_json_schema()` — has `title`, `required`, Pydantic-style anyOf nullables
- AC6: 801 tests 14/14 GREEN
- AC7: Existing MCP tests unaffected; pre-existing collection errors in 6 unrelated test files are unchanged

### Commit
`3703469e` — feat: add TaskSummary projection in engine.list_tasks + derive outputSchema from model (#802)
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest (scoped — 801+802 files): **21 passed, 0 failed**
- pytest (regression — engine_listing + crud + models): **126 passed, 2 failed**
  - `test_result_items_are_task_records` — pre-disclosed, tracked by #839
  - `test_unclaimed_returns_only_tasks_without_claimed_by` — pre-disclosed, tracked by #839
- pytest (mcp_kanban_list_tasks_472): 5 passed, 21 failed — all pre-existing
  - 18 failures: `AppContext.__init__() got unexpected kwarg 'kanban_bin'` — structural mismatch predating #802
  - 2 schema type failures: old schema already used `type: "object"` wrapper (research doc §3.5 confirms); #802 did not change top-level structure, only replaced hardcoded `items` content with `model_json_schema()`

### Lint
- clean: true — ruff passes on all changed files

### Coverage
- owlbear_kanban.models: **100%**
- owlbear_kanban.engine: **69%** (full engine; list_tasks path exercised by tests)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC3: engine annotation `list[TaskSummary]` | `test_engine_list_tasks_return_annotation_is_list_of_tasksummary` | YES — asserts `args[0] is TaskSummary` | COVERED |
| AC3: runtime items are TaskSummary | `test_engine_list_tasks_runtime_returns_tasksummary_instances` | YES — `isinstance(item, TaskSummary)` | COVERED |
| AC3: claimed is bool | `test_engine_list_tasks_claimed_is_bool_not_string_attribute` | YES — `isinstance(item.claimed, bool)` + `claimed_by` absent from model_dump | COVERED |
| AC3: body excluded | `test_engine_list_tasks_body_not_in_model_dump` | YES — `"body" not in dumped` | COVERED |
| AC4: `_strip` eliminated | pre-GREEN (no new test; verified absent by test-writer) | n/a | COVERED |
| AC5: items == model_json_schema() | `test_output_schema_items_equal_tasksummary_model_json_schema` | YES — exact dict equality | COVERED |
| AC5: has Pydantic title | `test_output_schema_items_include_pydantic_title_from_model` | YES — `"title" in items` and `items["title"] == "TaskSummary"` | COVERED |
| AC5: has required array | `test_output_schema_items_have_required_array_from_model_schema` | YES — `"required" in items` | COVERED |

#### Security Review
No issues. Changed code: engine projects Task→TaskSummary at return boundary (no new boundaries); server replaces hardcoded items dict with `model_json_schema()` (no injection surface). `extra="ignore"` + `_coerce_claimed` validator follow established KanbanTask pattern. No hardcoded secrets, no shell/SQL injection, no path traversal, no insecure deserialization.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_engine_list_tasks_return_annotation_is_list_of_tasksummary` | None | PRESERVED |
| `test_engine_list_tasks_runtime_returns_tasksummary_instances` | None | PRESERVED |
| `test_engine_list_tasks_claimed_is_bool_not_string_attribute` | None | PRESERVED |
| `test_engine_list_tasks_body_not_in_model_dump` | None | PRESERVED |
| `test_output_schema_items_equal_tasksummary_model_json_schema` | None | PRESERVED |
| `test_output_schema_items_include_pydantic_title_from_model` | None | PRESERVED |
| `test_output_schema_items_have_required_array_from_model_schema` | None | PRESERVED |

Builder only changed `engine.py` and `server.py` — test file unchanged.

#### Test Quality: STRONG
Assertions are specific and mutation-resistant: type annotation inspected via `get_type_hints`; runtime isinstance checks; attribute presence/absence verified; dict equality on schema. No lazy `assert result` patterns. Test names descriptive. Fixtures use tmp_path, no shared mutable state.

#### Data Safety: No issues
`model_validate(t.model_dump())` projection is deterministic, no LLM output, no race conditions.

#### Implementation-Aware Test Gap Analysis: No gaps
Core new path (TaskSummary projection at engine return boundary) fully exercised by 4 dedicated tests. outputSchema patching exercised by 3 dedicated tests. Filter logic operates on full Task objects before projection — architecture constraint verified correct.

#### Builder Process Quality: CLEAN
Single `## Builder Notes` section. No retries.

### Pass 2 — Informational
- **server.py double-conversion**: engine already returns `list[TaskSummary]`; server.py re-runs `TaskSummary.model_validate(record.model_dump())`. Redundant but safe — `extra="ignore"` makes round-trip idempotent. No functional impact.
- **Schema wrapper structure deviation**: Research §3.5 recommended `{"type": "array", "items": ...}` top-level, but builder preserved existing `{"type": "object", "properties": {"result": {...}}}` wrapper. Not a regression (structure was already `type: "object"` pre-#802). The AC5 tests verify items content, not wrapper shape.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: TaskSummary model in models.py | `serve/kanban/src/owlbear_kanban/models.py:86` — `class TaskSummary(BaseModel)` | #801 tests | PASS |
| AC2: 10 fields | `models.py:96-108` — id, title, status, priority, tags, blocked, block_reason, claimed, parent, depends_on | #801 tests | PASS |
| AC3: engine returns list[TaskSummary] | `engine.py:145` — `-> list[TaskSummary]`; `engine.py:~219` — `return [TaskSummary.model_validate(t.model_dump()) for t in tasks]` | 4 tests, all PASS | PASS |
| AC4: `_strip` eliminated | `server.py` — no `_strip` dict; `list_tasks` returns `list[TaskSummary]` directly; pre-GREEN | n/a | PASS |
| AC5: outputSchema from model_json_schema() | `server.py` — `_list_tasks_tool_obj.fn_metadata.output_schema = {..., "items": TaskSummary.model_json_schema()}` | 3 tests, all PASS | PASS |
| AC6: #801 tests GREEN | 21 passed includes 14 from `test_tasksummary_model_801.py` | quality-runner | PASS |
| AC7: Existing MCP tests unaffected | 5 passing MCP tests in #472 unchanged; 21 failures pre-existing (kanban_bin infrastructure mismatch + pre-existing type:object schema expectation) | quality-runner | PASS |

### Deductions
- None (Pass 1 fully met)

### Verdict: PASS
Confidence: .93

All AC lines verified with evidence. 7/7 task-specific tests pass. Pre-existing #472 failures confirmed pre-existing by research §3.5. 2 engine-listing regressions pre-disclosed and tracked by #839. Lint clean. No security issues. No TestFromAC modifications.
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `list_tasks` return type changed to `list[TaskSummary]`. `copilot-instructions.md` covers only project identity and branch conventions — no API tables; no update needed |
| 2 | Module docstrings | Yes | Verified | `engine.py` list_tasks: "Returns: Filtered, sorted list of TaskSummary objects." ✓ `models.py` TaskSummary: "Lightweight task summary for list operations — excludes body, timestamps, and claimed_by." ✓ `_coerce_claimed`: "Convert claimed_by string to a boolean claimed flag." ✓ `server.py` list_tasks: "List kanban tasks with optional filters." ✓ All accurate post-change |
| 3 | External attribution | No | N/A | Research S8 (Pydantic v2 docs) has no URL recorded, relevance 0.8, and is not among the 4 high-relevance sources. All actionable patterns derived from S3 (internal KanbanTask model). Pydantic v2 docs already in sources/overview.md from #806 |
| 4 | CLI changes | No | N/A | Builder notes confirm no CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/tasksummary-model-integration-802.md` exists, linked in task body under ## Research section, follow-up #839 created |

### Files Updated
None — all docstrings accurate, no behavior-change prose in copilot-instructions.md, no new external sources.

### Scratch Files
None found matching `.owlbear/scratch/802-*`.
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: TaskSummary model in models.py | `models.py:96` class TaskSummary(BaseModel) with extra="ignore" | PASS |
| AC2: 10 fields present | `models.py:101-110` all 10 fields verified | PASS |
| AC3: engine returns list[TaskSummary] | `engine.py:146` annotation; line ~219 projection via model_validate | PASS |
| AC4: _strip eliminated | grep confirms no _strip in server.py | PASS |
| AC5: outputSchema from model_json_schema() | `server.py:147` TaskSummary.model_json_schema() | PASS |
| AC6: #801 tests GREEN | 14/14 passed | PASS |
| AC7: Existing MCP tests unaffected | 21 MCP failures pre-existing (kanban_bin mismatch); unchanged by #802 | PASS |

### Test Results
- Task-scoped (801+802): 21 passed, 0 failed
- Full suite: 3599 passed, 271 failed, 6 collection errors, 8 skipped
- 2 in-scope failures (test_result_items_are_task_records, test_unclaimed_returns_only_tasks_without_claimed_by) pre-disclosed and tracked by follow-up #839
- Remaining 269 failures across 37 files are pre-existing infrastructure issues (ImportError, kanban_bin mismatch, etc.)
- ruff: All checks passed

### Architect Quality: 4/5
AC was specific and verifiable. File name error (engine_models.py vs models.py) caught early in research and documented. 2 engine test regressions were an anticipated consequence, mitigated by follow-up #839 before build started. Research recommendation (Option A) aligned with established patterns and was well-scoped.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (all 7 verified) = 0
- Lint violations: none = 0
- AC quality 4/5 (not <=3): 0
- Missing reviewer evidence: present, detailed, PASS verdict = 0
- Full-suite test failures in task scope: 2 failures caused by #802 return type change, pre-disclosed, tracked by #839 = -.05

### Confidence: .95
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4141e626 | test | tests/test_tasksummary_server_integration_802.py | #802 |
| 3703469e | feat | engine.py, server.py | #802 |