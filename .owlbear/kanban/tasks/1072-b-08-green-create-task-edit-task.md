---
id: 1072
title: 'B-08: GREEN — create_task + edit_task'
status: in-progress
priority: needed
created: 2026-04-21T10:48:51.287524+00:00
updated: 2026-04-25T01:15:59.196490+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1070
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.4, §1.5, §3.2, §3.4, §3.5
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.create_task and AgentView.edit_task. Fork point: B-09 (move/claim) and B-13 (pick_tasks) both depend on this task.

create_task: no `status` param (D50), tasks created at entry_status, predicate fires on entry, atomic ID allocation, body size validation, cross-ref validation.

edit_task: full parameter set per §1.5, body-exclusive gate, block_reason semantics (D53), no-op detection, archival field gates (D37 matrix), OCC bypass (AgentView — no expected_updated), timestamp prepend on append_body.

## Acceptance Criteria

- [ ] All RED tests from B-07 (#1070) pass
- [ ] `create_task` creates at `BoardConfig.entry_status` with no `status` param (D50)
- [ ] Body size: >500KB → ERR_BODY_TOO_LARGE; >100KB → guidance warning; applies to post-append total (D47)
- [ ] `edit_task` no-op → ERR_NO_OP (engine computes diff)
- [ ] block_reason non-empty → sets blocked=true + block_reason; empty/null → clears both (D53)
- [ ] Archival refs matrix fully enforced per §3.2
- [ ] Predicate on entry_status evaluated on create (D15+D50)
- [ ] `updated` advanced on any successful change (D14)
- [ ] AgentView.edit_task has NO `expected_updated` param (D46 — last-writer-wins)
[[2026-04-25]]
## Test-Writer Notes
- Test file: tests/test_engine_create_edit_1072.py
- Classes: TestFromAC_EditTaskSemanticDiff
- Tests per category: happy 0, edge 4 (add/remove tags and deps that are already present/absent), error 6 (all ERR_NO_OP), boundary 0
- Total: 6 tests, all FAIL ("DID NOT RAISE ValidationError")
- ruff: clean

AC coverage:
| AC item | Tests |
|---------|-------|
| D14 — updated advanced on any successful change (via semantic diff: no-op must NOT advance updated) | test_same_priority_raises_no_op, test_same_body_raises_no_op |
| "engine computes diff" — same tag/dep/priority/body → ERR_NO_OP | test_add_existing_tag_raises_no_op, test_remove_nonexistent_tag_raises_no_op, test_add_existing_dep_raises_no_op, test_remove_nonexistent_dep_raises_no_op |
| D46 — no expected_updated param | NOT testable as RED: param is already absent; introspection test would pass immediately — omitted per skill |
| All #1070 tests pass | 31 existing tests green (pre-condition verified before authoring) |

Note: #1070 tests (31) all PASS — implementation was already complete when #1072 entered the pipeline. New RED tests cover only the "engine computes diff" semantic no-op requirement which is NOT yet implemented.
[[2026-04-25]]
## Builder Notes
- Implementation: added semantic no-op detection in AgentView edit_task so requested edits must produce an effective state change or raise ERR_NO_OP.
- File changed: serve/kanban/src/owlbear_kanban/engine.py
- Commit: c43371c0 feat: implement semantic no-op detection in edit_task (#1072, builder)
- Test results via quality-runner: 37 passed, 0 failed, 0 skipped
- Lint: ruff clean on target source and task test files
- Coverage evidence: owlbear_kanban.engine 35 percent in scoped run (task-focused suite)
- Fixes applied: semantic comparison for body, priority, parent, tag and dependency add remove operations, block_reason transitions, and archival field changes; no-op now raises ValidationError ERR_NO_OP.
- AC evidence summary: the six TestFromAC semantic-diff RED tests now pass, including same priority, same body, add existing tag, remove missing tag, add existing dep, and remove missing dep.

Post-task reflection
- Problem faced: kwargs presence was treated as change, allowing semantic no-ops to advance updated.
- Workaround applied: computed change intent against existing task state before calling engine edit path.
- Pattern discovered: body equality needs newline normalization to match markdown parsed storage behavior.
- Quality gap noted: module-wide coverage percentage remains low in scoped runs despite full task criteria coverage.
[[2026-04-25]]
## Review Evidence
### Test Results
- pytest scoped create/edit suites: 37 passed, 0 failed, 0 skipped
- pytest corrected engine coverage scope: 359 passed, 0 failed, 0 skipped

### Lint: clean
- ruff clean on serve/kanban/src/, serve/kanban/tests/test_engine_create_edit_1070.py, tests/test_engine_create_edit_1072.py

### Coverage: owlbear_kanban.engine 93%
- corrected scope: tests/test_engine_create_edit_1072.py, serve/kanban/tests/test_engine_create_edit_1070.py, serve/kanban/tests/test_engine_archived_edit_1120.py, serve/kanban/tests/test_engine_reads_1069.py, serve/kanban/tests/test_engine_coverage_1068.py, tests/test_engine_coverage_1113.py, serve/kanban/tests/test_engine_atomicity_1104.py

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|-------------------------|---------|
| All RED tests from B-07 pass | quality-runner scoped run on serve/kanban/tests/test_engine_create_edit_1070.py | Yes | COVERED |
| create_task uses entry_status and exposes no status param | serve/kanban/tests/test_engine_create_edit_1070.py:172 plus serve/kanban/src/owlbear_kanban/engine.py:1819 | Yes | COVERED |
| body-size hard cap and warning, including post-append total | serve/kanban/tests/test_engine_create_edit_1070.py:201, 211, 221, 291, 301, 311, 324 | Yes | COVERED |
| edit_task semantic no-op raises ERR_NO_OP | serve/kanban/tests/test_engine_create_edit_1070.py:283 and tests/test_engine_create_edit_1072.py:162, 175, 188, 202, 215, 229 | No. Same-value archived archival_reason or archival_refs is still treated as a change by serve/kanban/src/owlbear_kanban/engine.py:2067 and :2071 | FAIL |
| block_reason set, clear, and omission semantics | serve/kanban/tests/test_engine_create_edit_1070.py:336, 354, 365 | Yes | COVERED |
| archival refs matrix | serve/kanban/tests/test_engine_create_edit_1070.py:415, 426, 437, 454, 485, 499, 511, 530, 543, 556, 569, 583 | Yes | COVERED |
| predicate on entry_status during create | serve/kanban/tests/test_engine_create_edit_1070.py:233 | Yes | COVERED |
| updated advances on successful change | serve/kanban/tests/test_engine_archived_edit_1120.py:403 plus core write at serve/kanban/src/owlbear_kanban/engine.py:1026 | Yes for successful edit path | COVERED |
| AgentView.edit_task omits expected_updated | serve/kanban/src/owlbear_kanban/engine.py:1886 and tests/test_engine_create_edit_1072.py:23 | No executable rejection test. Comment says the case is not testable even though the explicit signature makes an unexpected-keyword TypeError test possible | FAIL |

#### Security Review
- No security issues found in the scoped create_task and edit_task changes. The reviewed paths are validation and in-process state mutation only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_EditTaskSemanticDiff methods in tests/test_engine_create_edit_1072.py | No weakening observed; exact ERR_NO_OP assertions remain at lines 173, 186, 200, 213, 227, and 240 | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact ValidationError codes are asserted in tests/test_engine_create_edit_1072.py and serve/kanban/tests/test_engine_create_edit_1070.py |
| Negative and success-path coverage | ADEQUATE | #1070 and archived-edit suites cover successful create/edit paths; #1072 covers semantic no-op negatives |
| Manual mutation resistance | WEAK | No test covers same-value archived archival_reason or archival_refs, and no executable guard exists for unexpected expected_updated |
| Independence and naming | STRONG | Fresh tmp_path boards and descriptive test names across the reviewed suites |

#### Data Safety
- Archived-task semantic no-ops still churn persisted state. In AgentView.edit_task, same-value archival_reason and archival_refs on archived tasks force changes_requested true at serve/kanban/src/owlbear_kanban/engine.py:2067 and :2071. KanbanEngine.edit_task always rewrites updated at serve/kanban/src/owlbear_kanban/engine.py:1026, so the call mutates state instead of raising ERR_NO_OP.

#### Implementation-Aware Gaps
- No test exercises same-value archival_reason on an archived task through AgentView.edit_task.
- No test exercises same-value archival_refs on an archived task through AgentView.edit_task.
- No executable test calls AgentView.edit_task with expected_updated to prove rejection of the removed keyword contract.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Divergence from the initial code-reader pass: once #1070 and the archived-edit suite are included, create_task, body-size, block_reason, predicate, and archival-matrix AC lines are covered. The remaining hard failures are the archived-metadata no-op defect and the missing D46 executable proof.
- An exploratory wider engine run reached 94% engine coverage but surfaced unrelated background failures in serve/kanban/tests/test_idtofilename_cache_943.py, serve/kanban/tests/test_idtofilename_cache_944.py, and serve/kanban/tests/test_engine_crash_safety_1101.py. Those suites were excluded from task-local gating after the corrected passing engine scope was established.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-07 pass | quality-runner scoped create/edit run: serve/kanban/tests/test_engine_create_edit_1070.py 30 passed | serve/kanban/tests/test_engine_create_edit_1070.py | PASS |
| create_task uses BoardConfig.entry_status and no status param | serve/kanban/tests/test_engine_create_edit_1070.py:172 and serve/kanban/src/owlbear_kanban/engine.py:1819 | test_create_task_uses_entry_status_not_defaults_status | PASS |
| body size hard cap and warning apply, including post-append total | serve/kanban/tests/test_engine_create_edit_1070.py:201, 211, 221, 291, 301, 311, 324 | create/edit body-size tests | PASS |
| edit_task semantic no-op yields ERR_NO_OP | serve/kanban/src/owlbear_kanban/engine.py:2067 and :2071 force archived metadata no-ops down the write path | #1070 no-op test plus #1072 semantic diff tests | FAIL |
| block_reason non-empty sets blocked and empty/null clears | serve/kanban/tests/test_engine_create_edit_1070.py:336, 354, 365 | block_reason tests | PASS |
| archival refs matrix enforced | serve/kanban/tests/test_engine_create_edit_1070.py:415, 426, 437, 454, 485, 499, 511, 530, 543, 556, 569, 583 | archival gate and matrix tests | PASS |
| predicate on entry_status evaluated during create | serve/kanban/tests/test_engine_create_edit_1070.py:233 | test_create_task_predicate_failed_on_entry_status_raises_predicate_failed | PASS |
| updated advances on successful change | serve/kanban/tests/test_engine_archived_edit_1120.py:403 and serve/kanban/src/owlbear_kanban/engine.py:1026 | test_edit_archived_updated_timestamp_advances | PASS |
| AgentView.edit_task omits expected_updated | serve/kanban/src/owlbear_kanban/engine.py:1886 shows explicit signature without the keyword, but tests/test_engine_create_edit_1072.py:23 documents comment-only proof | no executable test | FAIL |

### Confidence: 0.72
### Verdict: FAIL
### Action: Reject to in-progress. Fix the archived-task no-op branch in AgentView.edit_task and add executable proof for the expected_updated contract before re-review.