---
id: 1125
title: Restore fail outcome to AgentView end_work and align MCP model
status: todo
priority: important
created: '2026-04-25 17:32:33.022138+00:00'
updated: '2026-04-25 18:15:10.154729+00:00'
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/reconcile-end-work-outcome-contract.md (parent #1124, T-A follow-up)
- Sources: 9 studied (inherited from #1124), 9 high-relevance
- Recommendation: Restore `fail` to AgentView valid_outcomes + EndWorkParams Literal (confidence: 0.85)
- Follow-up tasks created: none — this IS the follow-up task; implementation scope is self-contained
- Decision requests: none (T1 — autonomous bug fix)

## Validation Pass (2026-04-25)

Confirmed codebase state matches #1124 research findings exactly:
- `AgentView.end_work` valid_outcomes = `{"success", "reject", "block", "release"}` — excludes `fail`
- `EndWorkParams` Literal = `["success", "reject", "release", "block"]` — excludes `fail`
- `KanbanEngine.end_work` valid_outcomes = `{"success", "fail", "block", "reject"}` — includes `fail`
- MCP server.py parameter Literal includes `"fail"` — correct
- h-mcp-kanban skill outcome table has `fail` but missing `release` row

## Implementation Scope (5 files)

1. `serve/kanban/src/owlbear_kanban/engine.py` — AgentView.end_work: add `fail` to valid_outcomes, add `elif outcome == "fail"` branch (require claimed, forbid move_to/block_reason/archival, delegate to raw engine)
2. `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` — EndWorkParams: add `"fail"` to outcome Literal
3. `serve/kanban/tests/test_engine_end_work_1077.py` — flip `test_fail_outcome_raises_err_invalid_outcome` to expect success (note appended, status unchanged, claim released)
4. `serve/mcp-kanban/tests/test_mcp_models_1084.py` — flip `test_end_work_outcome_rejects_invalid_literal` to use a truly invalid value (e.g. `"retry"`)
5. `share/skills/h-mcp-kanban/SKILL.md` — add `release` row to outcome table

## Challenge Results
- Challenger: inherited from #1124 (reconsider, confidence 0.34 — rebutted)
- Confidence in original: 0.85 (validated against live code)
[[2026-04-25]]
## Acceptance Criteria

- [ ] AC1: `AgentView.end_work(outcome="fail", note=...)` succeeds — appends timestamped note, keeps current status, releases claim (delegates to `KanbanEngine.end_work`)
- [ ] AC2: `AgentView.end_work(outcome="fail")` requires the task to be claimed (`ERR_NOT_CLAIMED` when unclaimed)
- [ ] AC3: `AgentView.end_work(outcome="fail")` rejects `move_to`, `block_reason`, `archival_reason`, `archival_refs` with validation errors matching the `success` branch error codes (`ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS` pattern → use `ERR_MOVE_TO_FORBIDDEN_ON_FAIL`, `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK`, `ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS` pattern → use `ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL`)
- [ ] AC4: `EndWorkParams(outcome="fail")` validates successfully (Pydantic Literal includes `"fail"`)
- [ ] AC5: h-mcp-kanban SKILL.md outcome table includes `release` row with behavior: "Release claim without note or status change (idempotent on unclaimed)"

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: restore `fail` outcome across AgentView/MCP contract |
| Interface clarity | PASS (after AC addition) | AC1-AC5 are mechanically testable |
| Dependency correctness | PASS | No dependencies; self-contained fix |
| Module layering | PASS | AgentView → KanbanEngine delegation is correct direction |
| TDD compliance | PASS | Test-writer handles RED phase; existing tests need flipping |
| KISS/YAGNI | PASS | Minimal scope: one outcome added to two validation points + doc |
| Premise challenge | PASS | Gap is real — `fail` mandated by pipeline protocol (3 active use cases), missing from AgentView |
| Pattern consistency | PASS | Follows existing outcome branch pattern in AgentView.end_work |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine domain; skill doc update is ancillary |

### Codebase Evidence
- `KanbanEngine.end_work` (engine.py:1395): valid_outcomes includes `fail` ✅
- `AgentView.end_work` (engine.py:2778): valid_outcomes excludes `fail` ❌ (the bug)
- `EndWorkParams` (models.py:111): Literal excludes `fail` ❌ (the bug)
- MCP `server.py` (line 400): Literal includes `fail` ✅ (already correct)
- `_apply_outcome` (engine.py:1356): `fail` case = no status change ✅
- `release_task` (engine.py:1259): does NOT append notes — confirms `release` ≠ `fail`

### Failure Mode Map
No new failure modes. Restoring existing behavior that raw engine already handles.

### Challenge Results
- Challenger: proceed (0.78 — below 0.80 threshold)
- Concerns: AC specificity on test expectations, claimed-state requirement for fail
- Architect response: addressed — AC2 explicitly requires claimed state, AC3 specifies error codes, AC1/AC4 define positive behavior. Concerns were about AC completeness, now resolved by REFINE.

### Verdict: APPROVE (via REFINE — AC added)
### Action Taken: Added AC1-AC5 checkboxes formalizing behavior, error codes, and doc deliverable. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes
- Test file: tests/test_engine_end_work_fail_1125.py
- Classes: TestFromAC_FailOutcome, TestFromAC_EndWorkParamsFail, TestFromAC_SkillDocReleaseRow
- Tests per category: happy 5 (AC1 success path), error 5 (AC2 unclaimed + AC3 forbidden params), boundary 3 (AC4 Pydantic Literal, AC5 SKILL.md rows)
- Total: 13 tests, all FAIL
- ruff: clean

| AC | Tests | Coverage |
|----|-------|----------|
| AC1 | test_fail_outcome_returns_response, test_fail_outcome_status_unchanged, test_fail_outcome_releases_claim, test_fail_outcome_note_appended, test_fail_outcome_note_has_timestamp | ✅ |
| AC2 | test_fail_outcome_unclaimed_raises_not_claimed | ✅ |
| AC3 | test_fail_outcome_move_to_raises_forbidden, test_fail_outcome_block_reason_raises_forbidden, test_fail_outcome_archival_reason_raises_forbidden, test_fail_outcome_archival_refs_raises_forbidden | ✅ |
| AC4 | test_end_work_params_accepts_fail | ✅ |
| AC5 | test_skill_doc_outcome_table_has_release_row, test_skill_doc_release_row_describes_behavior | ✅ |

