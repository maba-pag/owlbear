---
id: 1469
title: 'E2a-B4: Merge mcp_kanban task tests into durable'
status: archived
priority: medium
created: 2026-05-09T07:21:35.691519+00:00
updated: 2026-05-09T18:07:48.633502+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
parent: 1415
depends_on:
- 1466
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Research: `.owlbear/research/1463-python-root-test-cleanup.md` §5b
Supersedes: #1463 (partial)

## Scope

Merge 7 task-scoped files (53 tests) into existing `test_mcp_kanban.py` (67 tests), then delete sources.

### Source files

| File | Tests |
|------|:-----:|
| test_mcp_kanban_1091.py | 3 |
| test_mcp_kanban_1092.py | 7 |
| test_mcp_kanban_1126.py | 1 |
| test_mcp_kanban_1196.py | 12 |
| test_mcp_kanban_1197.py | 5 |
| test_mcp_kanban_1360.py | 8 |
| test_mcp_kanban_1450.py | 17 |

**Target:** `test_mcp_kanban.py` (existing durable, 67 tests pre-merge)

## AC

- [ ] All unique `def test_*` from 7 source files present in `test_mcp_kanban.py` (td:0)
- [ ] Duplicate test-name collisions resolved by renaming incoming to `test_{name}_{original_task_id}` (e.g. `test_edit_task_has_no_status_parameter_1091`). Known collision: `test_edit_task_has_no_status_parameter` (durable L208 vs 1091) (td:0)
- [ ] Fixture collisions (target-vs-source AND source-vs-source): keep target's if identical, rename source's if different. Known inter-source: `app_ctx_mock` (1091 vs 1092), `app_ctx` (1196 vs 1450) (td:0)
- [ ] All 7 source files deleted after merge (td:0)
- [ ] Per-target checkpoint: `uv run pytest tests/test_mcp_kanban.py --collect-only -q` collects ≥ 120 tests (67 existing + 53 merged) (td:0)
- [ ] Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline via `uv run pytest tests/ -q` before any changes) (td:0)
- [ ] Collected test count ≥ pre-task `--collect-only` baseline (td:0)
- [ ] `test_kanban_topology_1439.py` untouched (td:0)

## Out of scope

- Other merge targets (decisions_api, mutation_api, read_api, pipeline_diagram)
- Renames — handled in #1466
- Semantic deduplication of tests with different names but overlapping coverage

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: merge 7 task-scoped test files into one durable |
| Interface clarity | PASS | Source files, target file, and verification criteria all explicit |
| Dependency correctness | PASS | #1466 archived (done) — renames completed before this merge |
| Module layering | N/A | No production code changes — test file manipulation only |
| TDD compliance | PASS | All AC lines td:0 — mechanical merge, no new logic |
| KISS/YAGNI | PASS | Mechanical merge with no abstractions |
| Premise challenge | PASS | 7 stale files (53 tests) for archived tasks clutter tests/; durable exists with 67 tests |
| Pattern consistency | PASS | Follows same merge pattern as sibling tasks #1467, #1468 |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Test infrastructure only |

### Codebase Evidence
- Durable `test_mcp_kanban.py`: 67 test functions confirmed via grep (lines 155–1032)
- Fixtures in durable: `app_ctx_with_mock_view`, `app_ctx_todo`, `app_ctx_claimed` — no name collision with source fixtures
- 1 confirmed test name collision: `test_edit_task_has_no_status_parameter` in durable (L208) and 1091
- 2 inter-source fixture collisions: `app_ctx_mock` (1091/1092), `app_ctx` (1196/1450)
- `test_mcp_kanban_error_mapping.py` exists as separate durable — not in scope

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Reason: Mechanical file merge, no architectural decisions

### Design Diverge
- Skipped — single approach (mechanical merge), no competing designs

### Verdict: APPROVE
### Action Taken
- Applied AC Correction: replaced `pytest -x` lines with delta-based verification
- Applied AC Correction: collision rename suffix uses original task ID for traceability
- Expanded fixture collision AC to cover inter-source collisions with known instances
- Added "semantic dedup" to out-of-scope to prevent scope creep
- `quality` tag already present for test-writer pass-through
[[2026-05-09]]
Architecture review complete. Refined AC: replaced `pytest -x` with delta-based verification, collision rename uses original task ID for traceability, expanded fixture collision AC to cover inter-source collisions (app_ctx_mock in 1091/1092, app_ctx in 1196/1450). Confirmed 67 durable tests via grep. All td:0, test-writer SKIP. Challenger skipped (all td:0). Dependency #1466 archived.
[[2026-05-09]]
## Test-Writer Notes
- Tagged `quality` — non-implementation task (mechanical test-file merge).
- All AC lines are (td:0) — test-writer skipped per Step 1a/1c.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task per `## Test-Writer Notes` (`td:0` AC across task).
- Code changes: none.
- Tests/lint: not run by builder (pass-through workflow for non-impl tasks).
- Outcome: passing through to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner skipped. This task is all td:0 and the review hinged on direct artifact inspection, not executable behavior.
- No builder-side pytest evidence was provided in the task body.

### Lint Results
- Not run. The failure is structural and was established from file state alone.

### Coverage
- Not applicable for this td:0 merge/delete task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All unique def test_* from 7 source files present in test_mcp_kanban.py | Source [tests/test_mcp_kanban_1196.py](tests/test_mcp_kanban_1196.py#L90) still defines test_empty_string_rejected_with_tool_error, but workspace search found no same-name test in [tests/test_mcp_kanban.py](tests/test_mcp_kanban.py). Source [tests/test_mcp_kanban_1092.py](tests/test_mcp_kanban_1092.py#L132) still defines test_move_task_kanban_error_routed_via_helper, but workspace search found no same-name test in [tests/test_mcp_kanban.py](tests/test_mcp_kanban.py). | FAIL |
| Duplicate test-name collisions resolved by renaming incoming to test_{name}_{original_task_id} | Source [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py#L214) still defines test_edit_task_has_no_status_parameter. Durable file still has only [tests/test_mcp_kanban.py](tests/test_mcp_kanban.py#L171). Workspace search found no test_edit_task_has_no_status_parameter_1091 anywhere under tests/. | FAIL |
| Fixture collisions handled during merge | Durable fixtures were already normalized in [tests/test_mcp_kanban.py](tests/test_mcp_kanban.py#L79-L111), but the source collision fixtures still remain in [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py#L86), [tests/test_mcp_kanban_1092.py](tests/test_mcp_kanban_1092.py#L96), [tests/test_mcp_kanban_1196.py](tests/test_mcp_kanban_1196.py#L66), and [tests/test_mcp_kanban_1450.py](tests/test_mcp_kanban_1450.py#L68). The merge/delete work was not completed in this task cycle. | FAIL |
| All 7 source files deleted after merge | The seven source files still exist: [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py), [tests/test_mcp_kanban_1092.py](tests/test_mcp_kanban_1092.py), [tests/test_mcp_kanban_1126.py](tests/test_mcp_kanban_1126.py), [tests/test_mcp_kanban_1196.py](tests/test_mcp_kanban_1196.py), [tests/test_mcp_kanban_1197.py](tests/test_mcp_kanban_1197.py), [tests/test_mcp_kanban_1360.py](tests/test_mcp_kanban_1360.py), [tests/test_mcp_kanban_1450.py](tests/test_mcp_kanban_1450.py). | FAIL |
| Per-target checkpoint: collect-only on tests/test_mcp_kanban.py collects >= 120 tests | Not independently executable in this tool surface, and no builder evidence was recorded. Structural failures above already show the merge/delete task is incomplete. | FAIL |
| Post-cleanup failure count <= pre-task baseline failure count | Not evidenced. Builder notes report no code changes and no test execution for a task whose deliverable is file movement/deletion. | FAIL |
| Collected test count >= pre-task collect-only baseline | Not evidenced. Builder notes report no code changes and no collect-only run. | FAIL |
| test_kanban_topology_1439.py untouched | [tests/test_kanban_topology_1439.py](tests/test_kanban_topology_1439.py#L1) still exists, but untouched status was not independently verifiable because the task body provided no commit hash or changed-file list. | NOT VERIFIED |

### Findings
- The current repo state looks partially pre-consolidated: durable [tests/test_mcp_kanban.py](tests/test_mcp_kanban.py) already contains substantial coverage from the source suites, but the source files were never deleted and the known collision rename was never completed.
- The task body's latest builder section says "Code changes: none." For this task shape, that is a pipeline/ownership defect, not just a missed implementation detail.
- This is the first review failure on the task. Routing to backlog is appropriate because the td:0 pass-through contract left real test-file merge/delete work with no owning agent.

### Deductions
- -0.35: direct AC violation: all seven source files still exist.
- -0.15: required collision rename missing.
- -0.08: task design/ownership failure: td:0 pass-through produced no file changes for a file-edit task.
- -0.05: topology untouched claim not independently verifiable from provided evidence.

### Verdict
- FAIL
- Confidence: 0.37
- Route: backlog

### Action
- Re-scope this as an implementation-bearing test-cleanup task, or split it into explicit remaining work items (exact-name preservation/rename requirements vs source-file deletion) so a downstream agent actually owns the file edits.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite task ownership/scope so the remaining merge-delete work is owned by an executing agent; current td:0 pass-through leaves the task with no implementer | tests/test_mcp_kanban.py; tests/test_mcp_kanban_1091.py; tests/test_mcp_kanban_1092.py; tests/test_mcp_kanban_1126.py; tests/test_mcp_kanban_1196.py; tests/test_mcp_kanban_1197.py; tests/test_mcp_kanban_1360.py; tests/test_mcp_kanban_1450.py | Builder notes say Code changes: none; all seven source files still exist |
| 2 | architect | Clarify the exact preservation contract for merged test names and enforce the documented collision rename for the 1091 duplicate before the next cycle | tests/test_mcp_kanban.py; tests/test_mcp_kanban_1091.py; tests/test_mcp_kanban_1196.py; tests/test_mcp_kanban_1092.py | No test_edit_task_has_no_status_parameter_1091 exists; source-only names such as test_empty_string_rejected_with_tool_error and test_move_task_kanban_error_routed_via_helper do not appear in the durable file by name |
[[2026-05-09]]


## Architecture Re-Review (Cycle 2)

### Root Cause
Cycle 1 failure: all AC lines marked td:0, combined with `quality` pass-through tag, caused test-writer SKIP → builder pass-through → zero file changes. The merge/delete work was never executed by any agent.

### Corrective Actions
1. Raised AC lines 1 and 4 to td:1 (merge presence + source deletion) — test-writer writes RED tests, builder executes merge/delete for GREEN
2. Removed `quality` tag — this task requires implementation (file editing and deletion)
3. Preserved collision/fixture resolution as td:0 (naming convention detail, verified by inspection)
4. Fixed line reference drift: collision at durable L171 (not L208 as originally noted)

### Revised AC (supersedes original AC section)
- [ ] All unique `def test_*` from 7 source files present in `test_mcp_kanban.py` (td:1)
- [ ] Duplicate test-name collisions resolved by renaming incoming to `test_{name}_{original_task_id}` (e.g. `test_edit_task_has_no_status_parameter_1091`). Known collision: `test_edit_task_has_no_status_parameter` (durable L171 vs 1091) (td:0)
- [ ] Fixture collisions (target-vs-source AND source-vs-source): keep target's if identical, rename source's if different. Known inter-source: `app_ctx_mock` (1091 vs 1092), `app_ctx` (1196 vs 1450) (td:0)
- [ ] All 7 source files deleted after merge (td:1)
- [ ] Per-target checkpoint: `uv run pytest tests/test_mcp_kanban.py --collect-only -q` collects ≥ 120 tests (67 existing + 53 merged) (td:0)
- [ ] Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline via `uv run pytest tests/ -q` before any changes) (td:0)
- [ ] Collected test count ≥ pre-task `--collect-only` baseline (td:0)
- [ ] `test_kanban_topology_1439.py` untouched (td:0)

### Codebase Evidence (refreshed)
- Durable `test_mcp_kanban.py`: 67 `def test_` functions confirmed (L118–L995)
- Source totals verified: 3+7+1+12+5+8+17 = 53 tests across 7 files
- Fixtures in durable: `app_ctx_with_mock_view`, `app_ctx_todo`, `app_ctx_claimed` — no collision with source fixtures
- 1 confirmed test name collision: `test_edit_task_has_no_status_parameter` (durable L171 vs 1091 L214)
- 2 inter-source fixture collisions: `app_ctx_mock` (1091 L86 / 1092 L96), `app_ctx` (1196 L66 / 1450 L68)
- `test_mcp_kanban_error_mapping.py` and `test_kanban_topology_1439.py` exist as separate durables — not in scope

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: merge 7 task-scoped test files into one durable |
| Interface clarity | PASS | Source files, target file, collision handling, and verification all explicit |
| Dependency correctness | PASS | #1466 archived — renames completed before this merge |
| Module layering | N/A | No production code changes — test file manipulation only |
| TDD compliance | PASS | 2 AC lines at td:1 ensure test-writer writes RED, builder does GREEN |
| KISS/YAGNI | PASS | Mechanical merge with no abstractions |
| Premise challenge | PASS | 7 stale files (53 tests) for archived tasks clutter tests/; durable exists with 67 tests |
| Pattern consistency | PASS | Follows same merge pattern as sibling tasks #1467, #1468 |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Test infrastructure only |

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Challenge Results
- Challenger: reconsider (confidence 0.18)
- Challenges: "task artifact still shows td:0 / quality tag / source files exist" — conflated backlog-approval with completion sign-off. Source files are EXPECTED to exist at backlog stage; the builder will perform the merge on this cycle.
- Valid point incorporated: line reference drift (L208 → L171)
- Architect response: override — challenger evidence pertains to cycle-1 state, not the corrected blueprint being approved for cycle 2

### Verdict: APPROVE
### Action Taken
- Removed `quality` tag to prevent builder pass-through
- Raised AC lines 1 ("all test_* present") and 4 ("all source files deleted") to td:1
- Fixed collision line reference (L208 → L171)
- Preserved all other AC content and out-of-scope boundaries from cycle 1

[[2026-05-09]]
Architecture re-review (cycle 2). Root cause: all-td:0 + quality tag caused builder pass-through with zero file changes. Fix: raised AC lines 1 (test presence) and 4 (source deletion) to td:1, removed quality tag. Test-writer will write RED verification tests; builder will execute the merge/delete for GREEN. Challenger overridden — confused backlog-approval with completion sign-off. Codebase evidence refreshed: 67 durable + 53 source = 120 expected, 1 test name collision, 2 inter-source fixture collisions confirmed.
[[2026-05-09]]
## Test-Writer Notes
- Test file: `tests/test_mcp_kanban_merge_1469.py`
- Classes: `TestFromAC_SourceFilesDeleted`, `TestFromAC_AllSourceTestsPresent`
- Tests per category:
  - AC4 (source files deleted): 7 parametrized tests (one per source file)
  - AC1 (test names present in durable): 53 parametrized tests (3+7+1+12+5+8+17)
- Total: **60 tests, all FAIL** — confirmed via pytest (60 failed in 0.34s)
- Ruff: clean
- Commit: 86b7eea9

### AC Coverage
| AC Line | Tests | Class |
|---|---|---|
| AC1 (td:1): all test_* from 7 sources in durable | 53 (parametrized by source + name) | TestFromAC_AllSourceTestsPresent |
| AC2 (td:0): collision rename | covered by test_edit_task_has_no_status_parameter_1091 assertion in AC1 | TestFromAC_AllSourceTestsPresent |
| AC4 (td:1): all 7 source files deleted | 7 parametrized | TestFromAC_SourceFilesDeleted |
| AC2/AC3/AC5/AC6/AC7/AC8 (td:0) | not tested — builder/reviewer verification | — |

### Implementation notes for builder
- Collision rename: `test_edit_task_has_no_status_parameter` (1091) → `test_edit_task_has_no_status_parameter_1091`
- Inter-source fixture collisions: `app_ctx_mock` (1091/1092), `app_ctx` (1196/1450) — keep target's if identical, rename source's if different
- Source files to delete after merge: test_mcp_kanban_1091.py, _1092.py, _1126.py, _1196.py, _1197.py, _1360.py, _1450.py
[[2026-05-09]]
## Builder Notes
- Implementation: merged required test methods into durable `tests/test_mcp_kanban.py` and removed 7 task-scoped source files (`tests/test_mcp_kanban_1091.py`, `tests/test_mcp_kanban_1092.py`, `tests/test_mcp_kanban_1126.py`, `tests/test_mcp_kanban_1196.py`, `tests/test_mcp_kanban_1197.py`, `tests/test_mcp_kanban_1360.py`, `tests/test_mcp_kanban_1450.py`).
- Collision handling: added renamed method `test_edit_task_has_no_status_parameter_1091`; fixture collisions resolved with suffixed fixture names (`app_ctx_mock_1091`, `app_ctx_mock_1092`, `app_ctx_1196`, `app_ctx_1450`, archived variants).
- RED verification: quality-runner scoped run on `tests/test_mcp_kanban_merge_1469.py` reported 60 failed / 0 passed before edits.
- GREEN verification: quality-runner scoped run on `tests/test_mcp_kanban_merge_1469.py` + `tests/test_mcp_kanban.py` reported 180 passed / 0 failed.
- Lint: ruff clean on scoped paths (`tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_merge_1469.py`).
- Coverage evidence: quality-runner reported `owlbear_mcp_kanban.server` at 89% in this scoped test run.
- Commit: `37834406fdb9d66c13bc1919a57ecd877f768f3d` (`test: merge mcp_kanban task tests into durable (#1469, builder)`).
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_mcp_kanban_merge_1469.py` + `tests/test_mcp_kanban.py`: **180 passed, 0 failed, 0 skipped**.
- quality-runner broad run with normal repo pytest config (`pytest tests/ -q --tb=short`): **3170 passed, 260 failed, 5 errors, 4 skipped, 3439 collected**.
- quality-runner broad baseline comparison against pre-change snapshot `f7d83998` (parent of the task's RED-test commit): baseline was **3101 passed, 274 failed, 0 errors, 4 skipped, 3379 collected**; current state therefore has **14 fewer failures** and **60 more collected tests**.
- quality-runner confirmed **no failures or errors** in `tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_merge_1469.py`, or other root `mcp_kanban` tests during the broad normal-config run.

### Lint Results
- ruff on `tests/test_mcp_kanban.py` and `tests/test_mcp_kanban_merge_1469.py`: **clean**.

### Coverage
- Scoped quality-runner report showed `owlbear_mcp_kanban` packages at **95%** and `server.py` at **89%` in the scoped run.
- This task changes test files only; coverage is informational here. Structural proof and scoped green results are the gating evidence.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All unique `def test_*` from 7 source files present in `test_mcp_kanban.py` | `TestFromAC_AllSourceTestsPresent` enumerates the exact moved names at `tests/test_mcp_kanban_merge_1469.py:55-172`; all 180 scoped tests passed. | PASS |
| Duplicate test-name collision resolved by renaming incoming method to `test_{name}_{original_task_id}` | Renamed durable method exists at `tests/test_mcp_kanban.py:1155`; the RED verifier expects that exact renamed symbol in `tests/test_mcp_kanban_merge_1469.py:55-66`. | PASS |
| Fixture collisions handled during merge | Original durable fixtures remain at `tests/test_mcp_kanban.py:81`, `:100`, `:109`; renamed source fixtures are present at `tests/test_mcp_kanban.py:1008`, `:1022`, `:1037`, `:1045`. | PASS |
| All 7 source files deleted after merge | `TestFromAC_SourceFilesDeleted.test_source_file_does_not_exist` asserts deletion at `tests/test_mcp_kanban_merge_1469.py:43-52`; workspace file search for the seven exact source filenames returned no matches. | PASS |
| Per-target checkpoint: `tests/test_mcp_kanban.py --collect-only -q` collects >= 120 tests | quality-runner collect-only evidence reported **120 collected** for `tests/test_mcp_kanban.py`. | PASS |
| Post-cleanup failure count <= pre-task baseline failure count | Baseline snapshot `f7d83998`: **274 failed**. Current normal-config run: **260 failed**. Failure count decreased by 14, and quality-runner found no failures/errors in the task's `mcp_kanban` scope. | PASS |
| Collected test count >= pre-task `--collect-only` baseline | Baseline snapshot `f7d83998`: **3379 collected**. Current state: **3439 collected**. Count increased by 60. | PASS |
| `test_kanban_topology_1439.py` untouched | The topology suite still exists as a separate file at `tests/test_kanban_topology_1439.py:1`; no contrary evidence surfaced in task notes or quality-runner output. | PASS |

### Test Integrity / Quality
- `TestFromAC_SourceFilesDeleted.test_source_file_does_not_exist` would fail on any undeleted source file.
- `TestFromAC_AllSourceTestsPresent.test_merged_from_1091` through `_1450` assert exact durable-name membership, not vague non-empty or substring checks.
- No evidence of weakened `TestFromAC_*` assertions was found in the live file. Commit-diff immutability could not be proven directly in this tool surface, so confidence is slightly reduced.

### Deductions
- -0.03: `git status` / commit-diff tooling was not available in this session, so dirty-tree overlap on scoped files could not be independently ruled out.
- -0.02: `TestFromAC_*` immutability was verified indirectly from current file state and task history rather than a direct commit diff.
- -0.02: the broad root suite currently reports 5 errors outside task scope; no evidence ties them to `mcp_kanban`, but they reduce broad-context confidence slightly.

### Verdict
- PASS
- Confidence: 0.93
- Route: docs

### Action
- Advance to docs. Implementation and task-local proof are sufficient for the revised cycle-2 AC, and the broad baseline comparison does not show a task-scoped regression.
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task changes test files only — no API, CLI, config, or package structure changes; no IN-scope prose docs reference `tests/test_mcp_kanban*.py` |
| 2 | Module docstrings | No | N/A | No production Python modules created or modified; only `tests/*.py` files |
| 3 | External attribution | No | N/A | No external patterns used; purely internal test-file merge/delete |
| 4 | Research doc | No | N/A | `.owlbear/research/1463-python-root-test-cleanup.md` referenced as context (pre-existing); no new research doc required for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index diagrams describe `serve/cockpit/**`, `serve/kanban/src/**`, `serve/mcp-*/src/**`, etc. — none match `tests/**` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | 7 deleted files are test files (`tests/test_mcp_kanban_109x/119x/136x/145x.py`) — OUT of scope; no IN-scope prose doc references them |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_mcp_kanban.py | OUT | N/A (test file) |
| tests/test_mcp_kanban_merge_1469.py | OUT | N/A (test file) |
| tests/test_mcp_kanban_1091.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1092.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1126.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1196.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1197.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1360.py (deleted) | OUT | N/A (test file) |
| tests/test_mcp_kanban_1450.py (deleted) | OUT | N/A (test file) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1469-*` files found)
[[2026-05-09]]
## Audit\n\n### Regression Detection\nquality-runner full suite: 4884 passed, 258 failed, 0 errors, 4 skipped. Task-scoped files (`test_mcp_kanban.py`, `test_mcp_kanban_merge_1469.py`) — zero failures. Broad failure count (258) lower than reviewer baseline (260) and pre-task baseline (274). Ruff clean on task files. No task-introduced regressions.\n\n### Intent Verification\nAll changes confined to `tests/` domain (test file merge/delete only). 7 source files confirmed deleted via workspace search. Merge verification file `test_mcp_kanban_merge_1469.py` present. `test_kanban_topology_1439.py` untouched. No extraneous scope.\n\n### Architect Quality\nScore: 4/5. Cycle 1 had all-td:0 misjudgment causing builder pass-through with zero file changes (wasted cycle). Cycle 2 corrected cleanly: raised td to 1 for merge/delete AC lines, removed quality tag, documented known collisions (1 test name, 2 inter-source fixtures), and specified delta-based verification. Specific and complete for cycle 2.\n\n### Commit Integrity\nTest-writer RED commit `86b7eea9` and builder GREEN commit `37834406` both present, both reference #1469.\n\n### Deductions\nNone.\n\n### Confidence\n1.00\n\n### Action\nArchive.