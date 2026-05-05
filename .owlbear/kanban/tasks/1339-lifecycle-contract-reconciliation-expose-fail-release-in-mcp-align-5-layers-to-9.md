---
id: 1339
title: Reconcile MCP lifecycle tools, guidance, and 9-tool contract
status: review
priority: needed
created: 2026-05-04T15:00:05.806598+00:00
updated: 2026-05-05T10:59:19.155709+00:00
tags:
- sync-blocker
- mcp-kanban
- docs
parent:
depends_on:
- 1343
- 1349
blocked: false
block_reason:
claimed_at: 2026-05-05T10:59:19.155709+00:00
archival_reason:
archival_refs: []
---

## Context

Engine, AgentView, MCP, handbook, README, guidance text, and parameter metadata disagree about lifecycle outcomes and the MCP tool surface. The deployment contract is now confirmed: MCP exposes 9 tools including `create_dr`, and `end_work` supports five outcomes: `success`, `fail`, `reject`, `block`, and `release`.

Decision: expose both `fail` (records failure and releases work) and `release` (silent unclaim) in MCP.

## Acceptance Criteria

1. MCP `end_work` handler accepts `outcome="fail"` and routes to the existing failure lifecycle path.
2. MCP `end_work` handler accepts `outcome="release"` and routes to task claim release without recording failure.
3. MCP server schema/metadata names all five outcomes: `success`, `fail`, `reject`, `block`, `release`.
4. `share/skills/h-mcp-kanban/SKILL.md` lists 9 tools and includes `create_dr` in the tool table.
5. `share/skills/h-mcp-kanban/SKILL.md` documents all five `end_work` outcomes with concise use-when guidance.
6. `serve/mcp-kanban/README.md` matches the 9-tool and 5-outcome contract.
7. `AgentView._BLOCK_AR_HINT` and MCP guidance text refer to the canonical `create_dr` tool, not the stale `scribe agent` wording.
8. MCP parameter metadata patches match actual tool signatures; remove stale/nonexistent patched params and document JSON arrays as arrays, not comma-separated strings.
9. MCP status and priority metadata is either derived from board config or intentionally schema-light; no stale hard-coded `_STATUSES` / `_PRIORITIES` lists can drift from live board config.
10. The lifecycle parameter matrix is explicit and consistent across code, tests, README, and handbook, including the currently tested behavior that valid `success + move_to` is accepted unless a new decision deliberately changes that contract.
11. Tests prevent false greens from generic substring matches such as bare `fail` appearing in unrelated failure prose.
12. Existing MCP behavior tests pass after contract reconciliation.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `share/skills/h-mcp-kanban/SKILL.md`
- `serve/mcp-kanban/README.md`
- `tests/test_mcp_end_work_fail_1339.py`

## Audit Evidence

- Live MCP server exposes 9 tools, but the handbook still says 8.
- `EndWorkParams` includes `fail`, but the server tool signature omits it.
- Guidance has already moved toward `create_dr`, while `AgentView._BLOCK_AR_HINT` still mentions the scribe agent.
- Parameter metadata patches still describe older tool params that no longer match the live signatures.
- MCP server metadata currently hard-codes status and priority vocabulary even though the kanban board config is the authority.
- Existing tests/prose conflict around `success + move_to`; newer tests allow valid `move_to`, while older language implies stricter behavior.

## Test-Writer Notes

Existing RED file: `tests/test_mcp_end_work_fail_1339.py`.

Keep table/section tests specific. For example, a documentation test for `fail` should match a table row or explicit outcome section, not any occurrence of the substring in failure-handling prose.

## Source

Deployment audit reconciliation, 2026-05-04.
[[2026-05-05]]


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes serve one goal: reconcile MCP lifecycle contract across 5 layers |
| Interface clarity | PASS | AC lines name exact files, constants, and expected values |
| Dependency correctness | PASS | 1343 and 1349 archived (done) |
| Module layering | PASS | mcp-kanban → kanban dependency direction respected; _BLOCK_AR_HINT is lifecycle surface |
| TDD compliance | PASS | RED tests exist in `tests/test_mcp_end_work_fail_1339.py` (AC1-6) and `tests/test_guidance_text_1183.py` (AC7) |
| KISS/YAGNI | PASS | Each change justified by audit evidence; no speculative additions |
| Premise challenge | PASS | Real drift confirmed: server Literal has 4 values, SKILL.md says 8 tools, _BLOCK_AR_HINT stale |
| Pattern consistency | PASS | Follows existing _patch_params pattern and MCP tool conventions |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | MCP kanban lifecycle domain (feature-coupled packages in explicit dependency chain) |

### Challenge Results

- Challenger: reconsider (0.44 confidence)
- Architect response: rebutted — challenger was factually wrong about SKILL.md state (still says 8, not 9), mischaracterized AC10 as contradiction (AC text explicitly resolves it), and invalid cross-package concern (explicit dependency). Valid point about README bare-substring tests is already addressed by AC11.

### Test Depth

- AC1: `(td:2)` — new code path + schema + routing
- AC2: `(td:1)` — regression guard
- AC3: `(td:1)` — schema check
- AC4: `(td:1)` — doc content test
- AC5: `(td:1)` — doc content test
- AC6: `(td:1)` — doc content test
- AC7: `(td:1)` — text constant change (covered by test_guidance_text_1183.py)
- AC8: `(td:1)` — remove stale params, verify no runtime error
- AC9: `(td:1)` — design choice: builder documents approach taken
- AC10: `(td:1)` — consistency check, maintain tested success+move_to behavior
- AC11: `(td:2)` — test quality; README tests must use specific matchers not bare substring
- AC12: `(td:0)` — builder exit gate (run existing suite)
- Max depth: 2
- Test-writer: PROCEED

### Builder Guidance

- AC1: Add `"fail"` to `end_work` outcome `Literal` in server.py (line ~577). Routing already works via `_invoke_view_end_work`.
- AC7: Update `AgentView._BLOCK_AR_HINT` in `agent_view.py` L46-49 to match `guidance.py`'s `_DR_REQUIRED_MSG` canonical text.
- AC8: Remove stale `_patch_params` entries for edit_task (`"block"`, `"tags"`, `"status"`, `"depends_on"`) and create_task (`"status"`). Fix `depends_on`/`tags` descriptions: replace "Comma-separated" with "JSON array of IDs/strings".
- AC9: The `_STATUSES`/`_PRIORITIES` hard-coded lists (server.py L687-688) run at import time before the engine exists. Simplest fix: remove enum hints entirely from patches (schema-light approach) since agents get validation errors with valid values from the engine. Document choice in end_work note.
- AC11: The README assertions in `test_mcp_end_work_fail_1339.py` (lines ~321, 331) use bare `"fail" in section.lower()` — tighten to table-row or bullet-list matchers consistent with the SKILL.md tests.

### Verdict: APPROVE
### Action Taken: Approved with test-depth annotations and builder guidance. Moving to todo.
[[2026-05-05]]
Architecture review complete. All 10 criteria PASS. Challenger rebutted (factual errors on SKILL.md state, invalid cross-package claim). Approved with td annotations and builder guidance for AC1/7/8/9/11.
[[2026-05-05]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_end_work_fail_1339.py`

**AC3 note:** Pre-satisfied — `owlbear-dev` SKILL.md already says "9 tools" and has `create_dr` row. Two passing AC3 tests removed per RED-phase rules.

### Tests added this session (AC8/9/10)

| Class | Tests | Category |
|-------|-------|----------|
| `TestFromAC_PatchParamsJsonArrayDoc` | 4 | boundary — description quality |
| `TestFromAC_SchemaLight` | 2 | error — stale enum constraints |
| `TestFromAC_OutcomeDescriptionConsistency` | 2 | error — missing outcome in description |

### Full test inventory (18 tests, all FAIL)

| Class | Tests | AC | Status |
|-------|-------|----|--------|
| `TestFromAC_EndWorkFailOutcome` | 2 | AC1 | FAIL ✅ |
| `TestFromAC_EndWorkOutcomeSpec` | 2 | AC1+2 | FAIL ✅ |
| `TestFromAC_SkillDocEndWorkOutcomes` | 3 | AC4 | FAIL ✅ |
| `TestFromAC_ReadmeEndWorkOutcomes` | 3 | AC5 | FAIL ✅ |
| `TestFromAC_PatchParamsJsonArrayDoc` | 4 | AC8 | FAIL ✅ |
| `TestFromAC_SchemaLight` | 2 | AC9 | FAIL ✅ |
| `TestFromAC_OutcomeDescriptionConsistency` | 2 | AC10 | FAIL ✅ |

**Total: 18 tests, 18 FAIL, 0 PASS** (pytest 0.84s)
**Ruff:** clean

### AC coverage table

| AC | Tests | Coverage |
|----|-------|----------|
| AC1 | 4 (EndWorkFailOutcome + EndWorkOutcomeSpec) | "fail" in Literal; exactly 5 values |
| AC2 | 2 (EndWorkOutcomeSpec) | "release" retained; set of 5 check |
| AC3 | — | Pre-satisfied; no tests needed |
| AC4 | 3 (SkillDocEndWorkOutcomes) | SKILL.md end_work table has all 5 outcome rows |
| AC5 | 3 (ReadmeEndWorkOutcomes) | README.md end_work section has all 5 outcomes |
| AC6 | — | README already has 9 tools + create_dr; pre-satisfied |
| AC7 | — | Covered by `tests/test_guidance_text_1183.py` (existing RED) |
| AC8 | 4 (PatchParamsJsonArrayDoc) | depends_on/tags/add_dep/remove_dep use JSON array not comma-separated |
| AC9 | 2 (SchemaLight) | list_tasks.status/priority have no hard-coded enum constraints |
| AC10 | 2 (OutcomeDescriptionConsistency) | outcome description mentions all 5 outcomes including "release" |
| AC11 | — | Already addressed in existing tests via table-row matchers |
| AC12 | — | Builder exit gate (td:0) |

### Builder guidance reminders

- AC1: Add `"fail"` to `end_work` outcome Literal in `server.py` L601
- AC8: Change "Comma-separated" → "JSON array of IDs/strings" in `_patch_params` for create_task (depends_on, tags) and edit_task (add_dep, remove_dep)
- AC9: Remove `"enum": _STATUSES` and `"enum": _PRIORITIES` from `list_tasks` _patch_params
- AC10: Update `end_work` `outcome` description in `_patch_params` to include all 5 outcomes including "release"
[[2026-05-05]]
## Builder Notes
- Files changed:
  - `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
  - `serve/kanban/src/owlbear_kanban/agent_view.py`
  - `share/skills/h-mcp-kanban/SKILL.md`
  - `serve/mcp-kanban/README.md`
- AC implementation summary:
  - Added `fail` to `end_work` outcome type contract (`Literal["success", "fail", "reject", "block", "release"]`).
  - Reconciled MCP parameter metadata with live signatures and schema-light policy.
  - Removed stale hard-coded `_STATUSES` / `_PRIORITIES` enum patching from metadata to avoid drift from board config.
  - Updated array-typed parameter descriptions to use JSON-array wording (`depends_on`, `tags`, `add_dep`, `remove_dep`).
  - Updated `end_work.outcome` description to include all five lifecycle outcomes including `release`.
  - Updated `AgentView._BLOCK_AR_HINT` to canonical `create_dr` tool wording.
  - Updated handbook + README lifecycle outcome docs to include `fail` with concise use-when behavior.
- RED verification (quality-runner, scoped):
  - `tests/test_mcp_end_work_fail_1339.py`: 18 failed / 0 passed (expected RED baseline).
- GREEN verification (quality-runner, scoped):
  - `tests/test_mcp_end_work_fail_1339.py` + `tests/test_guidance_text_1183.py`: 22 passed, 0 failed.
- Regression verification (quality-runner, scoped):
  - `tests/test_mcp_kanban.py`: 63 passed, 0 failed.
- Lint status:
  - Ruff clean on changed Python/test files.
- Coverage evidence:
  - Scoped regression run reported `owlbear_mcp_kanban.server` at 90%.
  - `owlbear_kanban.agent_view` remains low in scoped coverage due module breadth; no tests were modified by builder per protocol.
- Notes:
  - One broader optional regression bundle including `tests/test_mcp_kanban_1197.py` reports an existing structural substring assertion (`"_agent_view_for" not in source`) unrelated to this task's acceptance checks; no changes were made to that legacy test in builder phase.