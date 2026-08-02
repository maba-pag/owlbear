---
id: 1342
title: Curate stale pick_tasks RED suite after clarity-gate integration
status: archived
priority: medium
created: 2026-05-04T15:10:47.698484+00:00
updated: 2026-05-05T11:42:05.683636+00:00
tags:
- sync-blocker
- kanban
- test
parent:
depends_on:
- 1343
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The older `serve/kanban/tests/test_engine_pick_tasks_1074.py` suite is stale after TDD and clarity gates were integrated into dispatch. Many failures are caused by fixtures that no longer satisfy current dispatch eligibility, not by proven wave-assembly bugs.

`pick_tasks()` remains deployment-critical because it decides what work agents can start, but builders must repair the stale test layer before changing the algorithm.

**Failure modes in the stale suite (multi-modal):**
- Clarity gate: `_TASK_TMPL` uses `Body text.` — no bullets/numbered lines. All `status="todo"` and `status="review"` fixtures fail `_passes_clarity_gate`.
- Superseded assertions: some tests assert prior behavior (e.g., "research status excluded" which was correct pre-port but current `pick_tasks` includes all non-terminal statuses).
- Valid algorithm contracts: sort order (priority_rank ASC, age DESC, id ASC), dep_status strings, dep-disjointness, and bucket compatibility tests that need clarity-compliant fixtures but test correct current behavior.

## Acceptance Criteria

1. Audit every failing test in `serve/kanban/tests/test_engine_pick_tasks_1074.py` against the current clarity/TDD dispatch contract. (td:2)
2. Fixtures intended to reach wave assembly include bullet or numbered AC lines (matching `_AC_PATTERN = r"(?m)^\s*(-\s|\d+\.\s)"`). (td:2)
3. Tests that contradict the current dispatch contract (e.g., asserting research-status exclusion or agent-string truncation) are rewritten to match current behavior or deleted with rationale. (td:2)
4. After fixture repair, any remaining failure is isolated as a focused algorithm contract with a clarity-compliant fixture. (td:2)
5. `tests/test_dispatch_gate_port_1214.py` remains green. (td:1)
6. No algorithm changes to `agent_view.py` or `dispatch.py` unless a live failure remains after stale fixtures are corrected. (td:0)

## Key Files

- `serve/kanban/src/owlbear_kanban/agent_view.py` — `pick_tasks()` implementation with gate integration
- `serve/kanban/src/owlbear_kanban/dispatch.py` — `_passes_clarity_gate`, `_passes_tdd_gate`, `_AC_PATTERN`
- `serve/kanban/tests/test_engine_pick_tasks_1074.py` — stale test suite (target of curation)
- `tests/test_dispatch_gate_port_1214.py` — regression guard (must stay green)

## Audit Evidence

- `serve/kanban/tests/test_engine_pick_tasks_1074.py` currently has failing tests, but many fixtures use prose-only task bodies and are now correctly excluded by the clarity gate.
- The newer clarity/TDD dispatch suite `tests/test_dispatch_gate_port_1214.py` passes 21/21, including a clarity-compliant bucket-compatibility regression.
- Current `AgentView.pick_tasks()` already delegates to dispatch TDD/clarity predicates and implements wave size, direct dependency-edge disjointness, and symmetric bucket compatibility.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Curate one stale test file against current contract |
| Interface clarity | PASS | AC specifies exact regex pattern, exact files, clear pass/fail criteria |
| Dependency correctness | PASS | Task 1343 archived (done) — dependency satisfied |
| Module layering | PASS | Test-only changes, no production imports affected |
| TDD compliance | PASS | Task IS test curation; tagged `test` for pass-through |
| KISS/YAGNI | PASS | Minimal scope: fix fixtures, don't change algorithm |
| Premise challenge | PASS | Stale tests mask real signal; curation is necessary before algorithm work |
| Pattern consistency | PASS | Follows existing test fixture patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Challenge Results

- Challenger: reconsider (confidence 0.68)
- Key concerns: (1) AC3 was anticipatory (no in-progress fixtures in file), (2) multi-modal failure modes beyond clarity gate, (3) sort/dep_status contracts not covered by 1214
- Architect response: accepted partially — removed AC3 (trivially satisfied), expanded context section to document all failure modes, kept AC4+AC5 which already handle the broader failure categories. Valid algorithm contracts (sort, dep_status) are handled by AC4 ("remaining failure isolated as focused algorithm contract").

### Test Depth

- Max depth: 2
- Test-writer: SKIP (tagged `test` — pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC (removed trivially-satisfied AC3, added explicit _AC_PATTERN reference, expanded failure mode documentation, annotated test depths), tagged `test` for pass-through, advanced to todo.

## Source

Deployment audit reconciliation, 2026-05-04.
[[2026-05-05]]
Architecture review complete. Refined AC: removed trivially-satisfied AC3 (no in-progress fixtures exist in file), added explicit _AC_PATTERN regex reference in AC2, expanded context with multi-modal failure documentation, annotated test depths. Tagged `test` for test-writer pass-through. Challenger raised valid concern about narrowing root cause to clarity-only — addressed by documenting all three failure modes (clarity gate, superseded assertions, valid algorithm contracts) and showing AC3+AC4 cover the full scope.
[[2026-05-05]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Task is test suite curation: audit and repair existing fixtures in `serve/kanban/tests/test_engine_pick_tasks_1074.py` against the current clarity/TDD dispatch contract.
- Architecture review explicitly annotated: "Test-writer: SKIP (tagged `test` — pass-through)".
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- No files changed (builder does not edit tests).
- Scoped quality evidence shows the stale suite remains red after pass-through handoff.
- Test results: 27 passed, 16 failed.
- Failed tests are all in `serve/kanban/tests/test_engine_pick_tasks_1074.py` and map to AC curation targets (clarity fixtures/superseded assertions/isolated algorithm contracts).
- Lint: clean (`ruff` 0) for scoped files.
- Coverage snapshot (informational): `owlbear_kanban.agent_view` 30%, `owlbear_kanban.dispatch` 57% from failing run.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Curate stale fixtures in the pick_tasks RED suite to satisfy the current clarity/TDD dispatch contract, then rerun scoped tests to green. | serve/kanban/tests/test_engine_pick_tasks_1074.py | quality-runner scoped report: 16 failures including `TestFromAC_PickTasksSort::test_sort_priority_rank_age_desc_id_asc_combined`, `TestFromAC_PickTasksWaveAssembly::test_incompatible_agent_buckets_go_to_different_waves`, `TestFromAC_PickTasksAgent::test_agent_is_full_agent_map_value_not_first_character` |
| 2 | test-writer | Keep the dispatch gate regression green while curating the stale suite. | tests/test_dispatch_gate_port_1214.py | quality-runner scoped run: this file passed while stale suite failed (split indicates stale-test debt localized to pick_tasks suite) |
[[2026-05-05]]
## Test-Writer Notes
- Retry: curated stale fixture in `serve/kanban/tests/test_engine_pick_tasks_1074.py`.
- Root cause: `_TASK_TMPL` body was `Body text.` (prose-only) — fails `_passes_clarity_gate` for all tasks in `_CLARITY_STATUSES = {"todo", "in-progress", "review", "docs", "done"}`.
- Fix: changed template body from `Body text.` to `- AC item.` (one bullet line), satisfying `_AC_PATTERN = r"(?m)^\s*(-\s|\d+\.\s)"`.
- Scope: 1 line changed in test fixture template; no production code touched.
- Result: 22/22 in stale suite (16 formerly failing → green); `tests/test_dispatch_gate_port_1214.py` 21/21 still green. Total: 43 passed, 0 failed.
- AC coverage: AC1 ✓ (audited all failures — single root cause), AC2 ✓ (fixtures now carry bullet AC lines), AC4 ✓ (no remaining algorithm failures), AC5 ✓ (dispatch gate stays green), AC6 ✓ (no production code changed).
- Commit: 546bc901
[[2026-05-05]]
## Builder Notes
- Non-implementation task confirmed (test-curation handoff completed by test-writer retry).
- Files changed by builder: none.
- Scoped quality evidence:
  - `serve/kanban/tests/test_engine_pick_tasks_1074.py`: 22 passed, 0 failed.
  - `tests/test_dispatch_gate_port_1214.py`: 21 passed, 0 failed.
  - Combined scoped tests: 43 passed, 0 failed.
- Lint: clean (`ruff` violations: 0) on scoped files.
- Coverage (informational, scoped run): `owlbear_kanban.agent_view` 31%, `owlbear_kanban.dispatch` 57%.
- AC evidence summary: fixture curation is green, dispatch-gate regression remains green, and no production algorithm changes were required.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run: `serve/kanban/tests/test_engine_pick_tasks_1074.py` 22 passed, 0 failed; `tests/test_dispatch_gate_port_1214.py` 21 passed, 0 failed; combined 43 passed, 0 failed, 0 skipped.
- No failing scoped tests remained after the fixture repair.

### Lint Results
- Ruff clean for `serve/kanban/tests/test_engine_pick_tasks_1074.py`, `tests/test_dispatch_gate_port_1214.py`, `serve/kanban/src/owlbear_kanban/agent_view.py`, and `serve/kanban/src/owlbear_kanban/dispatch.py`.

### Coverage
- Informational only for this test-curation task: `owlbear_kanban.agent_view` 31%, `owlbear_kanban.dispatch` 57%.
- No task-owned production diff was proven, so module percentages are residual context rather than a gate on this review.

### Code Review
- `serve/kanban/tests/test_engine_pick_tasks_1074.py:143` now injects `- AC item.` into `_TASK_TMPL`, which satisfies the live clarity contract at `serve/kanban/src/owlbear_kanban/dispatch.py:52` and `serve/kanban/src/owlbear_kanban/dispatch.py:108`.
- The curated suite still proves current behavior directly: exact sort contract at `serve/kanban/tests/test_engine_pick_tasks_1074.py:290`, non-todo status inclusion at `serve/kanban/tests/test_engine_pick_tasks_1074.py:427`, full agent-string mapping at `serve/kanban/tests/test_engine_pick_tasks_1074.py:460`, and archived-dependency behavior at `serve/kanban/tests/test_engine_pick_tasks_1074.py:515`, `:531`, and `:542`.
- Live source still supports those contracts: `AgentView.pick_tasks()` filters `dep_status != "blocked"` and delegates TDD/clarity checks at `serve/kanban/src/owlbear_kanban/agent_view.py:406`, `:409`, `:410`, `:420`, and `:422`; ordering and dispatch entry construction remain at `serve/kanban/src/owlbear_kanban/agent_view.py:437`, `:438`, and `:519`; archival dependency mapping keeps `dropped`/`wontfix -> blocked` and `deprecated`/`duplicate -> redirect` at `serve/kanban/src/owlbear_kanban/engine.py:508`.
- code-reader flagged weak negative-only assertions in the pre-existing adjacent regression suite `tests/test_dispatch_gate_port_1214.py` at `:250/:277`, `:341/:367`, `:371/:397`, and `:511/:541`. I treated that as non-blocking adjacent-suite debt because AC5 only requires that file remain green, not that task 1342 rewrite it, and no task-owned change to 1214 was independently proven.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Audit every failing test in `serve/kanban/tests/test_engine_pick_tasks_1074.py` against the current clarity/TDD dispatch contract. | quality-runner shows 1074 green (22/22); repaired shared fixture at `serve/kanban/tests/test_engine_pick_tasks_1074.py:143` re-enables the formerly red sort/wave/agent/dependency tests, including `:290`, `:427`, and `:460`. | PASS |
| 2. Fixtures intended to reach wave assembly include bullet or numbered AC lines. | `_TASK_TMPL` now contains `- AC item.` at `serve/kanban/tests/test_engine_pick_tasks_1074.py:143`, matching `_AC_PATTERN` at `serve/kanban/src/owlbear_kanban/dispatch.py:52` and `_passes_clarity_gate()` at `serve/kanban/src/owlbear_kanban/dispatch.py:108`. | PASS |
| 3. Tests that contradict the current dispatch contract are rewritten to match current behavior or deleted with rationale. | Live suite now asserts current behavior: research status inclusion at `serve/kanban/tests/test_engine_pick_tasks_1074.py:427`, full agent string at `serve/kanban/tests/test_engine_pick_tasks_1074.py:460`, and blocked/redirect archived-dep handling at `serve/kanban/tests/test_engine_pick_tasks_1074.py:515`, `:531`, and `:542`, with source support at `serve/kanban/src/owlbear_kanban/engine.py:508`. | PASS |
| 4. After fixture repair, any remaining failure is isolated as a focused algorithm contract with a clarity-compliant fixture. | There are no remaining scoped failures: quality-runner reports 43 passed, 0 failed overall, with 1074 at 22/22. | PASS |
| 5. `tests/test_dispatch_gate_port_1214.py` remains green. | quality-runner reports `tests/test_dispatch_gate_port_1214.py` 21 passed, 0 failed. | PASS |
| 6. No algorithm changes to `agent_view.py` or `dispatch.py` unless a live failure remains after stale fixtures are corrected. | The only task-linked commit independently proven in `.git/logs/HEAD:1969` is `546bc901736ca8b9ff1e4aa5225a88abf77dd6f9` with message `test: fix clarity-gate fixture in pick_tasks suite (#1342, test-writer)`. Current source inspection shows the live production contract intact and no task-owned production change evidence surfaced. | PASS |

### Deductions
- `-0.03` Full commit-diff reconstruction and `git status --porcelain` were not available from the tool surface, so immutability and dirty-scope checks rely on `.git/logs` plus direct file inspection rather than a commit diff.
- `-0.02` The adjacent 1214 regression file has pre-existing negative-only assertions that weaken its standalone proof value, but that debt is outside the owned 1074 curation change.

### Verdict
- PASS -> docs | confidence 0.93

### Action
- Advanced to docs.
[[2026-05-05]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task is test-only curation; no API/CLI/config/behavior changes. No IN-scope docs reference this test file. |
| 2 | Module docstrings | No | N/A | No production modules modified. `agent_view.py` and `dispatch.py` were referenced for verification only — no task-owned diff. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research phase doc produced. |
| 5 | Diagram maintenance (describes match) | No | N/A | No IN-scope diagram has a describes glob matching test files. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/tests/test_engine_pick_tasks_1074.py | OUT (test file) | N/A |
| tests/test_dispatch_gate_port_1214.py | OUT (test file) | N/A |
| serve/kanban/src/owlbear_kanban/agent_view.py | OUT (source, not changed) | N/A |
| serve/kanban/src/owlbear_kanban/dispatch.py | OUT (source, not changed) | N/A |

**No docs impact.** Task is test suite curation only — a single fixture line changed in a test file. No IN-scope documentation is affected.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task #1342)
[[2026-05-05]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| 1. Audit every failing test against current clarity/TDD contract | quality-runner full suite: 1074 not in 198 failures; reviewer mapped all formerly-failing tests to clarity-gate root cause | PASS |\n| 2. Fixtures include bullet or numbered AC lines | Spot-checked serve/kanban/tests/test_engine_pick_tasks_1074.py:143 -- template body is now `- AC item.` matching _AC_PATTERN | PASS |\n| 3. Tests contradicting current contract rewritten or deleted | Reviewer verified at :427 (research inclusion), :460 (full agent string), :515/:531/:542 (archived-dep handling) -- all assert current behavior | PASS |\n| 4. Remaining failures isolated as focused algorithm contracts | quality-runner: 0 failures in 1074 file (22/22 pass) | PASS |\n| 5. test_dispatch_gate_port_1214.py remains green | Not in quality-runner failure list (4565 passed includes it) | PASS |\n| 6. No algorithm changes to agent_view.py or dispatch.py | git show --stat 546bc901: 1 file changed (test file only), 1 insertion, 1 deletion | PASS |\n\n### Test Results\n- pytest full suite: 4565 passed, 198 failed, 4 skipped\n- 198 failures all in unrelated modules (test_server_1199, test_engine_create_edit_1203, test_pick_tasks_resolve_1184, test_decisions_1195, test_memory_tools_1272, test_engine_pick_tasks_1076, test_guidance_edit_task_973, test_cockpit_react_compiler_1015); no imports from 1074 confirmed\n- ruff: 12 violations all in serve/knowledge/ and serve/tools/ -- none in task-scoped files\n\n### Commit Integrity\n- 546bc901 test: fix clarity-gate fixture in pick_tasks suite (#1342, test-writer)\n- Scope: 1 file, 1 insertion, 1 deletion -- clean\n\n### Architect Quality: 4/5\nAC lines are specific (exact file, regex pattern, clear pass/fail). Challenger appropriately removed anticipatory AC3. Minor gap: could have explicitly listed the expected test count after curation.\n\n### Deduction Breakdown\n- No AC lines without evidence: 0\n- No lint violations in scope: 0\n- AC quality 4 (above 3): 0\n- Reviewer evidence present and detailed: 0\n- No full-suite failures in task scope: 0\n\n### Confidence: 1.00\n### Action: archive