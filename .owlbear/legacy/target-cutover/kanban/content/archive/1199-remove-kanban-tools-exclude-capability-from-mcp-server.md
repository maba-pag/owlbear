---
id: 1199
title: Remove KANBAN_TOOLS_EXCLUDE capability from MCP server
status: archived
priority: medium
created: 2026-04-30T15:28:54.925794+00:00
updated: 2026-04-30T17:42:19.073176+00:00
tags:
- audit-kanban
- mcp-server
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove KANBAN_TOOLS_EXCLUDE env var capability from MCP server.

## Files
- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- serve/mcp-kanban/README.md
- setup/setup-guide.md
- share/skills/h-mcp-kanban/SKILL.md
- share/skills/r-architecture-standards/SKILL.md
- tests/test_server_1170.py

## Change
Remove the `_apply_tool_exclusions` function, its invocation in `app_lifespan`, its `__all__` export, and all product documentation references. No active consumers use this feature.

Note: `_apply_tool_exclusions` uses the public `server.remove_tool()` API — not `_tool_manager._tools`. The `_tool_manager._tools` accesses elsewhere in server.py (outputSchema patching, `_patch_params`) are unrelated to tool exclusion and must be preserved.

## AC
- [ ] `_apply_tool_exclusions` function removed from server.py (td:1)
- [ ] `_apply_tool_exclusions` call removed from `app_lifespan` (td:1)
- [ ] `_apply_tool_exclusions` removed from `__all__` (td:0)
- [ ] `KANBAN_TOOLS_EXCLUDE` removed from product docs: README.md, setup-guide.md, h-mcp-kanban SKILL.md, r-architecture-standards SKILL.md (td:0)
- [ ] `TestFromAC_ApplyToolExclusions` test class removed from test_server_1170.py (td:0)
- [ ] Server starts and registers all tools normally (td:1)
- [ ] Existing outputSchema and _patch_params functionality preserved — no regression in tool metadata (td:1)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Removes one feature (env-var tool exclusion) cleanly |
| Interface clarity | PASS | AC lines enumerate every deletion target |
| Dependency correctness | PASS | No dependencies; downstream #1198 depends on this correctly |
| Module layering | PASS | Pure deletion, no new imports or cross-module changes |
| TDD compliance | PASS | Test deletions + server-start assertion cover the change |
| KISS/YAGNI | PASS | Removes dead feature, reduces complexity |
| Premise challenge | PASS | Feature has zero active consumers; setup-guide documents it but no MCP config file in the repo uses it |
| Pattern consistency | PASS | Mirrors how dead code should be removed (function + docs + tests) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | MCP server domain only |

### Challenge Results
- Challenger: SKIPPED — mechanical deletion with max td:1; no design decisions to challenge

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC to remove incorrect _tool_manager._tools line (unrelated to TOOLS_EXCLUDE), added doc targets, scoped change precisely. Advanced to todo.

## Finding: 4.7

[[2026-04-30]]
Architecture review complete. Refined AC: removed incorrect `_tool_manager._tools` line (those accesses are for outputSchema/param-patching, unrelated to TOOLS_EXCLUDE). Added explicit file targets for documentation cleanup. Scoped to pure deletion of one dead feature. Max td:1, challenger skipped.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_server_1199.py
- Classes: TestFromAC_FunctionRemoval, TestFromAC_LifespanCallRemoval, TestFromAC_OutputSchemaPreserved
- Tests per category: happy 0, edge 0, error 0, boundary 0 (td:1 only — smoke tests)
- Total: 3 tests, 2 FAIL (RED), 1 green by design (regression guard)
- ruff: clean

### AC Coverage
| AC line | Test | Status |
|---------|------|--------|
| `_apply_tool_exclusions` function removed (td:1) | `test_apply_tool_exclusions_not_in_server_module` | FAIL ✓ |
| `_apply_tool_exclusions` call removed from `app_lifespan` (td:1) | `test_lifespan_does_not_remove_tools_when_env_set` | FAIL ✓ |
| `_apply_tool_exclusions` removed from `__all__` (td:0) | skipped | td:0 |
| `KANBAN_TOOLS_EXCLUDE` removed from docs (td:0) | skipped | td:0 |
| `TestFromAC_ApplyToolExclusions` removed from test_server_1170.py (td:0) | skipped | td:0 |
| Server starts and registers all tools normally (td:1) | covered by `test_lifespan_does_not_remove_tools_when_env_set` | FAIL ✓ |
| outputSchema and `_patch_params` preserved (td:1) | `test_list_tasks_output_schema_is_patched` | GREEN (regression guard) |

### Notes
- `test_list_tasks_output_schema_is_patched` is intentionally green: it guards against the builder accidentally deleting the outputSchema block during cleanup. The preserved behavior already exists, so no RED state is possible without corrupting production code.
- The lifespan test (`test_lifespan_does_not_remove_tools_when_env_set`) covers both "call removed from lifespan" and "server starts normally" — with `KANBAN_TOOLS_EXCLUDE=list_tasks` set, the current code removes the tool; after deletion it won't.
[[2026-04-30]]
## Builder Notes
- Implementation: removed `KANBAN_TOOLS_EXCLUDE` capability from MCP kanban server by deleting `_apply_tool_exclusions`, removing its `app_lifespan` invocation, removing its `__all__` export, and dropping now-unused `os` import.
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/README.md`, `setup/setup-guide.md`, `share/skills/h-mcp-kanban/SKILL.md`, `share/skills/r-architecture-standards/SKILL.md`, `tests/test_server_1170.py`.
- Tests (RED before GREEN): quality-runner on `tests/test_server_1199.py` showed 2 failing `TestFromAC_*` tests pre-fix.
- Tests (GREEN): 262 passed, 0 failed on expanded scoped MCP server suite including `tests/test_server_1199.py` and `tests/test_server_1170.py`.
- Coverage: `owlbear_mcp_kanban.server` 95% (scoped quality-runner coverage_modules run).
- ruff: clean.
- Evidence summary: task AC targets are satisfied (function removed, lifespan call removed, export removed, docs references removed, legacy `TestFromAC_ApplyToolExclusions` class removed) while outputSchema patching and `_patch_params` behavior remain covered and green.
- Commit: `24aa8c23` (`refactor: remove kanban tool exclusion path (#1199, builder)`).

### Post-task Reflection
- Removing dead feature tests can lower module coverage unexpectedly; include durable server suites early in verification.
- Expanded scoped verification gave the needed coverage without modifying test-writer tests.
- Keep AC scoping strict for deletion tasks to avoid touching unrelated tool-manager metadata logic.
- Delegated git commands must avoid destructive resets; validate working tree state immediately after execution.

[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner scoped task suite (`tests/test_server_1199.py`, `tests/test_server_1170.py`): 68 passed, 0 failed, 0 skipped
- quality-runner durable metadata suite (`serve/mcp-kanban/tests/test_mcp_server_1090.py`): 3 passed, 0 failed, 0 skipped

### Lint
- scoped task suite: clean
- durable metadata suite: clean

### Coverage
- `owlbear_mcp_kanban.server`: 85% on the scoped task suite
- Informational only for this deletion task: module-level coverage is below 90%, but the gating issue is proof completeness on an explicit AC branch, not changed-line execution.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| `_apply_tool_exclusions` function removed from server.py | `tests/test_server_1199.py::TestFromAC_FunctionRemoval::test_apply_tool_exclusions_not_in_server_module` | Yes | COVERED |
| `_apply_tool_exclusions` call removed from `app_lifespan` | `tests/test_server_1199.py::TestFromAC_LifespanCallRemoval::test_lifespan_does_not_remove_tools_when_env_set` | Yes | COVERED |
| Server starts and registers all tools normally | `tests/test_server_1199.py::TestFromAC_LifespanCallRemoval::test_lifespan_does_not_remove_tools_when_env_set` | Yes | COVERED |
| Existing outputSchema and `_patch_params` functionality preserved - no regression in tool metadata | `tests/test_server_1199.py::TestFromAC_OutputSchemaPreserved::test_list_tasks_output_schema_is_patched` | No for the `_patch_params` half of the AC. The test proves `list_tasks` still has a non-None `output_schema`, but it would still pass if all `_patch_params` metadata patches were removed. | LAX |

#### Security Review
- No issues found. This is a deletion-only change with no new input boundary, dependency, filesystem path, or secret surface.

#### Test Integrity
- Current-task `TestFromAC_*` classes in `tests/test_server_1199.py` were preserved.
- The removal of legacy `TestFromAC_ApplyToolExclusions` from `tests/test_server_1170.py` is explicitly required by this task's AC and is treated as authorized cleanup, not as weakening of the current task's RED tests.

#### Test Quality
- Assertion specificity, independence, and naming are adequate for the deletion behavior.
- The metadata-preservation proof is insufficient: no executable assertion was found that would fail if `_patch_params` disappeared while `output_schema` remained intact.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:742-820` still defines `_patch_params` and applies it to `list_tasks`, `create_task`, `move_task`, `edit_task`, and `end_work`.
- Durable output-schema proof exists in `serve/mcp-kanban/tests/test_mcp_server_1090.py:208-228` and passes.
- I found no executable proof for the `_patch_params` side of the AC. Workspace searches for the patched description strings only matched the implementation in `server.py`; they did not locate a test assertion that would fail on metadata-patch removal.
- Because the AC explicitly preserves both `outputSchema` and `_patch_params`, this is a real proof gap, not a documentation nit.

#### Builder Process Quality
- CLEAN. One builder cycle documented.
- Builder commit `24aa8c23` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `_apply_tool_exclusions` function removed from server.py | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:53` starts `__all__`; exact search of `server.py` found no `_apply_tool_exclusions`. `tests/test_server_1199.py:35` asserts module attribute absence. | `test_apply_tool_exclusions_not_in_server_module` | PASS |
| `_apply_tool_exclusions` call removed from `app_lifespan` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:92-97` shows lifespan now only instantiates engine, calls `sweep()`, and yields context. `tests/test_server_1199.py:64` asserts `server.remove_tool` is never called even when env var is set. | `test_lifespan_does_not_remove_tools_when_env_set` | PASS |
| `_apply_tool_exclusions` removed from `__all__` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:53` plus exact search of the file found no `_apply_tool_exclusions`. | n/a (td:0) | PASS |
| `KANBAN_TOOLS_EXCLUDE` removed from product docs | `serve/mcp-kanban/README.md:106-108` now states board dir resolution with no MCP-level override. Exact searches of `serve/mcp-kanban/README.md`, `setup/setup-guide.md`, `share/skills/h-mcp-kanban/SKILL.md`, and `share/skills/r-architecture-standards/SKILL.md` found no `KANBAN_TOOLS_EXCLUDE`. | n/a (td:0) | PASS |
| `TestFromAC_ApplyToolExclusions` test class removed from `test_server_1170.py` | Exact search of `tests/test_server_1170.py` found no `TestFromAC_ApplyToolExclusions`. | n/a (td:0) | PASS |
| Server starts and registers all tools normally | `tests/test_server_1199.py:64` proves `app_lifespan` does not remove `list_tasks` even when the old env var is set; scoped quality-runner suite passed 68/68. | `test_lifespan_does_not_remove_tools_when_env_set` | PASS |
| Existing outputSchema and `_patch_params` functionality preserved - no regression in tool metadata | `tests/test_server_1199.py:77-90` and `serve/mcp-kanban/tests/test_mcp_server_1090.py:208-228` prove `output_schema` preservation. `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:742-820` shows `_patch_params` code still exists, but no test was found that would fail if those parameter metadata patches were removed. | `test_list_tasks_output_schema_is_patched`; `test_list_tasks_output_schema_equals_model_json_schema` | FAIL |

### Deductions
- 0.10 deducted: explicit AC branch for `_patch_params` preservation lacks executable proof.
- 0.04 deducted: scoped module coverage is 85%, which increases reliance on code inspection for metadata behavior.

### Verdict
- FAIL -> todo
- Confidence: 0.86

### Required Follow-up
- Add a regression test that inspects MCP tool parameter metadata and would fail if `_patch_params` were removed or drifted. A minimal acceptable proof would assert at least one patched enum and one patched description, for example:
  - `move_task.parameters["properties"]["status"]["enum"]` includes the expected statuses
  - `edit_task.parameters["properties"]["append_body"]["description"]` matches the patched help text
- Re-run the task-owned suite and the durable metadata suite after adding that proof.

### Action
- Rejected to `todo` for test-only follow-up. No implementation defect was verified in the current code.
[[2026-04-30]]
## Test-Writer Notes
- Retry: added 1 test (`test_patch_params_applies_enum_and_description`) to `TestFromAC_OutputSchemaPreserved` in `tests/test_server_1199.py`.
- Reviewer gap filled: explicit assertion that `_patch_params` metadata survives — `move_task.status.enum` includes "archived", `edit_task.append_body.description` matches patched text exactly.
- All NEW tests PASS against current code (`_patch_params` already exists). Builder skip: test-only retry, all 5 tests green.
- ruff: clean.
- Commit: `e396de89` (`test: add _patch_params regression proof (#1199, test-writer)`).
[[2026-04-30]]
## Builder Notes
- Verification-only builder cycle after test-writer retry commit `e396de89`; no source or test files were edited in this pass.
- RED verification context: task body documents prior RED failures for `TestFromAC_FunctionRemoval` and `TestFromAC_LifespanCallRemoval` before the earlier builder implementation.
- GREEN verification (quality-runner, expanded scoped suite): 224 passed, 0 failed, 0 skipped.
- Coverage: `owlbear_mcp_kanban.server` 90% (meets task gate).
- Lint: ruff clean on scoped MCP server/task files.
- Evidence summary: AC proof now includes explicit `_patch_params` regression assertions in `tests/test_server_1199.py` and all scoped durable MCP suites remain green.

### Post-task Reflection
- Narrow scoped runs can underreport target-module coverage; durable MCP suites are required for realistic gate evidence.
- For retry loops with test-only follow-up, builder work can be pure verification while still producing strong closure evidence.
- Keeping coverage_modules focused on the touched contract (`owlbear_mcp_kanban.server`) avoids noise from unrelated package coverage.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner scoped suites: 72 passed, 0 failed, 0 skipped
- Scope reviewed: `tests/test_server_1199.py`, `tests/test_server_1170.py`, `serve/mcp-kanban/tests/test_mcp_server_1090.py`

### Lint
- ruff clean on `serve/mcp-kanban/src/`, `tests/test_server_1199.py`, `tests/test_server_1170.py`, and `serve/mcp-kanban/tests/test_mcp_server_1090.py`

### Coverage
- `owlbear_mcp_kanban.server`: 85%
- Informational only: module-level coverage is below 90% in this scoped run, but this task is a deletion with preserved import-time metadata behavior proved by executable assertions on the live MCP tool objects.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| `_apply_tool_exclusions` function removed from server.py | `tests/test_server_1199.py::TestFromAC_FunctionRemoval::test_apply_tool_exclusions_not_in_server_module` | Yes. The test fails immediately if the module still exports the helper. | COVERED |
| `_apply_tool_exclusions` call removed from `app_lifespan` | `tests/test_server_1199.py::TestFromAC_LifespanCallRemoval::test_lifespan_does_not_remove_tools_when_env_set` | Yes. The test sets the old env var and fails if `server.remove_tool()` is still reached. | COVERED |
| Server starts and registers all tools normally | `tests/test_server_1199.py::TestFromAC_LifespanCallRemoval::test_lifespan_does_not_remove_tools_when_env_set`; `tests/test_server_1170.py::TestFromAC_AppLifespan::test_lifespan_yields_app_context_with_swept_engine`; `serve/mcp-kanban/tests/test_mcp_server_1090.py::TestFromAC_OutputSchema::test_list_tasks_output_schema_equals_model_json_schema` | Yes. These checks prove lifespan still yields a valid app context, does not remove tools when the retired env var is set, and still exposes the registered `list_tasks` tool with the expected schema. | COVERED |
| Existing outputSchema and `_patch_params` functionality preserved, with no regression in tool metadata | `tests/test_server_1199.py::TestFromAC_OutputSchemaPreserved::test_list_tasks_output_schema_is_patched`; `tests/test_server_1199.py::TestFromAC_OutputSchemaPreserved::test_patch_params_applies_enum_and_description`; `serve/mcp-kanban/tests/test_mcp_server_1090.py::TestFromAC_OutputSchema::test_list_tasks_output_schema_equals_model_json_schema` | Yes. Removing the output schema patch breaks the schema assertions; removing `_patch_params` or its call sites breaks the enum and description assertions. | COVERED |

#### Security Review
- No issues found. This is a deletion-only change with no new dependency, boundary, secret surface, filesystem path, or execution sink.

#### Test Integrity
- Current-task `TestFromAC_*` coverage in `tests/test_server_1199.py` is preserved.
- The retry added a stronger `_patch_params` proof without weakening existing assertions.
- No builder-authored weakening or removal of current-task `TestFromAC_*` coverage was found.

#### Test Quality
- PASS. Assertions are specific and mutation-resistant for the task scope.
- The `_patch_params` retry test now checks both a patched enum (`move_task.status`) and an exact patched description (`edit_task.append_body`), which closes the earlier proof gap.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- No significant untested path remains inside the AC boundary.
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:92` shows `app_lifespan` now only instantiates `KanbanEngine`, calls `sweep()`, and yields `AppContext`.
- Exact searches found no `_apply_tool_exclusions` symbol in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, no `remove_tool` call in that file, and no `TestFromAC_ApplyToolExclusions` class in `tests/test_server_1170.py`.
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:742`, `:783`, and `:794` still define and apply `_patch_params`; the retry test suite proves those live metadata patches are observable on the registered MCP tools.

#### Builder Process Quality
- CLEAN. One earlier review rejection documented a proof gap, and the retry addressed that exact gap with stronger task-owned assertions.
- Builder commit `24aa8c23` and retry test-writer commit `e396de89` are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- This did not enter a repeated builder loop.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `_apply_tool_exclusions` function removed from server.py | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:53` begins `__all__`; exact search of the file found no `_apply_tool_exclusions`. `tests/test_server_1199.py:29` asserts the module no longer has that attribute. | `test_apply_tool_exclusions_not_in_server_module` | PASS |
| `_apply_tool_exclusions` call removed from `app_lifespan` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:92` defines `app_lifespan`; exact search found no `remove_tool` call in the file. `tests/test_server_1199.py:49` proves the retired env var no longer removes tools. | `test_lifespan_does_not_remove_tools_when_env_set` | PASS |
| `_apply_tool_exclusions` removed from `__all__` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:53` through the export list contains no `_apply_tool_exclusions`; exact search of the file found no symbol. | n/a (td:0) | PASS |
| `KANBAN_TOOLS_EXCLUDE` removed from product docs: README.md, setup-guide.md, h-mcp-kanban SKILL.md, r-architecture-standards SKILL.md | `serve/mcp-kanban/README.md:108` now states no MCP-level override is supported. Exact searches found no `KANBAN_TOOLS_EXCLUDE` in `serve/mcp-kanban/README.md`, `setup/setup-guide.md`, `share/skills/h-mcp-kanban/SKILL.md`, or `share/skills/r-architecture-standards/SKILL.md`. | n/a (td:0) | PASS |
| `TestFromAC_ApplyToolExclusions` test class removed from `test_server_1170.py` | Exact search of `tests/test_server_1170.py` found no `TestFromAC_ApplyToolExclusions`. The current lifespan regression class begins at `tests/test_server_1170.py:170`. | n/a (td:0) | PASS |
| Server starts and registers all tools normally | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:92` defines a minimal lifespan with engine init, `sweep()`, and yield only. `tests/test_server_1170.py:174` proves the yielded context and `sweep()` call. `tests/test_server_1199.py:49` proves the retired env var no longer removes a tool. `serve/mcp-kanban/tests/test_mcp_server_1090.py:208` proves `list_tasks` remains registered with the expected output schema. | `test_lifespan_does_not_remove_tools_when_env_set`; `test_lifespan_yields_app_context_with_swept_engine`; `test_list_tasks_output_schema_equals_model_json_schema` | PASS |
| Existing outputSchema and `_patch_params` functionality preserved, with no regression in tool metadata | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:742` defines `_patch_params`; `:783` patches `move_task.status` with `archived`; `:794` patches `edit_task.append_body` description. `tests/test_server_1199.py:77` proves `list_tasks` keeps a custom output schema, `tests/test_server_1199.py:94` proves the patched enum and description are still present, and `serve/mcp-kanban/tests/test_mcp_server_1090.py:208` proves exact output schema equality. | `test_list_tasks_output_schema_is_patched`; `test_patch_params_applies_enum_and_description`; `test_list_tasks_output_schema_equals_model_json_schema` | PASS |

### Deductions
- 0.04 deducted: module-level coverage for the scoped run is 85%, so confidence still relies partly on direct code inspection. This is non-blocking because the deletion boundary and preserved metadata side effects are both covered by executable proofs.

### Verdict
- PASS
- Confidence: 0.94

### Action
- Advanced to docs.

### Post-task Reflection
- Deletion tasks that touch import-time schema patching need executable metadata assertions, not only a non-None schema check.
- Exact no-match searches are useful evidence for AC lines that require removal of symbols or documentation text.
- Module-level coverage can understate confidence on deletion work; the key gate is whether the preserved side effects are still provably observable.
[[2026-04-30]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | `serve/mcp-kanban/README.md` and `setup/setup-guide.md` — exact searches found no `KANBAN_TOOLS_EXCLUDE` in either file; builder already removed all references. No further prose edits needed. |
| 2 | Module docstrings | Yes | Verified | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — searched for `KANBAN_TOOLS_EXCLUDE`, `_apply_tool_exclusions`, `tool exclusion` in docstrings; zero matches. No stale docstring references remain. |
| 3 | External attribution | No | N/A | Pure deletion task; no external patterns used. |
| 4 | Research doc | No | N/A | No research phase for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` describes `serve/mcp-kanban/src/**` — matches. `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — matches. Both footers updated from `567f19fa` → `743dbc36` (2026-04-30). |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | `_apply_tool_exclusions` was deleted from within `server.py` (not a file deletion). All IN-scope docs referencing this feature were already cleaned by the builder. No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | IN (docstrings) | Verified — no stale docstrings |
| `serve/mcp-kanban/README.md` | IN | Verified — `KANBAN_TOOLS_EXCLUDE` already removed |
| `setup/setup-guide.md` | IN | Verified — `KANBAN_TOOLS_EXCLUDE` already removed |
| `share/skills/h-mcp-kanban/SKILL.md` | OUT (agent-executable) | No action |
| `share/skills/r-architecture-standards/SKILL.md` | OUT (agent-executable) | No action |
| `tests/test_server_1170.py` | OUT (test file) | No action |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer updated to `2026-04-30 (743dbc36)`
- `share/diagrams/mcp-topology.excalidraw` — footer updated to `2026-04-30 (743dbc36)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `_apply_tool_exclusions` function removed from server.py | grep of serve/mcp-kanban/src/ found no match; reviewer confirmed at server.py:53 | PASS |
| `_apply_tool_exclusions` call removed from `app_lifespan` | reviewer confirmed server.py:92 lifespan is engine-init + sweep + yield only | PASS |
| `_apply_tool_exclusions` removed from `__all__` | reviewer confirmed no symbol in file | PASS |
| `KANBAN_TOOLS_EXCLUDE` removed from product docs | reviewer exact-searched 4 files, zero matches | PASS |
| `TestFromAC_ApplyToolExclusions` removed from test_server_1170.py | reviewer confirmed no match | PASS |
| Server starts and registers all tools normally | test_lifespan_does_not_remove_tools_when_env_set passes; full suite 3333 green in mcp-kanban scope | PASS |
| outputSchema and `_patch_params` preserved | test_patch_params_applies_enum_and_description (retry commit e396de89) proves patched enum + description | PASS |

### Test Results
- pytest full suite: 3333 passed, 73 failed, 4 skipped (exit 1)
- Task-scope failures: 0 (all 73 failures in unrelated packages: kanban engine 1068, storage 1050, cockpit 1015)
- ruff: 4 violations, all in unrelated packages (knowledge, mcp-memory, orchestrator). Task scope clean.

### Architect Quality: 5/5
AC was specific (exact function names, files, behaviors), correctly scoped preservation targets, and precise enough to drive a productive review rejection when proof was missing for `_patch_params`.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 have specific evidence)
- Lint violations in scope: 0
- AC quality deduction: 0 (score 5)
- Missing reviewer evidence: 0 (two thorough review cycles)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Agent |
|--------|------|-------|
| 24aa8c23 | refactor | builder |
| e396de89 | test | test-writer |