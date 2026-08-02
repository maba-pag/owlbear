---
id: 1196
title: 'P1-XX: Add task_id input validation at MCP boundary for decisions.create_dr'
status: archived
priority: medium
created: 2026-04-30T07:17:17.451013+00:00
updated: 2026-04-30T11:15:42.564304+00:00
tags:
- phase-1
- scope:kanban
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add input validation for the raw `task_id` parameter at the MCP boundary (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429-449`) before it is forwarded to `decisions.create_dr`.

## Acceptance Criteria

- [ ] Numeric-only check rejects non-numeric / wildcard / empty `task_id` values at the MCP boundary layer with a `ToolError` before `decisions.create_dr` is called (td:2)
- [ ] Invalid `task_id` values return an MCP error response and never reach `decisions.create_dr` (td:2)
- [ ] Tests prove rejection of: empty string, wildcard (`*`), path-traversal (`../`), non-numeric strings (td:2)
- [ ] Valid numeric task IDs (string `"42"` or int `42`) are coerced to `int` before forwarding to `decisions.create_dr` (td:1)
- [ ] Durable suite `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` assertion at line 145 updated to expect `int(1)` instead of `str("1")`, and both suites pass together (td:1)

## Context

- Architect loop-breaker cycle 7 ruling on #1180
- Parent: #1179
- Location: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` lines 429-449
- Downstream: `decisions.create_dr` expects `task_id: int` and uses it in filename construction
- Pattern: inline validation similar to the `request_type` check already present in `create_dr`

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validates one parameter at one boundary |
| Interface clarity | PASS | Clear inputs (str/int), outputs (ToolError or int forwarded) |
| Dependency correctness | PASS | No deps needed; standalone boundary guard |
| Module layering | PASS | MCP layer validates before calling kanban engine layer |
| TDD compliance | PASS | Task will flow through test-writer (RED) → builder (GREEN) |
| KISS/YAGNI | PASS | Minimal inline check; no new abstraction needed |
| Premise challenge | PASS | Path-traversal via filename interpolation is a real vulnerability |
| Pattern consistency | PASS | Mirrors existing `request_type` inline check at same location |
| Security surface | PASS | This task IS the security boundary fix |
| Single domain | PASS | MCP boundary only (scope:kanban) |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| task_id contains `../` | Path traversal in DR filename | None (silent write) | NO → fixed by this task | File written outside decisions dir |
| task_id is empty | Empty filename segment | Possible OSError | NO → fixed by this task | Corrupted filename |
| task_id is `*` | Glob expansion in engine.edit_task | Unexpected match | NO → fixed by this task | Wrong task mutated |

### Design Diverge
- Skipped: single clear approach (inline validation before forwarding), no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.18)
- Architect response: rebutted — challenger misread context as code-review of completed work; task is in backlog awaiting implementation. Valid point about str→int coercion incorporated into refined AC4.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC4 to specify int coercion (not passthrough), added test-depth annotations, advancing to todo

[[2026-04-30]]
## Architecture Review

Reviewed MCP boundary for `create_dr` tool. Confirmed path-traversal vulnerability: raw `task_id` flows into `f"{task_id}-{slug}.md"` filename construction in `decisions.create_dr`. Refined AC4 to specify int coercion (downstream expects `task_id: int`). All 10 criteria PASS. Challenger rebutted (misread backlog task as completed work). Advancing to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1196.py
- Classes: TestFromAC_CreateDrTaskIdValidation
- Tests per category: happy 0, edge 2, error 5, boundary 1
- Total: 8 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1 (td:2): numeric-only check rejects invalid task_id with ToolError | test_empty_string_rejected, test_wildcard_rejected, test_path_traversal_rejected, test_non_numeric_string_rejected, test_mixed_alphanumeric_rejected |
| AC2 (td:2): invalid never reaches decisions.create_dr | test_wildcard_does_not_reach_decisions_create_dr, test_empty_string_does_not_reach_decisions_create_dr |
| AC3 (td:2): explicit rejection proof for each listed invalid value | covered by AC1 tests (empty, wildcard, path-traversal, non-numeric each have dedicated test) |
| AC4 (td:1): numeric string coerced to int | test_numeric_string_coerced_to_int_before_forwarding |

Failure reasons:
- Tests 1-7: pytest.raises(ToolError) → 'DID NOT RAISE' (no validation in current code)
- Test 8: '42' (str) forwarded as-is; isinstance(task_id, int) fails
[[2026-04-30]]
## Builder Notes
- Implementation: added MCP boundary validation/coercion for `create_dr(task_id)` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Fixes applied:
  - Accept `task_id` as `str | int` at tool boundary.
  - Reject invalid values (`""`, `"*"`, `"../"`, non-numeric/mixed strings) with `ToolError("task_id must be numeric")` before engine-layer call.
  - Coerce valid numeric string IDs (e.g. `"42"`) to `int` before forwarding to `decisions.create_dr`.
  - Forward already-int IDs unchanged.
- Test results (quality-runner, scoped): 8 passed, 0 failed, 0 skipped for tests/test_mcp_kanban_1196.py.
- Coverage (quality-runner scoped report): `owlbear_mcp_kanban.server` reported 26% in scoped run context.
- Lint: clean (ruff clean for touched source + task test file).
- Durable module-level test file check: tests/test_mcp_kanban.py not present in workspace; durable single-file rerun skipped.
- Evidence summary: RED confirmed first (8 failing TestFromAC cases: missing ToolError + missing int coercion), then GREEN confirmed after single-file surgical patch.

### Reflection
- Boundary validation at MCP entrypoint is sufficient to block traversal/wildcard payloads before filesystem-sensitive downstream code.
- String-to-int coercion belongs at API boundary when downstream file naming assumes integer IDs.
- Scoped quality evidence is fast and reliable for AC closure, but module-percent coverage can underrepresent narrowly-scoped fixes in large files.

Commit:
- 4301b3d7 fix: validate create_dr task_id boundary (#1196, builder)
[[2026-04-30]]
## Review Evidence
### Changed Scope
- Builder commit `4301b3d7` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Changed-file scope reconstructed from builder notes and current source inspection: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- No current-tree evidence of weakened or removed `TestFromAC_*` assertions in `tests/test_mcp_kanban_1196.py`.

### Test Results
- pytest: 8 passed, 0 failed, 0 skipped in the scoped quality-runner pass for `tests/test_mcp_kanban_1196.py`.

### Lint
- ruff: clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `tests/test_mcp_kanban_1196.py`.

### Coverage
- Scoped quality-runner report: `owlbear_mcp_kanban.server` at 26% module coverage.
- Relevant branch gap: line 442 in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` was not executed, which is the direct `int` branch for `task_id`.
- Module-wide percentage is informational here; the gating issue is the uncovered changed branch tied to AC4.

### Pass 1 - Critical
#### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Numeric-only check rejects non-numeric, wildcard, and empty `task_id` values with `ToolError` before downstream call | Rejection logic is in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:443-447`. Dedicated rejection tests exist at `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, `:171`, and `:184`. | `test_empty_string_rejected_with_tool_error`, `test_wildcard_rejected_with_tool_error`, `test_path_traversal_rejected_with_tool_error`, `test_non_numeric_string_rejected_with_tool_error`, `test_mixed_alphanumeric_rejected_with_tool_error` | PASS |
| Invalid `task_id` values return an MCP error response and never reach `decisions.create_dr` | Explicit `assert_not_called()` proof exists only at `tests/test_mcp_kanban_1196.py:204-227` for wildcard and empty string. There is no equivalent non-call assertion for `../`, `abc`, or `42abc`. | `test_wildcard_does_not_reach_decisions_create_dr`, `test_empty_string_does_not_reach_decisions_create_dr` | FAIL |
| Tests prove rejection of empty string, wildcard, path-traversal, and non-numeric strings | Dedicated rejection tests exist at `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, and `:171`. | `test_empty_string_rejected_with_tool_error`, `test_wildcard_rejected_with_tool_error`, `test_path_traversal_rejected_with_tool_error`, `test_non_numeric_string_rejected_with_tool_error` | PASS |
| Valid numeric task IDs (`"42"` or `42`) are coerced to `int` before forwarding | The implementation has a separate direct-int branch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-442`. The suite tests only the string path at `tests/test_mcp_kanban_1196.py:234` with exact assertions at `:247` and `:250`. The scoped coverage report also shows line 442 unexecuted. | `test_numeric_string_coerced_to_int_before_forwarding` | FAIL |

#### Security Review
- No confirmed scoped security defect remains for the AC-listed string invalids. The handler rejects non-digit strings before the downstream file-creation call at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:443-459`.
- Informational only: Python `bool` would satisfy `isinstance(task_id, int)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-442`, but I did not find repo-local proof that the MCP boundary admits boolean payloads for this tool, so this was not used as a gating failure.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in the current task-owned suite.

#### Test Quality
- Assertion specificity is strong: the positive path uses exact forwarded-value and exact-type assertions at `tests/test_mcp_kanban_1196.py:247-250`.
- The gating weakness is coverage completeness, not assertion looseness: the suite omits the literal `42` branch and only partially proves the full non-call contract across all invalid classes named by the AC.

#### Data Safety
- No additional scoped data-safety defect confirmed.

### Deductions
- 0.10: AC4 proof is missing for the literal `task_id=42` branch.
- 0.06: AC2 proof is incomplete across the full invalid-value set named by the task.
- 0.02: changed-file scope was reconstructed from builder notes plus git-log presence rather than a direct diff.

### Verdict
- FAIL
- Confidence: 0.80
- Action: reject to `todo` for task-owned test strengthening.

### Required Follow-up
1. Add a task-owned test that passes literal `task_id=42` and asserts `decisions.create_dr` receives integer `42` through the direct-int branch.
2. Extend the non-call proof so the remaining invalid classes in scope also assert `decisions.create_dr` is not reached.
3. Re-run scoped quality after strengthening the suite. No builder change is required unless the stronger tests expose a real source defect.

### Reflection
- Scoped coverage can expose an untested AC branch even when the task-owned suite is green.
- This review found a proof gap, not a confirmed implementation defect.
- Keeping the possible boolean path informational avoided turning an unproven boundary question into a false implementation reject.
[[2026-04-30]]
## Test-Writer Notes
- Retry: added 4 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.

New tests added to `tests/test_mcp_kanban_1196.py` (class `TestFromAC_CreateDrTaskIdValidation`):
1. `test_path_traversal_does_not_reach_decisions_create_dr` — AC2 not-called proof for `../`
2. `test_non_numeric_string_does_not_reach_decisions_create_dr` — AC2 not-called proof for `abc`
3. `test_mixed_alphanumeric_does_not_reach_decisions_create_dr` — AC2 not-called proof for `42abc`
4. `test_literal_int_task_id_forwarded_unchanged` — AC4 direct-int branch (task_id=42)

Quality-runner: 12 passed, 0 failed — implementation already covers all gaps.
Lint: clean. Advancing directly to review (Step 1b.1).
[[2026-04-30]]
## Builder Notes
- Non-implementation builder pass-through on retry: current implementation already satisfies strengthened TestFromAC coverage.
- Files changed: none.
- Tests: 12 passed, 0 failed, 0 skipped (`tests/test_mcp_kanban_1196.py`).
- Lint: clean (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1196.py`).
- Coverage (scoped): `owlbear_mcp_kanban.server` 27% (module-wide percentage in scoped context; no new builder code introduced).
- Evidence summary: AC-focused invalid-path and int-branch proofs are now present in task-owned tests and pass against current source.

### Reflection
- This cycle was a proof-completeness retry from test-writer, not a code-defect repair.
- Builder skip is appropriate when strengthened tests pass and no implementation delta is required.
- Scoped quality verification remains necessary before releasing to review.
[[2026-04-30]]
## Review Evidence
### Changed Scope
- Current implementation under review: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-459`.
- Task-owned suite: `tests/test_mcp_kanban_1196.py`.
- Adjacent durable suite checked because it exercises the same public `create_dr` success path: `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:126-159`.
- Task file contains 1 prior `## Review Evidence` section already, so this rejection is the 2nd review failure and triggers the backlog loop-breaker route.

### Test Results
- Scoped quality-runner pass: 12 passed, 0 failed, 0 skipped for `tests/test_mcp_kanban_1196.py`.
- Related `create_dr` regression pass: 18 passed, 1 failed across `tests/test_mcp_kanban_1196.py` plus `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.
- Failing test: `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py::TestFromAC_CreateDrTool::test_create_dr_success_returns_created_true_and_relative_path`.
- Failure text: `AssertionError: create_dr did not forward task_id to decisions.create_dr — task_id forwarded as integer 1 instead of string '1'`.

### Lint
- ruff: clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1196.py`, and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.

### Coverage
- Scoped task-owned run: `owlbear_mcp_kanban.server` 27%.
- Related run: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` 28%.
- Module-wide percentage is informational only in this review. The blocker is the live adjacent-suite contract failure.

### Pass 1 - Critical
#### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Numeric-only check rejects non-numeric / wildcard / empty `task_id` values at the MCP boundary with `ToolError` before `decisions.create_dr` is called | Guard and normalization are at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:444-448`; invalid strings raise from the digit-only check at `:445-447` before downstream call at `:459`. | `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, `:171`, `:184` | PASS |
| Invalid `task_id` values return an MCP error response and never reach `decisions.create_dr` | Downstream call stays at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459`; task-owned tests assert `mock_create_dr.assert_not_called()` at `tests/test_mcp_kanban_1196.py:215`, `:227`, `:240`, `:249`, `:258`. | `tests/test_mcp_kanban_1196.py:204`, `:218`, `:234`, `:243`, `:252` | PASS |
| Tests prove rejection of empty string, wildcard (`*`), path-traversal (`../`), non-numeric strings | Dedicated `ToolError` assertions exist at `tests/test_mcp_kanban_1196.py:137`, `:151`, `:166`, `:179`. | `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, `:171` | PASS |
| Valid numeric task IDs (string `"42"` or int `42`) are coerced to `int` before forwarding to `decisions.create_dr` | Direct-int and string-to-int branches are at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-448`; forwarding happens at `:459`. Exact int-type assertions are at `tests/test_mcp_kanban_1196.py:281` and `:300`. | `tests/test_mcp_kanban_1196.py:265`, `:286` | PASS |

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in `tests/test_mcp_kanban_1196.py`.
- The retry strengthened the suite with direct non-call proofs and the literal-int branch proof.

#### Test Quality
- Task-owned suite quality is STRONG: exact `ToolError` checks, exact `assert_not_called()` checks, and exact forwarded-value + exact-type assertions.
- I am not rejecting on task-owned test weakness. The blocker is a live cross-suite contract contradiction.

#### Cross-Suite Contract Conflict
- The latest task authority requires int forwarding at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-448` and `:459`, and the task-owned suite now proves that contract.
- An older durable suite still asserts the opposite behavior for the same public success path: `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145-146` requires string passthrough (`"1"`) to `decisions.create_dr`.
- The related quality-runner pass confirms the contradiction is live today, not hypothetical: that older suite fails immediately once the task-owned suite is run alongside it.
- This makes the task structurally not ready for PASS even though the task-owned AC proof is green. Passing now would rubber-stamp a contradictory repo contract.

#### Security Review
- No confirmed residual defect remains for the AC-listed invalid string classes once the digit-only guard at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:445` is applied.
- Code-reader also raised a possible `bool`-path concern through `isinstance(task_id, int)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-442`, but I did not use that as gating evidence because there is no repo-local proof in this review that the MCP wire admits booleans for this tool. The reject is grounded instead in the live failing durable suite above.

#### Data Safety
- No additional scoped data-safety defect confirmed.

### Deductions
- 0.12: broader related `create_dr` suite fails on an opposite `task_id` forwarding contract.
- 0.04: contract authority between task #1196’s refined AC and the durable `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` suite is unresolved, so a PASS would be misleading.

### Verdict
- FAIL
- Confidence: 0.84
- Action: reject to `backlog`.

### Required Follow-up
1. Reconcile the public `create_dr` forwarding contract authority: int forwarding per task #1196, or string passthrough per `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145-146`.
2. Update the durable `create_dr` suite and any related docs/tests to match the chosen authority.
3. Re-run both the task-owned suite and the older durable `create_dr` suite together before returning to review.

### Reflection
- The task-owned suite now proves the refined AC well.
- The blocker is not missing branch coverage anymore; it is a live contradiction between the refined task contract and an older durable suite.
- On a 2nd review failure, that contradiction belongs in backlog for contract reconciliation, not another narrow builder loop.
[[2026-04-30]]

## Architecture Review (cycle 2)
### Contract Reconciliation Decision
- **Authority:** `decisions.create_dr` signature declares `task_id: int` — this is the definitive downstream contract.
- **Current handler:** correctly coerces `str → int` before forwarding.
- **Task-owned suite (#1196):** correctly asserts int forwarding — ALIGNED.
- **Durable suite (#1182):** `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145` asserts `task_id == "1"` (string) — STALE. Written pre-coercion, never updated.
- **Resolution:** The durable test assertion is wrong. Fix the durable test to assert `int(1)`, not `str("1")`.

### AC Addition
Added AC5 to address the cross-suite contract conflict identified by reviewer.

### Evaluation (delta from cycle 1)
- All 10 criteria still PASS.
- No new failure modes introduced.
- The reconciliation is a 1-line assertion fix in an adjacent suite.

### Test Depth
- AC5: (td:1) — single assertion update, one test proves it.
- Test-writer: PROCEED.

### Challenge Results
- Challenger: SKIPPED — reconciliation is mechanical (function signature proves authority).

### Verdict: APPROVE
### Action Taken: Added AC5 for durable-suite reconciliation, advancing to todo.

[[2026-04-30]]
## Architecture Review (cycle 2)

Contract reconciliation: `decisions.create_dr` signature declares `task_id: int` — definitive authority. Durable suite #1182 assertion is stale (pre-coercion). Added AC5 requiring the durable test to be fixed and both suites to pass together. All 10 criteria still PASS. Challenger skipped (mechanical fix). Advancing to todo.
[[2026-04-30]]
## Test-Writer Notes
- Retry (cycle 3): fixed stale assertion in durable suite per AC5 and Required Follow-up.
- Fix: `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145` — changed `"1"` (str) to `1` (int) to match current implementation's coercion contract.
- No new failing tests added — the fix reconciles the cross-suite contract contradiction identified by the 2nd reviewer.
- Quality: 19 passed, 0 failed across both suites (`tests/test_mcp_kanban_1196.py` 12 tests + `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` 7 tests).
- Lint: clean.
- Builder skip: test-only retry, all tests green (Step 1b.1).
- Commit: 9897f5dc test: fix stale task_id assertion in durable create_dr suite (#1196, test-writer)
[[2026-04-30]]
## Builder Notes
- Implementation: no code changes in this cycle (test-only retry was already applied by test-writer).
- Files changed: none.
- Tests: 19 passed, 0 failed, 0 skipped (`tests/test_mcp_kanban_1196.py` + `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`).
- Coverage: `owlbear_mcp_kanban.server` 28% in scoped context (module-wide percentage informational for this targeted validation).
- ruff: clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1196.py`, and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.
- Evidence summary: cross-suite task_id contract is reconciled; both suites pass together and lint is clean.

### Reflection
- This was a builder verification pass, not an implementation pass.
- Cross-suite contract reconciliation is confirmed by a combined scoped run.
- Scoped quality-runner evidence is sufficient to advance without additional source edits.
[[2026-04-30]]
## Review Evidence
### Changed Scope
- Retry commit `9897f5dc` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Live source under review: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429-468`.
- Live suites under review: `tests/test_mcp_kanban_1196.py` and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.
- `vscode_listCodeUsages` found only MCP registration at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:61` and the tool definition at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429`; no downstream Python callers were impacted by the widened boundary input type.

### Test Results
- quality-runner scoped combined run: 19 passed, 0 failed, 0 skipped across `tests/test_mcp_kanban_1196.py` and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.

### Lint
- ruff: clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1196.py`, and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.

### Coverage
- quality-runner scoped coverage: `owlbear_mcp_kanban.server` 28% module-wide.
- Module percentage is informational here. The AC-relevant branches are exercised in the live suites: invalid `request_type` guard at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:437-439` by `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:246`; direct-int branch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-442` by `tests/test_mcp_kanban_1196.py:286-300`; string normalize/reject/coerce path at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:443-448` by `tests/test_mcp_kanban_1196.py:127-281`; downstream handoff at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459` by both suites; `KanbanError` mapping at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:465` by `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:168`; relative-path serialization at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:467-468` by `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:121-164`.

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Numeric-only check rejects non-numeric / wildcard / empty `task_id` values at the MCP boundary with `ToolError` before `decisions.create_dr` is called | Validation and rejection live at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-450`. Dedicated rejection coverage is at `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, `:171`, `:184` with `pytest.raises(ToolError)` assertions at `:137`, `:151`, `:166`, `:179`, `:195`. | `test_empty_string_rejected_with_tool_error`, `test_wildcard_rejected_with_tool_error`, `test_path_traversal_rejected_with_tool_error`, `test_non_numeric_string_rejected_with_tool_error`, `test_mixed_alphanumeric_rejected_with_tool_error` | PASS |
| Invalid `task_id` values return an MCP error response and never reach `decisions.create_dr` | The downstream call remains after validation at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459`. Non-call proof is explicit at `tests/test_mcp_kanban_1196.py:204-258`, with `mock_create_dr.assert_not_called()` at `:215`, `:227`, `:240`, `:249`, `:258`. | `test_wildcard_does_not_reach_decisions_create_dr`, `test_empty_string_does_not_reach_decisions_create_dr`, `test_path_traversal_does_not_reach_decisions_create_dr`, `test_non_numeric_string_does_not_reach_decisions_create_dr`, `test_mixed_alphanumeric_does_not_reach_decisions_create_dr` | PASS |
| Tests prove rejection of: empty string, wildcard (`*`), path-traversal (`../`), non-numeric strings | The rejection tests listed above are present and would fail if the MCP boundary stopped raising `ToolError` for those inputs. | `tests/test_mcp_kanban_1196.py:127`, `:142`, `:156`, `:171` | PASS |
| Valid numeric task IDs (string `"42"` or int `42`) are coerced to `int` before forwarding to `decisions.create_dr` | Coercion and forwarding live at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:441-459`. Exact forwarded-value and exact-type assertions are at `tests/test_mcp_kanban_1196.py:278`, `:281`, `:297`, `:300`. | `test_numeric_string_coerced_to_int_before_forwarding`, `test_literal_int_task_id_forwarded_unchanged` | PASS |
| Durable suite `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` assertion updated to expect `int(1)` instead of `str("1")`, and both suites pass together | The durable success-path assertion now expects integer `1` at `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145`, and the combined quality-runner run passed both suites together (19/19). | `test_create_dr_success_returns_created_true_and_relative_path` plus combined quality-runner run | PASS |

#### Security Review
- PASS. Invalid-string inputs are stripped and rejected before the engine handoff at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:443-447`, and only a validated integer is forwarded at `:459`. I found no remaining path-traversal, injection, secret, or logging-leak issue in the reviewed scope.

#### Test Integrity
- PASS. No weakened or removed `TestFromAC_*` assertions were found.
- The durable suite change at `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:145` is a strengthening that aligns the older suite with the authoritative `int` contract already proven by `tests/test_mcp_kanban_1196.py:278-300`.

#### Test Quality
- PASS. Assertion specificity is strong: invalid-input tests require `ToolError` and exact non-call proof at `tests/test_mcp_kanban_1196.py:213-258`; valid-input tests require exact numeric equality and exact `int` type at `tests/test_mcp_kanban_1196.py:278-281` and `:297-300`.
- code-reader found no significant untested branch inside the declared contract.

#### Data Safety
- PASS. This boundary now validates before the single threaded handoff and does not persist unvalidated `task_id` strings or introduce shared-state/race behavior in the reviewed path.

#### Builder Process Quality
- FRICTION, not LOOP. The task has prior review failures, but the retries varied approach and closed distinct issues: first missing proof, then durable-suite contract reconciliation. No repeated identical retry pattern or tier-3 loop is present.

### Deductions
- 0.02: module-wide coverage remains low in scoped context, so confidence rests on branch-specific proof rather than percentage.
- 0.01: stale RED-phase prose remains in the headers/comments of the two reviewed test files, which slightly lowers documentation clarity but does not weaken executable proof.

### Verdict
- PASS
- Confidence: 0.97
- Action: advance to `docs`.

### Informational
- `tests/test_mcp_kanban_1196.py:1-20` still describes the suite as failing RED-phase coverage even though the live run is green.
- `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py:1` still says `RED phase tests` even though the suite now matches the green contract.
- These are non-blocking because the executable assertions and combined run are authoritative.

### Reflection
- Combined scoped quality evidence was necessary here; the task could not be passed safely on the task-owned suite alone because prior review history had already surfaced a cross-suite contract contradiction.
- The durable-suite assertion is now aligned with the downstream `decisions.create_dr(task_id: int)` contract, and both suites prove the same behavior.
- Branch-specific proof mattered more than module-wide percentage on this narrow boundary-validation fix.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-kanban/README.md` tools table listed `create_dr(task_id: str, ...)` — stale after boundary widened to `str | int`. Updated to `task_id: str \| int`. |
| 2 | Module docstrings | Yes | N/A | `create_dr` docstring ("Create a pending decision/action request file and return relative path.") remains accurate; public behavior unchanged. No edit needed. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/kanban.excalidraw` describes `serve/mcp-kanban/src/**`; `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**`. Both footers updated from `902fbc55` → `843dfc38` (same date 2026-04-30). |
| 6 | Explicit diagram creation | No | N/A | Not requested. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | IN (docstrings) | Docstring verified accurate; no edit needed |
| `tests/test_mcp_kanban_1196.py` | OUT | Test file — excluded |
| `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` | OUT | Test file — excluded |
| `serve/mcp-kanban/README.md` | IN | Updated `create_dr` signature |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/mcp-kanban/README.md` — `create_dr` signature updated to `task_id: str | int`
- `share/diagrams/kanban.excalidraw` — footer hash updated to `843dfc38`
- `share/diagrams/mcp-topology.excalidraw` — footer hash updated to `843dfc38`
- Commit: `3ebf2979`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1196-*` files found)

[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Numeric-only check rejects invalid task_id with ToolError | server.py:444-447 validation; tests at test_mcp_kanban_1196.py:127-195 | PASS |
| AC2: Invalid values never reach decisions.create_dr | assert_not_called() proofs at test_mcp_kanban_1196.py:204-258 | PASS |
| AC3: Tests prove rejection of empty/wildcard/path-traversal/non-numeric | Dedicated tests at test_mcp_kanban_1196.py:127-184 | PASS |
| AC4: Coercion to int before forwarding | server.py:441-448; assertions at test_mcp_kanban_1196.py:278-300 | PASS |
| AC5: Durable suite assertion fixed and both suites pass | test_mcp_create_dr_1182.py:145 asserts int(1); combined 19/19 | PASS |

### Test Results
- pytest (full): 3324 passed, 73 failed (none in task scope), 4 skipped
- ruff: clean

### Architect Quality: 4/5
AC was specific and verifiable. Required cycle 2 to add AC5 for durable-suite reconciliation the reviewer surfaced, but that was appropriate architect intervention for an emergent cross-suite conflict.

### Deduction Breakdown
- All 5 AC lines have specific evidence: 0
- Lint: clean: 0
- AC quality 4/5: 0
- Reviewer evidence: present, detailed, PASS: 0
- Full-suite failures outside task scope (pre-existing debt): 0
- Module coverage low but branch-specific proof strong: 0

### Confidence: 0.99
### Action: archive