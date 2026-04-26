---
id: 1125
title: Restore fail outcome to AgentView end_work and align MCP model
status: review
priority: important
created: 2026-04-25 17:32:33.022138+00:00
updated: 2026-04-26T02:16:07.760194+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
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


[[2026-04-26]]
## Test-Writer Notes
- Test file: tests/test_engine_end_work_fail_1125.py (committed 9e99d6de — already in repo)
- Classes: TestFromAC_FailOutcome, TestFromAC_EndWorkParamsFail, TestFromAC_SkillDocReleaseRow
- Tests per category: happy 5 (AC1), error 5 (AC2, AC3), boundary 3 (AC4, AC5)
- Total: 13 tests

**Out-of-order delivery note:** All 13 tests currently PASS. The implementation was delivered outside the normal pipeline flow before this test-writer run (engine.py `fail` branch committed in #1077 history; EndWorkParams Literal updated in 41c170b2). The test file was committed in 9e99d6de (previous test-writer session that did not advance the task).

**AC coverage confirmed via passing tests:**

| AC | Tests | Status |
|----|-------|--------|
| AC1 | test_fail_outcome_returns_response, test_fail_outcome_status_unchanged, test_fail_outcome_releases_claim, test_fail_outcome_note_appended, test_fail_outcome_note_has_timestamp | ✅ impl done |
| AC2 | test_fail_outcome_unclaimed_raises_not_claimed | ✅ impl done |
| AC3 | test_fail_outcome_move_to_raises_forbidden, test_fail_outcome_block_reason_raises_forbidden, test_fail_outcome_archival_reason_raises_forbidden, test_fail_outcome_archival_refs_raises_forbidden | ✅ impl done |
| AC4 | test_end_work_params_accepts_fail | ✅ impl done |
| AC5 | test_skill_doc_outcome_table_has_release_row, test_skill_doc_release_row_describes_behavior | ✅ impl done |

Builder: implementation appears complete — verify and advance.
[[2026-04-26]]
## Builder Notes
- Implementation: No new code edits in this builder pass; AC implementation already present in workspace (`serve/kanban/src/owlbear_kanban/engine.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`, `share/skills/h-mcp-kanban/SKILL.md`) and verified.
- Tests: 13 TestFromAC tests passed in `tests/test_engine_end_work_fail_1125.py` (failed: 0).
- Lint: ruff clean on task-relevant source + tests.
- Coverage: Module-focused verification in broad quality-runner pass reported `owlbear_kanban.engine` 95% and `owlbear_mcp_kanban.models` 99%; scoped-only run is lower due narrow slice but functional AC coverage is complete.
- Evidence summary: quality-runner scoped run (task tests/lint) passed; broader run confirmed strong module coverage for touched contracts; full-suite run shows unrelated pre-existing failures/errors outside this task scope.
- Approach: Verification-and-advance path for out-of-order implementation; no speculative refactors.

### Post-task Reflection
- Problem faced: Task was already implemented out-of-order, so builder phase required validation rather than coding.
- Workaround applied: Used quality-runner scoped and broader module-focused runs to establish trustworthy GREEN evidence.
- Pattern discovered: For large modules (`owlbear_kanban.engine`), ultra-scoped coverage can under-represent true module exercised paths; broader-but-related suites provide better gate signal.
- Time sink: Full-suite verification produced significant unrelated failures/errors, reducing signal for task-specific gating.
- Quality gap: Repository-wide suite has baseline instability unrelated to #1125, which should be handled as separate stabilization work.
[[2026-04-26]]
## Review Evidence
### Test Results
- quality-runner scoped run: 13 passed, 0 failed, 0 skipped for `tests/test_engine_end_work_fail_1125.py`.
- quality-runner broader related slice: 251 passed, 1 failed, 0 skipped.
- Broader-slice failure used as regression context only: `serve/kanban/tests/test_engine_coverage_1110.py::TestFromAC_EngineListSessionsSpecialActions::test_release_action_produces_released_session` asserted `'released'` vs `'release'`, outside #1125 AC scope.

### Lint
- Scoped lint on task-relevant source and tests: clean.

### Coverage
- Scoped run: `owlbear_kanban.engine` 17%, `owlbear_mcp_kanban.models` 90%.
- Broader related slice: `owlbear_kanban.engine` 53%, `owlbear_mcp_kanban.models` 97%.
- Coverage note: `serve/kanban/src/owlbear_kanban/engine.py` is a large shared module, so isolated reruns under-report module-wide coverage. The routing decision below is based on proof quality, not on treating the unrelated broader-slice failure as a task regression.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1 | `test_fail_outcome_returns_response`, `test_fail_outcome_status_unchanged`, `test_fail_outcome_releases_claim`, `test_fail_outcome_note_appended`, `test_fail_outcome_note_has_timestamp` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L145) | Yes. These tests would fail on rejection of `fail`, status change, missing claim release, missing note, or missing timestamp. | COVERED |
| AC2 | `test_fail_outcome_unclaimed_raises_not_claimed` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L224) | Yes. Exact `ERR_NOT_CLAIMED` assertion. | COVERED |
| AC3 | `test_fail_outcome_move_to_raises_forbidden`, `test_fail_outcome_block_reason_raises_forbidden`, `test_fail_outcome_archival_reason_raises_forbidden`, `test_fail_outcome_archival_refs_raises_forbidden` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L242) | Yes. Each forbidden parameter has its own exact error-code assertion. | COVERED |
| AC4 | `test_end_work_params_accepts_fail` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L315) | Yes. Literal acceptance is asserted directly. | COVERED |
| AC5 | `test_skill_doc_outcome_table_has_release_row` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L344) and `test_skill_doc_release_row_describes_behavior` at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L356) | No. The behavior check at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L372) accepts any one of `idempotent`, `release claim`, or `unclaimed`, so a partially wrong row could still pass. | LAX |

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-body inventory of 13 `TestFromAC_*` tests | All 13 named tests are present in the current snapshot at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L145) | PRESERVED |

#### Test Quality
- Assertion specificity: WEAK for AC5. [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L372) only keyword-matches the release-row behavior. A row like `Release claim.` would still pass, even though AC5 requires the full behavior text now present at [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L65).
- Negative and error-path coverage: ADEQUATE for AC1-AC4.
- Manual mutation reasoning: removing `without note or status change` from the release row would not fail the current AC5 proof.
- Test independence and naming: ADEQUATE.

#### Security Review
- No issues found. This task restores an existing outcome contract and updates validation/docs only.

#### Data Safety
- No issues found. `fail` still routes through the existing engine end-work path that appends the timestamped note and clears the claim before applying the no-status-change outcome at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1252) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1415).

#### Implementation-Aware Test Gaps
- AC5 proof gap: exact row text is not asserted. The implementation currently matches AC5 at [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L65), but the test would false-green on a partial behavior string.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability.

#### Builder Process Quality
- CLEAN. No prior `## Review Evidence` section was present in the task body.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `fail` is accepted in AgentView valid outcomes at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2806); non-release outcomes delegate to raw engine at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2950); raw engine appends timestamped notes and clears claim before applying the no-status-change fail outcome at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1252) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1415). Scoped pytest was green. | AC1 tests at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L145) | PASS |
| AC2 | Unclaimed mutating outcomes raise `ERR_NOT_CLAIMED` at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2922). Scoped pytest was green. | AC2 test at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L224) | PASS |
| AC3 | `fail` forbids `move_to` and archival fields at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2827) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2832), with matching task tests green. | AC3 tests at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L242) | PASS |
| AC4 | MCP input model accepts `fail` in the outcome literal at [serve/mcp-kanban/src/owlbear_mcp_kanban/models.py](serve/mcp-kanban/src/owlbear_mcp_kanban/models.py#L114). Scoped pytest was green. | AC4 test at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L315) | PASS |
| AC5 | The skill doc contains the required release row at [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L65). Current tests are green, but the proof is lax because it does not assert the full required behavior string. | AC5 tests at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L344) | PASS (proof LAX) |

### Informational
- [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2776) still says `"fail"` raises at the AgentView layer. The implementation no longer does.
- [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L10) still says all tests are expected to fail, and the RED-phase comments at [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L318) and [tests/test_engine_end_work_fail_1125.py](tests/test_engine_end_work_fail_1125.py#L347) are now stale.

### Deductions
- -0.10 AC5 proof is lax and can false-green on a partially wrong behavior string.
- -0.02 Stale RED-phase/docstring comments reduce trust but are non-blocking.

### Verdict
- Confidence: 0.88
- FAIL
- Action: Return to `todo` for test-writer to strengthen AC5 proof. The minimal repair is to assert the full release-row behavior text exactly, not keyword presence.

### Post-task Reflection
- Problem faced: task-owned tests were green, but the only doc-behavior proof for AC5 was weaker than the AC text.
- Workaround applied: combined a clean scoped quality-runner pass with direct line-by-line code reading and a broader related-slice run for regression context.
- Pattern discovered: doc-string ACs need exact row or exact cell assertions; keyword matching is a recurring false-green source.
- Time sink: broader engine slices surfaced unrelated legacy failures while still under-reporting coverage on the large shared engine module.
- Quality gap: stale RED-phase comments remain in the task test file and one AgentView docstring still describes the pre-fix contract.
[[2026-04-26]]
## Test-Writer Notes
- Test file: tests/test_engine_end_work_fail_1125.py
- Classes: TestFromAC_FailOutcome, TestFromAC_EndWorkParamsFail, TestFromAC_SkillDocReleaseRow
- Retry action: Added `test_skill_doc_release_row_exact_behavior_text` to TestFromAC_SkillDocReleaseRow — asserts the verbatim AC5 behavior string "Release claim without note or status change (idempotent on unclaimed)" rather than keyword presence.
- Total: 14 tests (13 original + 1 new), all PASS (out-of-order delivery — implementation was already present)
- ruff: clean
- Commit: 5f7312b1

| AC | Tests | Coverage |
|----|-------|----------|
| AC1 | test_fail_outcome_returns_response, test_fail_outcome_status_unchanged, test_fail_outcome_releases_claim, test_fail_outcome_note_appended, test_fail_outcome_note_has_timestamp | ✅ |
| AC2 | test_fail_outcome_unclaimed_raises_not_claimed | ✅ |
| AC3 | test_fail_outcome_move_to_raises_forbidden, test_fail_outcome_block_reason_raises_forbidden, test_fail_outcome_archival_reason_raises_forbidden, test_fail_outcome_archival_refs_raises_forbidden | ✅ |
| AC4 | test_end_work_params_accepts_fail | ✅ |
| AC5 | test_skill_doc_outcome_table_has_release_row, test_skill_doc_release_row_describes_behavior, test_skill_doc_release_row_exact_behavior_text (NEW — exact string) | ✅ strong |
[[2026-04-26]]
## Builder Notes
- Implementation: No source edits in this builder pass; implementation for AC1-AC5 was already present, and this pass validated the strengthened AC5 proof from test-writer.
- Files changed: none.
- Tests: 14 passed, 0 failed, 0 skipped (`tests/test_engine_end_work_fail_1125.py`).
- Coverage: `owlbear_kanban.engine` 17% and `owlbear_mcp_kanban.models` 90% in scoped run. `engine.py` remains a large shared module where task-scoped coverage under-represents broader exercised paths.
- ruff: clean (no violations).
- Evidence summary: quality-runner scoped verification passed with zero failures; task-specific AC coverage is green including the exact AC5 release-row text assertion added by test-writer.
- Approach: verification-and-advance builder pass (no-op code path) after out-of-order implementation history.

### Post-task Reflection
- Problem faced: Builder phase ran on an already-implemented task, so RED->GREEN sequencing could not be replayed historically.
- Workaround applied: Used current authoritative task tests and lint as the gating evidence for advancement.
- Pattern discovered: When implementation predates task lifecycle order, strict task-scoped verification still provides reliable builder handoff evidence.
- Time sink: Distinguishing lifecycle-history noise from current acceptance evidence.
- Quality gap: Module-level coverage metrics for large shared modules remain low in narrow scoped runs; broader regression slices should continue to be interpreted as context, not route blockers.