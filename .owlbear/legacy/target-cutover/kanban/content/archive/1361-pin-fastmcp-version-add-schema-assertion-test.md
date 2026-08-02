---
id: 1361
title: Pin FastMCP version + add schema assertion test
status: archived
priority: medium
created: 2026-05-05T23:34:57.032184+00:00
updated: 2026-05-06T00:52:24.641062+00:00
tags:
- kanban
- stability
- deploy-prep
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Pin FastMCP dependency with an upper bound and add an integration test that validates the monkey-patched schema fields still exist after import.

## AC

- [ ] `pyproject.toml` for `serve/mcp-kanban` pins FastMCP with upper bound (e.g. `fastmcp>=2.0,<3.0`)
- [ ] Test asserts: all 5 mutation tools have `outputSchema` set to `SingleTaskResponse` schema
- [ ] Test asserts: `list_tasks` has `outputSchema` set to `ListTasksResponse` schema
- [ ] Test asserts: patched parameter descriptions/enums are present for `list_tasks`, `create_task`, `move_task`, `edit_task`, `end_work`
- [ ] Test fails clearly if FastMCP internals change (catches breakage at upgrade time)

## Context

Audit Finding Group 7. The MCP server accesses `mcp._tool_manager._tools` (private API) in 3 places to customize schemas. This works with current FastMCP but could break silently on upgrade.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_mcp_schema_assertion_1361.py
- Classes: TestFromAC_DependencyVersionPin, TestFromAC_MutationToolOutputSchema, TestFromAC_ListTasksOutputSchema, TestFromAC_PatchedParameterDescriptions
- Tests per category: happy 0, edge 0, error 0, boundary 1 (version spec); regression guards 27
- Total: 28 tests

**RED verification:**
- `TestFromAC_DependencyVersionPin::test_mcp_dependency_has_upper_bound` → FAIL ✓  
  (`AssertionError: MCP dependency 'mcp[cli]>=1.27.0' must include an upper bound`)
- All 27 AC2–AC4 tests → PASS (monkey-patching implementation already exists in server.py)

**AC2–AC4 note:** The schema assertions and param-description tests pass immediately because the monkey-patching in `server.py` already sets `fn_metadata.output_schema` and patches `tool.parameters['properties']`. Per w-tdd-red these would normally be removed, but the AC explicitly requires them as regression guards ("test fails clearly if FastMCP internals change"). They are kept as-is; the builder's only remaining action is AC1 (pin the dep).

**Builder scope:** Add upper bound to `mcp[cli]` in `serve/mcp-kanban/pyproject.toml` (e.g. `mcp[cli]>=1.27.0,<2.0`) to make `test_mcp_dependency_has_upper_bound` pass.

- ruff: clean
[[2026-05-05]]
## Builder Notes
- Implementation: updated dependency bound in serve/mcp-kanban/pyproject.toml (`mcp[cli]>=1.27.0,<2.0`).
- Files changed: serve/mcp-kanban/pyproject.toml
- Tests: 28 passed / 0 failed (`tests/test_mcp_schema_assertion_1361.py`)
- Coverage: 25% on `owlbear_mcp_kanban.server` in scoped run (task is dependency-pin + regression guard assertions; no server logic changes).
- ruff: clean (0 violations) for `serve/mcp-kanban/src/owlbear_mcp_kanban/` and `tests/test_mcp_schema_assertion_1361.py`.
- Evidence summary: RED had exactly 1 failure (`test_mcp_dependency_has_upper_bound`), GREEN passed after one-line dependency pin.
- Fixes applied: removed unbounded `mcp[cli]>=1.27.0` and pinned with upper bound to guard FastMCP upgrade breakage.

## Post-task Reflection
- Problem faced: initial patch briefly introduced duplicate `dependencies` key in TOML.
- Workaround applied: immediate surgical correction to a single canonical `dependencies` entry.
- Pattern discovered: task-writer regression guards can be mostly-green by design; builder should target only the remaining failing AC.
- Quality gap: coverage on broad server module is low for this narrowly scoped dependency-pin task, but scoped AC assertions are fully green.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped pytest: 28 passed, 0 failed, 0 skipped for `tests/test_mcp_schema_assertion_1361.py`.
- quality-runner scoped ruff: clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/` and `tests/test_mcp_schema_assertion_1361.py`.
- VS Code diagnostics: no errors in `serve/mcp-kanban/pyproject.toml`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, or `tests/test_mcp_schema_assertion_1361.py`.

### Coverage Data
- quality-runner scoped coverage on `owlbear_mcp_kanban.server`: 29% module coverage, 19% overall run coverage.
- Non-blocking. The builder-scoped change is the dependency pin in `serve/mcp-kanban/pyproject.toml`; no `owlbear_mcp_kanban.server` lines were modified in the builder note scope, so module-level coverage is informational only under the diff-scoped rule.

### Source-Control Evidence
- Task-related commits are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`:
  - `0538b2a3e911b5d929837a8d7c50d72f50789f3a` — `test: add schema assertion + version-pin tests for mcp-kanban (#1361, test-writer)`
  - `c377940da31b9db22e7df1cdb4c6a224a036e462` — `fix: pin mcp upper bound (#1361, builder)`
- Direct `git show` / `git status` execution was unavailable in this session, so full changed-file diff reconstruction, dirty-tree contamination checking, and TestFromAC immutability verification are lower-confidence than normal.

### Test Integrity And Quality
- AC1 proof is discriminating: `tests/test_mcp_schema_assertion_1361.py:75` asserts every MCP/FastMCP dependency spec contains an upper bound and fails with a clear remediation message when missing.
- AC2 proof is discriminating: `tests/test_mcp_schema_assertion_1361.py:136` compares each mutation tool's `fn_metadata.output_schema` to `SingleTaskResponse.model_json_schema()` for exact equality, matching the runtime monkey-patch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:548`.
- AC3 proof is discriminating: `tests/test_mcp_schema_assertion_1361.py:181` compares `list_tasks.fn_metadata.output_schema` to `ListTasksResponse.model_json_schema()` exactly, matching the runtime registration at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:233`.
- AC4 proof is adequate and direct: the suite inspects `tool.parameters['properties']` through `_get_tool_props()` (`tests/test_mcp_schema_assertion_1361.py:52`) and verifies patched description/enum fields across the named tools (`tests/test_mcp_schema_assertion_1361.py:230`, `:254`, `:274`, `:284`, `:338`) against the patch surface at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:558-635`.
- AC5 regression guard is explicit: the tests intentionally dereference the private FastMCP path `mcp._tool_manager._tools` (`tests/test_mcp_schema_assertion_1361.py:39`) plus `fn_metadata.output_schema` and `tool.parameters['properties']`, so FastMCP internal breakage fails loudly rather than silently.
- No lazy assertions, weakened checks, security findings, or builder-loop issues found. Builder process quality is CLEAN (single builder cycle, no prior `## Review Evidence` section).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `pyproject.toml` for `serve/mcp-kanban` pins FastMCP with upper bound | `serve/mcp-kanban/pyproject.toml:6` contains `mcp[cli]>=1.27.0,<2.0`; enforced by `tests/test_mcp_schema_assertion_1361.py:75` | `TestFromAC_DependencyVersionPin::test_mcp_dependency_has_upper_bound` | PASS |
| All 5 mutation tools have `outputSchema` set to `SingleTaskResponse` schema | Runtime patch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:548`; exact-equality assertion at `tests/test_mcp_schema_assertion_1361.py:136` | `TestFromAC_MutationToolOutputSchema::test_mutation_tool_output_schema_equals_single_task_response` | PASS |
| `list_tasks` has `outputSchema` set to `ListTasksResponse` schema | Runtime patch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:233`; exact-equality assertion at `tests/test_mcp_schema_assertion_1361.py:181` | `TestFromAC_ListTasksOutputSchema::test_list_tasks_output_schema_equals_list_tasks_response` | PASS |
| Patched parameter descriptions/enums are present for `list_tasks`, `create_task`, `move_task`, `edit_task`, `end_work` | Patch surface at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:558-635`; direct property assertions at `tests/test_mcp_schema_assertion_1361.py:230`, `:254`, `:274`, `:284`, `:338` | `TestFromAC_PatchedParameterDescriptions` representative assertions | PASS |
| Test fails clearly if FastMCP internals change | Private-API regression guard in `tests/test_mcp_schema_assertion_1361.py:39`, `:52`, `:125-150`, `:172-191`; runtime depends on same private surfaces at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:230`, `:545`, `:563-564` | Helper + schema assertion tests | PASS |

### Deductions
- `-0.03` Dirty-tree contamination check could not be executed because terminal/git commands were unavailable in this session.
- `-0.02` TestFromAC immutability could not be fully verified via commit diff; commit presence was confirmed from `.git/logs/**` only.

### Verdict
- PASS
- Confidence: 0.95
- Action: advance to `docs`.

### Post-task Reflection
- Problem faced: no direct terminal/git execution tool was available for the normal `git show` / `git status` review steps.
- Workaround applied: confirmed task-specific commit presence from `.git/logs/**` and anchored AC proof with direct file reads plus independent quality-runner passes.
- Pattern discovered: for dependency-pin tasks backed by pre-existing regression guards, module-level coverage can stay low while diff-scoped proof remains strong because no source module lines changed.
- Quality gap: source-control integrity checks are lower-confidence without direct diff/status access, even when the code and task-scoped evidence are clean.
[[2026-05-06]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/mcp-kanban/README.md` Dependencies table lists `mcp[cli]` with no version column — task only added upper bound in pyproject.toml; no prose doc update needed |
| 2 | Module docstrings | No | N/A | No Python source modules modified; only `serve/mcp-kanban/pyproject.toml` changed |
| 3 | External attribution | No | N/A | No external patterns used (pure dependency pin) |
| 4 | Research doc | No | N/A | No research phase for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/mcp-kanban/src/**`; changed file `pyproject.toml` is not under `src/` — no match. `mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — same, no match |
| 6 | Explicit diagram creation | No | N/A | Not requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/pyproject.toml | OUT (config, not a doc) | N/A |
| tests/test_mcp_schema_assertion_1361.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task 1361)
[[2026-05-06]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pyproject.toml pins FastMCP with upper bound | serve/mcp-kanban/pyproject.toml:6 contains mcp[cli]>=1.27.0,<2.0; enforced by test_mcp_dependency_has_upper_bound | PASS |
| All 5 mutation tools have outputSchema set to SingleTaskResponse | test_mutation_tool_output_schema_equals_single_task_response passes (exact equality assertion) | PASS |
| list_tasks has outputSchema set to ListTasksResponse | test_list_tasks_output_schema_equals_list_tasks_response passes (exact equality assertion) | PASS |
| Patched param descriptions/enums present for named tools | TestFromAC_PatchedParameterDescriptions suite passes (direct property assertions) | PASS |
| Test fails clearly if FastMCP internals change | Tests dereference private mcp._tool_manager._tools and fn_metadata.output_schema; breakage fails loudly | PASS |

### Test Results
- pytest (task-scoped): 28 passed, 0 failed
- pytest (full suite): 2585 passed, 295 failed (all failures in unrelated test files: memory models, cockpit read API, engine migration, etc. Zero failures in mcp-kanban scope)
- ruff: clean for task files

### Architect Quality: 4/5
AC lines are specific and testable with clear enumeration of tools. One line ("Test fails clearly if FastMCP internals change") is slightly abstract but test-writer interpreted it reasonably.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 5 verified)
- Lint violations in task scope: 0
- AC quality score 4 (above 3 threshold): 0
- Reviewer evidence section: present, detailed, PASS verdict
- Full-suite task-scope failures: 0
- No deductions applied

### Confidence: 1.00
### Action: archive

### Commits Verified
- 0538b2a3 test: add schema assertion + version-pin tests for mcp-kanban (#1361, test-writer)
- c377940d fix: pin mcp upper bound (#1361, builder)
- Working tree clean for task files (git status confirms no uncommitted changes)