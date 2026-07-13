---
id: 1476
title: 'P4-25: consolidation test: topology-constant regression remediation'
status: archived
priority: medium
created: 2026-05-09T08:46:53.962568+00:00
updated: 2026-05-10T18:18:57.355674+00:00
tags:
- phase-4
- type:test
- scope:tests
- topology
- consolidation-test
parent: 1439
depends_on:
- 1472
- 1473
- 1474
- 1475
- 1479
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context
Parent #1439 AC5 regression gate. All 4 category subtasks (#1472 Cat-A, #1473 Cat-B1, #1474 Cat-B2, #1475 Cat-C) plus #1479 triage must pass before this consolidation gate runs.

## Scope
In scope: bounded topology-domain test verification.
Out of scope: any test modifications (those are done by the category subtasks); failures outside the bounded pathset.

## Acceptance Criteria
1. Builder runs the bounded topology-verification pathset and confirms exit 0: `uv run pytest tests/test_kanban_topology_1439.py serve/kanban/tests/ tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py serve/mcp-kanban/tests/ --tb=short`. Pathset covers: task-scoped suite + Cat-A (#1472) + Cat-B1 (#1473) + Cat-C (#1475). Failures outside this pathset are not in scope. (td:0)

## Verification Method
Run the bounded pytest command above. Exit 0 = pass. Any failures within the pathset must be triaged as either pre-existing (documented) or requiring a follow-up remediation task.
[[2026-05-10]]
Architecture review (3rd pass). Replaced unverifiable AC1 ("no #1439-attributable failures" referencing nonexistent triage file) with machine-verifiable bounded pathset: `uv run pytest tests/test_kanban_topology_1439.py serve/kanban/tests/ tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py serve/mcp-kanban/tests/ --tb=short`. Covers task-scoped suite + Cat-A + Cat-B1 + Cat-C. Out-of-scope failures documented (accessor migration #1173/#1174, memory-tool API rename, cockpit tests). All 5 deps archived. td:0, test-writer SKIP, challenger waived.
[[2026-05-10]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-10]]
## Builder Notes
- Implementation: no code changes (td:0 consolidation verification task).
- Files changed: none.
- Tests: bounded topology pathset command passed with 1847 passed, 0 failed, exit 0.
- Coverage: not requested for this gate (`--cov` not part of AC command).
- Ruff: not run (no source/test modifications in scope).
- Evidence summary: executed required bounded command exactly as AC specifies: `uv run pytest tests/test_kanban_topology_1439.py serve/kanban/tests/ tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py serve/mcp-kanban/tests/ --tb=short`; result `1847 passed in 9.66s`.
[[2026-05-10]]
## Review Evidence
### Test Results
- Independent `quality-runner` bounded-pathset rerun on the AC1 scope (`tests/test_kanban_topology_1439.py`, `serve/kanban/tests/`, `tests/test_config_loader.py`, `tests/test_config_authority.py`, `tests/test_config_schema.py`, `tests/test_config_grouped.py`, `serve/mcp-kanban/tests/`) returned `1845 passed, 2 failed`, pytest exit `1`.
- The failing cases were `serve/kanban/tests/test_engine_crash_safety.py::TestFromAC_EngineCrashSafety::test_ac2_create_task_routes_through_allocate_next_id` and `serve/kanban/tests/test_engine_crash_safety.py::TestFromAC_EngineCrashSafety::test_ac3_create_task_contract_preserved_with_new_routing` (definitions at `serve/kanban/tests/test_engine_crash_safety.py:180` and `serve/kanban/tests/test_engine_crash_safety.py:207`).
- Independent `quality-runner` rerun of `serve/kanban/tests/test_engine_crash_safety.py` alone returned `4 passed`, pytest exit `0`.
- Independent second `quality-runner` rerun of the same full bounded pathset returned `1847 passed`, pytest exit `0`.
- Builder task notes claim the bounded command passed once with `1847 passed, 0 failed` at `.owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md:51`, and the builder scratch log shows the four crash-safety tests passing at `.owlbear/scratch/1476-pytest-output.log` around lines `8996-9016`.
- Static inspection shows `KanbanEngine.create_task()` still calls `storage.allocate_next_id(self._kanban_dir)` at `serve/kanban/src/owlbear_kanban/engine.py:1015`, so the first failing rerun is not explained by an obvious direct code-path removal.

### Lint Results
- Not requested / not run. This is a td:0 verification task with no builder-reported file changes (`.owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md:49`), and the `quality-runner` invocations used empty `lint_paths`.

### Coverage
- Informational only. The bounded-pathset runs reported ~70% overall coverage and the isolated crash-safety-file run reported 24% package coverage, but coverage is not a gate for this td:0 verification task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | The task requires the bounded topology-verification pathset to exit 0 at `.owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md:37` with the verification method immediately below. One independent rerun of that exact bounded scope exited `1` with two crash-safety failures, while a later rerun exited `0`. Because the same gate both failed and passed during review, the task does not prove a stable exit-0 regression gate. | FAIL |

### Deductions
- `-0.12` Gate nondeterminism: the same bounded pathset produced both exit `1` and exit `0` during review.
- `-0.05` Evidence conflict: builder evidence and current reviewer evidence disagree on the same command surface.
- `-0.03` Root cause unresolved: the isolated crash-safety file passes, so the defect appears to be broader-suite interaction or state contamination rather than an obvious single-file regression.
- Builder process quality: CLEAN. No prior `## Review Evidence` section exists in the task file, so this is the first review failure.

### Verdict
- Confidence: `0.80`
- FAIL -> in-progress
- Reason: AC1 requires a repeatable bounded exit-0 gate, but the reviewer reproduced both a failing and a passing result on the same scope.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reproduce and eliminate the scope-sensitive crash-safety failure so the bounded topology pathset exits `0` consistently across repeated runs, not just a single pass. | serve/kanban/tests/test_engine_crash_safety.py; serve/kanban/tests/; .owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md | First bounded-pathset `quality-runner` rerun failed `test_ac2_create_task_routes_through_allocate_next_id` and `test_ac3_create_task_contract_preserved_with_new_routing`; second bounded-pathset rerun passed on the same scope. |
| 2 | builder | Capture the reproduction conditions for the broader-suite interaction in the task body or task-scoped scratch evidence so the next review can verify the nondeterminism was actually removed. | .owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md; .owlbear/scratch/1476-pytest-output.log | `serve/kanban/tests/test_engine_crash_safety.py` passed in isolation (`4 passed`) while the broader bounded run failed those same tests once and then passed on retry. |
[[2026-05-10]]
## Builder Notes
- Implementation: fixed stale storage-module reference in engine by resolving the live `owlbear_kanban.storage` module at call time, then using it for `allocate_next_id` and `write_task_if_unchanged` in the claim/create code paths.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`.
- Root cause addressed: `serve/kanban/tests/test_storage.py` pops/reimports `owlbear_kanban.storage`; engine previously held an older module object, so later patch-based tests in bounded pathset could miss calls (`call_count=0`) despite correct source logic.
- Tests (quality-runner, bounded AC pathset, run 1): 1847 passed, 0 failed, pytest exit 0.
- Tests (quality-runner, bounded AC pathset, run 2): 1847 passed, 0 failed, pytest exit 0.
- Coverage: not requested for this td:0 consolidation gate.
- Ruff/lint: not required for this gate (`lint_paths` intentionally empty); no additional lint issues reported by quality-runner.
- Commit: `bb325d67206394f477daea490c3c60291b9ddba1`.
- Evidence summary: bounded topology command now exits 0 repeatably across consecutive reruns, removing prior suite-order sensitivity involving crash-safety and start_work CAS tests.
[[2026-05-10]]
## Review Evidence
### Test Results
- Second-cycle review after one prior FAIL.
- Independent quality-runner reran the bounded AC1 pathset twice on the current workspace state. Run 1: 1847 passed, 0 failed, pytest exit 0. Run 2: 1847 passed, 0 failed, pytest exit 0.
- Independent quality-runner reran `serve/kanban/tests/test_engine_crash_safety.py`. Result: 4 passed, 0 failed, pytest exit 0.
- The same scoped run linted `serve/kanban/src/owlbear_kanban/engine.py`. Result: ruff exit 0, 0 violations.

### Lint Results
- Scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` was clean.
- No broader lint gate applies to this td:0 verification task.

### Coverage
- Not a gate for this task. AC1 is bounded-pathset exit 0 only.
- Informationally, the bounded rerun reported `serve/kanban/src/owlbear_kanban/engine.py` at 86% module coverage.

### Code Inspection
- The builder retry records the storage-module lookup fix in `.owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md:94` and commit `bb325d67206394f477daea490c3c60291b9ddba1` at line 101.
- `serve/kanban/src/owlbear_kanban/engine.py:129` defines `_storage_module()` to resolve the live `owlbear_kanban.storage` module.
- `serve/kanban/src/owlbear_kanban/engine.py:1021` routes `create_task()` ID allocation through the live module.
- `serve/kanban/src/owlbear_kanban/engine.py:1377` and `serve/kanban/src/owlbear_kanban/engine.py:1397` route the claim CAS writes through the live module.
- The fix is consistent with `serve/kanban/tests/test_storage.py:2031-2032`, which removes and re-imports `owlbear_kanban.storage`, and with the patch-based regression checks in `serve/kanban/tests/test_engine_crash_safety.py:180` and `serve/kanban/tests/test_engine_crash_safety.py:207` plus `serve/kanban/tests/test_engine_move_claim.py:626` and `serve/kanban/tests/test_engine_move_claim.py:647`.
- No task test-file change was disclosed, and no current evidence indicates weakened `TestFromAC_*` assertions. Direct commit diff was not available in this tool surface, so immutability confidence remains slightly reduced.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | The bounded topology pathset required at `.owlbear/kanban/tasks/1476-p4-25-consolidation-test-topology-constant-regression-remediation.md:37` was independently rerun twice after the builder retry. Both reruns exited 0 with 1847 passed and 0 failed. The previously sensitive crash-safety suite also passed independently (4 passed), and the touched engine module linted clean. | PASS |

### Deductions
- `-0.03` Commit-integrity / immutability deduction: I could confirm the builder commit exists in `.git/logs/HEAD:2540`, but this tool surface does not expose full `git diff` or `git status`, so changed-file immutability and dirty-tree contamination could not be proven as strongly as ideal.
- `-0.02` Root-cause certainty deduction: the live-module lookup fix matches the failing test pattern, but the exact earlier worker-order trigger was not replayed directly.

### Verdict
- Confidence: `0.95`
- PASS to docs.
- Reason: AC1 is now satisfied by repeatable reviewer reruns on the bounded pathset, and the touched engine path plus the previously unstable crash-safety regression file are green.
[[2026-05-10]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` describes `create_task` as "Allocate next ID and write a new task file" and `claim_task` as "Mark task claimed by this engine's agent_name; rejects blocked/rival claims" — both still accurate after the live-module lookup fix (internal mechanism changed, public contract unchanged). |
| 2 | Module docstrings | Yes | Verified | `_storage_module()` docstring: "Return the live storage module, even if tests force a re-import." — accurate. `create_task()` docstring says "ID allocation is delegated to `storage.allocate_next_id()`" — still accurate. `claim_task()` docstring is unchanged and correct. No edits needed. |
| 3 | External attribution | No | N/A | No external patterns or sources used. |
| 4 | Research doc | No | N/A | No research doc mentioned in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` describes `serve/kanban/src/**` — footer updated to `Last verified: 2026-05-10 (bb325d67)`. `share/diagrams/mcp-topology.excalidraw` also describes `serve/kanban/src/**` — footer updated to `Last verified: 2026-05-10 (bb325d67)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set (`serve/kanban/src/owlbear_kanban/engine.py` modified only). |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/engine.py | IN (docstrings) | Verified — docstrings accurate, no edits needed |
| share/diagrams/kanban.excalidraw | IN | Footer updated (describes match) |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated (describes match) |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-05-10 (bb325d67)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-05-10 (bb325d67)`
- Commit: `6c695462`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1476-*` scratch files found)
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: 4370 passed / 226 failed (Python), 1218 passed / 0 failed (frontend)
- 226 Python failures are all in non-kanban domains (cockpit NameErrors, mcp-memory import errors, vitest timeouts, stale task-scoped test references) — none attributable to #1476
- Independent bounded-pathset rerun: 1847 passed, 0 failed, exit 0
- Independent full kanban suite rerun: 1336 passed, 0 failed, exit 0
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (only file changed: `serve/kanban/src/owlbear_kanban/engine.py` — correct kanban domain, 10 insertions / 4 deletions)
- purpose match: PASS (live-module resolver for `owlbear_kanban.storage` fixes nondeterministic test-order sensitivity, matches stated task purpose)
- extraneous scope: none (3 call sites + 1 import + 1 helper function, all engine-internal)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was specific and machine-verifiable after 3rd-pass arch review (exact pytest command, exit 0 gate). Minor: required 3 arch iterations to replace unverifiable AC referencing a nonexistent triage file.

### Commit Integrity
- upstream commit presence: PASS (builder `bb325d67` — 1 file; docs `6c695462` — 2 diagram footers)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions. Full-suite failures are pre-existing in other domains; bounded pathset and kanban suite fully green; intent aligned; commits present.

### Confidence: 1.00
### Action: archive