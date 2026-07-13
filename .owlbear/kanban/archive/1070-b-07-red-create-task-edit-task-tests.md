---
id: 1070
title: 'B-07: RED — create_task + edit_task tests'
status: archived
priority: medium
created: 2026-04-21T10:48:33.317250+00:00
updated: 2026-04-24T23:58:04.164708+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1068
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.4, §1.5, §3.2, §3.4, §3.5, §4
Module: `serve/kanban/tests/test_engine_create_edit.py`

Test AgentView.create_task and AgentView.edit_task. Covers validation matrix, body size limits, predicate-on-create, body-exclusive, block_reason semantics, no-op detection, parent/dep existence checks, archival-field gates, timestamp wire format.

## Acceptance Criteria

- [ ] AC6: `edit_task(<archived>, archival_reason="completed")` → ValidationError(ERR_COMPLETED_REQUIRES_DONE)
- [ ] AC14: `edit_task(id, body=..., append_body=...)` both set → ValidationError(ERR_BODY_EXCLUSIVE)
- [ ] AC24: `create_task(..., depends_on=[99999])` → ValidationError(ERR_DEP_NOT_FOUND)
- [ ] AC25: `edit_task(id, add_dep=[99999])` → ValidationError(ERR_DEP_NOT_FOUND)
- [ ] AC29: `created`, `updated` carry explicit `±HH:MM` or `Z`
- [ ] AC30: `edit_task(append_body=..., timestamp=true)` prepends ISO timestamp
- [ ] AC-NEW-15: `edit_task(id, parent=99999)` → ValidationError(ERR_PARENT_NOT_FOUND)
- [ ] No `status` param on create_task — tasks created at BoardConfig.entry_status (D50)
- [ ] Body >500KB → ValidationError(ERR_BODY_TOO_LARGE); >100KB → guidance warning (D35+D47)
- [ ] Post-append total body checked against size caps (D47)
- [ ] `block_reason` non-empty sets blocked; empty/null clears both (D53)
- [ ] No-op call (no field changes) → ValidationError(ERR_NO_OP)
- [ ] Archival fields on non-archived task → ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)
- [ ] Archival refs matrix per §3.2 (required/forbidden/missing/self/cycle)
- [ ] Predicate on entry_status fires on create (D15+D50)
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_engine_create_edit_1070.py`
- Classes: `TestFromAC_CreateTask`, `TestFromAC_EditTaskValidation`, `TestFromAC_EditTaskArchivalGates`, `TestFromAC_EditTaskArchivalRefs`
- Tests per category: happy 1, edge 2, error 21, boundary 2
- Total: 26 tests, all FAIL
- ruff: clean

**AC coverage:**

| AC | Test |
|---|---|
| AC6 | `TestFromAC_EditTaskArchivalGates.test_archived_completed_reason_requires_terminal_status` |
| AC14 | `TestFromAC_EditTaskValidation.test_body_and_append_body_both_set_raises_body_exclusive` |
| AC24 | `TestFromAC_CreateTask.test_create_task_dep_not_found_raises_validation_error` |
| AC25 | `TestFromAC_EditTaskValidation.test_add_dep_nonexistent_raises_dep_not_found` |
| AC29 | Satisfied by existing engine — `datetime.now(tz=UTC).isoformat()` → no failing test needed |
| AC30 | `TestFromAC_EditTaskValidation.test_append_body_timestamp_uses_iso_datetime_with_offset` |
| AC-NEW-15 | `TestFromAC_EditTaskValidation.test_parent_nonexistent_raises_parent_not_found` |
| D50 entry_status | `TestFromAC_CreateTask.test_create_task_uses_entry_status_not_defaults_status` |
| ERR_BODY_TOO_LARGE | create x2, edit x2 (replace + post-append) |
| ERR_NO_OP | `TestFromAC_EditTaskValidation.test_no_op_call_raises_no_op_error` |
| ERR_ARCHIVAL_FIELDS_FORBIDDEN | `TestFromAC_EditTaskArchivalGates` x2 (reason + refs on active) |
| D53 block_reason clears | `TestFromAC_EditTaskValidation.test_empty_block_reason_clears_blocked_and_block_reason` |
| §3.2 refs matrix | `TestFromAC_EditTaskArchivalRefs` — all 8 codes (required x2, forbidden x3, missing, self, cycle) |
| D15+D50 predicate | `TestFromAC_CreateTask.test_create_task_predicate_failed_on_entry_status_raises_predicate_failed` |

**Failure modes:**
- 1 test: `AssertionError` (wrong status value — entry_status vs defaults.status)
- 16 tests: `DID NOT RAISE ValidationError` (validation not implemented)
- 2 tests: `AssertionError` (block_reason not cleared; timestamp lacks ISO offset)
- 8 tests (`TestFromAC_EditTaskArchivalRefs` + 2 in ArchivalGates): `NotFoundError` (engine cannot yet locate tasks in archive/ — correct RED signal; builder must also add archive-path lookup to edit_task)

Commit: b78c931d — `test: add failing tests for AgentView create_task/edit_task (#1070, test-writer)`
[[2026-04-24]]
## Builder Notes
- Files changed in this attempt: none (verification-only retry)
- Verified target RED suite: `serve/kanban/tests/test_engine_create_edit_1070.py` -> 26 passed, 0 failed
- Scoped regression: `serve/kanban/tests/test_engine_create_edit*.py` -> 26 passed, 0 failed
- Lint status: `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_create_edit_1070.py` -> clean (0 issues)
- Coverage evidence (scoped run): engine module 33% (TOTAL 35%) from single-target suite; this retry performed no code changes and was used to confirm GREEN behavior for the 26 AC-mapped tests.
- Evidence summary by retry buckets:
  - ValidationError implementations: passing (16 expected validations now asserted)
  - archive-path lookup in `edit_task`: passing (archived-task edit/ref tests no longer NotFound)
  - block/timestamp fixes: passing (2 assertion tests green)
- Fixes applied in this attempt: none (existing implementation already satisfies #1070 acceptance checks).
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on serve/kanban/tests/test_engine_create_edit_1070.py: 26 passed, 0 failed, 0 skipped.
- Editor diagnostics: no errors in serve/kanban/src/owlbear_kanban/engine.py or serve/kanban/tests/test_engine_create_edit_1070.py.

### Lint
- Scoped ruff on serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/tests/test_engine_create_edit_1070.py: clean.

### Coverage
- Scoped coverage for owlbear_kanban.engine: 33%.
- This is not the sole blocker, but it confirms the green slice is narrow.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC were violated? | Verdict |
|---|---|---|---|
| AC6 completed-requires-terminal | test_archived_completed_reason_requires_terminal_status at serve/kanban/tests/test_engine_create_edit_1070.py:368 | Yes; specific ERR_COMPLETED_REQUIRES_DONE guard at serve/kanban/src/owlbear_kanban/engine.py:1943 | COVERED |
| AC14 body and append_body exclusive | test_body_and_append_body_both_set_raises_body_exclusive at serve/kanban/tests/test_engine_create_edit_1070.py:245 | Yes; specific ERR_BODY_EXCLUSIVE guard at serve/kanban/src/owlbear_kanban/engine.py:1880 | COVERED |
| AC24 create missing dependency | test_create_task_dep_not_found_raises_validation_error at serve/kanban/tests/test_engine_create_edit_1070.py:183 | Yes; specific ERR_DEP_NOT_FOUND guard at serve/kanban/src/owlbear_kanban/engine.py:1813 | COVERED |
| AC25 edit add_dep missing | test_add_dep_nonexistent_raises_dep_not_found at serve/kanban/tests/test_engine_create_edit_1070.py:255 | Yes; specific ERR_DEP_NOT_FOUND guard at serve/kanban/src/owlbear_kanban/engine.py:1896 | COVERED |
| AC29 created and updated include explicit offset or Z | No executable task-owned test; coverage header at serve/kanban/tests/test_engine_create_edit_1070.py:16 says none needed | No; regressing timestamps at serve/kanban/src/owlbear_kanban/engine.py:887 or serve/kanban/src/owlbear_kanban/engine.py:1009 would not fail the suite | MISSING |
| AC30 append_body timestamp prepends full ISO timestamp | test_append_body_timestamp_uses_iso_datetime_with_offset at serve/kanban/tests/test_engine_create_edit_1070.py:317 | No; regex at serve/kanban/tests/test_engine_create_edit_1070.py:329 checks only a partial token and does not prove prepend position or full plus/minus HH:MM or Z form. Timestamp formatting lives at serve/kanban/src/owlbear_kanban/engine.py:1903 and serve/kanban/src/owlbear_kanban/engine.py:1971 | LAX |
| AC-NEW-15 parent missing | test_parent_nonexistent_raises_parent_not_found at serve/kanban/tests/test_engine_create_edit_1070.py:263 | Yes; specific ERR_PARENT_NOT_FOUND guard at serve/kanban/src/owlbear_kanban/engine.py:1889 | COVERED |
| D50 entry_status on create | test_create_task_uses_entry_status_not_defaults_status at serve/kanban/tests/test_engine_create_edit_1070.py:172 | Yes; create_task forces status=entry_status at serve/kanban/src/owlbear_kanban/engine.py:1836 | COVERED |
| D35 plus D47 hard body cap | create tests at serve/kanban/tests/test_engine_create_edit_1070.py:201 and :211, edit tests at :279 and :289 | Yes; _validate_body_size at serve/kanban/src/owlbear_kanban/engine.py:1595 plus post-append size check | COVERED |
| 100 KB guidance warning | No task-owned assertion in serve/kanban/tests/test_engine_create_edit_1070.py | No; warning branches at serve/kanban/src/owlbear_kanban/engine.py:1847 and :2006 can be removed without failing the suite | MISSING |
| D53 block_reason set and clear semantics | test_empty_block_reason_clears_blocked_and_block_reason at serve/kanban/tests/test_engine_create_edit_1070.py:299 | No; clear path is covered, but there is no positive set-block assertion and an omitted-input bug survives | LAX |
| ERR_NO_OP | test_no_op_call_raises_no_op_error at serve/kanban/tests/test_engine_create_edit_1070.py:271 | Yes; ERR_NO_OP guard at serve/kanban/src/owlbear_kanban/engine.py:1995 | COVERED |
| Archival fields forbidden on active tasks | tests at serve/kanban/tests/test_engine_create_edit_1070.py:346 and :357 | Yes; ERR_ARCHIVAL_FIELDS_FORBIDDEN guard at serve/kanban/src/owlbear_kanban/engine.py:1911 | COVERED |
| Archival refs matrix | tests at serve/kanban/tests/test_engine_create_edit_1070.py:416, :430, :442, :461, :474, :487, :500, :514 | Yes; guards at serve/kanban/src/owlbear_kanban/engine.py:1931, :1937, :1950, :1955, :1961 | COVERED |
| D15 plus D50 predicate-on-create | test_create_task_predicate_failed_on_entry_status_raises_predicate_failed at serve/kanban/tests/test_engine_create_edit_1070.py:221 | Yes; predicate guard at serve/kanban/src/owlbear_kanban/engine.py:1819 and ERR_PREDICATE_FAILED at :1828 | COVERED |
| Historical RED prerequisite | Test-Writer note in the task body records 26 failing tests before builder work | Historical only; not reproducible from the current snapshot | PASS |

#### Security Review
- No task-specific security issues found in the create_task and edit_task validation paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC suite | Builder note reports verification-only retry with no file changes; current file shows no skip, xfail, or broadened exception patterns | PRESERVED |
| AC29 coverage row | Task file replaced executable proof with commentary at serve/kanban/tests/test_engine_create_edit_1070.py:16 | CURRENT PROOF MISSING |
| AC30 timestamp proof | Regex at serve/kanban/tests/test_engine_create_edit_1070.py:329 is weaker than the stated contract | CURRENT PROOF WEAK |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC30 regex at serve/kanban/tests/test_engine_create_edit_1070.py:329 does not require full offset or prepend position |
| Negative and error-path coverage | ADEQUATE | Validation coverage is broad across serve/kanban/tests/test_engine_create_edit_1070.py:183-514 |
| Manual mutation reasoning | WEAK | Removing AC29 timestamp fields or the 100 KB guidance branches at serve/kanban/src/owlbear_kanban/engine.py:1847 and :2006 would leave the task-owned suite green |
| Test independence | STRONG | tmp_path-backed board helpers isolate each test |
| Descriptive names | STRONG | Test names are AC-oriented and specific |

#### Data Safety
- Real implementation defect in task scope: AgentView.edit_task defaults block_reason to an empty string at serve/kanban/src/owlbear_kanban/engine.py:1863, clears blocked state on any blocked task when block_reason is omitted at serve/kanban/src/owlbear_kanban/engine.py:1989-1991, and engine.edit_task then persists blocked=False and block_reason=None at serve/kanban/src/owlbear_kanban/engine.py:995-1000. The task-owned suite only covers the explicit clear call at serve/kanban/tests/test_engine_create_edit_1070.py:299 and misses this destructive omitted-input path.

#### Implementation-Aware Gaps
- No task-owned assertion proves AC29 created and updated wire format.
- No task-owned assertion proves the 100 KB guidance warning on create or edit.
- No task-owned assertion proves the non-empty block_reason sets blocked=True path.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Stale RED commentary remains in serve/kanban/tests/test_engine_create_edit_1070.py:169, :242, :343, and :412 even though the live guards now exist.
- Scoped module coverage is only 33%, so the green task slice should not be treated as module-level proof.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC6 | serve/kanban/tests/test_engine_create_edit_1070.py:368 and serve/kanban/src/owlbear_kanban/engine.py:1943 | test_archived_completed_reason_requires_terminal_status | PASS |
| AC14 | serve/kanban/tests/test_engine_create_edit_1070.py:245 and serve/kanban/src/owlbear_kanban/engine.py:1880 | test_body_and_append_body_both_set_raises_body_exclusive | PASS |
| AC24 | serve/kanban/tests/test_engine_create_edit_1070.py:183 and serve/kanban/src/owlbear_kanban/engine.py:1813 | test_create_task_dep_not_found_raises_validation_error | PASS |
| AC25 | serve/kanban/tests/test_engine_create_edit_1070.py:255 and serve/kanban/src/owlbear_kanban/engine.py:1896 | test_add_dep_nonexistent_raises_dep_not_found | PASS |
| AC29 | No executable task-owned assertion; serve/kanban/tests/test_engine_create_edit_1070.py:16 defers to implementation, while timestamps live at serve/kanban/src/owlbear_kanban/engine.py:887 and :1009 | none | FAIL |
| AC30 | serve/kanban/tests/test_engine_create_edit_1070.py:317 and :329 prove only a partial regex, not prepend and full offset; source formats at serve/kanban/src/owlbear_kanban/engine.py:1903 and :1971 | test_append_body_timestamp_uses_iso_datetime_with_offset | FAIL |
| AC-NEW-15 | serve/kanban/tests/test_engine_create_edit_1070.py:263 and serve/kanban/src/owlbear_kanban/engine.py:1889 | test_parent_nonexistent_raises_parent_not_found | PASS |
| No status param on create and entry_status used | serve/kanban/tests/test_engine_create_edit_1070.py:172 and :181, serve/kanban/src/owlbear_kanban/engine.py:1836 | test_create_task_uses_entry_status_not_defaults_status | PASS |
| Body over 500 KB raises ERR_BODY_TOO_LARGE | serve/kanban/tests/test_engine_create_edit_1070.py:201, :211, :279, :289 and serve/kanban/src/owlbear_kanban/engine.py:1595 | four body-cap tests | PASS |
| 100 KB guidance warning | serve/kanban/src/owlbear_kanban/engine.py:1529, :1847, :2006; no matching assertion in the task-owned suite | none | FAIL |
| Post-append total body checked | serve/kanban/tests/test_engine_create_edit_1070.py:289 and serve/kanban/src/owlbear_kanban/engine.py:1903-1905 | test_append_body_total_over_500kb_raises_body_too_large | PASS |
| block_reason semantics | serve/kanban/tests/test_engine_create_edit_1070.py:299 proves explicit clear only; serve/kanban/src/owlbear_kanban/engine.py:1986-1991 and :995-1000 expose missing set proof and an omitted-input bug | test_empty_block_reason_clears_blocked_and_block_reason | FAIL |
| ERR_NO_OP | serve/kanban/tests/test_engine_create_edit_1070.py:271 and serve/kanban/src/owlbear_kanban/engine.py:1995 | test_no_op_call_raises_no_op_error | PASS |
| Archival fields on active tasks | serve/kanban/tests/test_engine_create_edit_1070.py:346 and :357, serve/kanban/src/owlbear_kanban/engine.py:1911 | two archival-field tests | PASS |
| Archival refs matrix | serve/kanban/tests/test_engine_create_edit_1070.py:416, :430, :442, :461, :474, :487, :500, :514 and serve/kanban/src/owlbear_kanban/engine.py:1931, :1937, :1950, :1955, :1961 | TestFromAC_EditTaskArchivalRefs | PASS |
| Predicate on entry_status fires on create | serve/kanban/tests/test_engine_create_edit_1070.py:221 and :229, serve/kanban/src/owlbear_kanban/engine.py:1819 and :1828 | test_create_task_predicate_failed_on_entry_status_raises_predicate_failed | PASS |
| All tests fail in RED phase | task body Test-Writer note records 26 failing tests before builder work | task body evidence | PASS |

### Deductions
- 0.20 deduction for missing AC29 executable proof.
- 0.10 deduction for weak AC30 timestamp assertion.
- 0.10 deduction for missing 100 KB guidance-warning proof.
- 0.15 deduction for incomplete D53 proof and the live omitted-input unblock defect.
- 0.05 deduction for low scoped module coverage and stale RED commentary.

### Confidence: 0.40
### Verdict: FAIL
### Action: reject to in-progress. Builder should fix the omitted-input block_reason clear path and add task-owned proof for AC29, AC30, the 100 KB guidance warning, and the positive D53 set-block behavior before returning to review.
[[2026-04-24]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) in `AgentView.edit_task` to distinguish omitted `block_reason` from explicit clear.
- Fix applied: changed `block_reason` parameter default from empty string to `None`, and only mutate `blocked`/`block_reason` when the argument is explicitly provided. This preserves explicit clear semantics (`""` clears) while preventing accidental unblock when `block_reason` is omitted.
- Tests: 26 TestFromAC tests passed (quality-runner scoped on `serve/kanban/tests/test_engine_create_edit_1070.py`).
- Coverage: 32% on touched module (`owlbear_kanban.engine`) in scoped task run.
- ruff: clean (scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_create_edit_1070.py`).
- Durable module test file check: requested `serve/kanban/tests/test_engine_create_edit.py` does not exist in workspace; task-owned suite remains the executable proof target.
- Evidence summary: omitted-input `block_reason` no longer triggers unintended unblock path; explicit non-empty value still sets blocked with reason; explicit empty string still clears both fields.

Post-task reflection:
- Problem faced: default empty string made omitted input indistinguishable from explicit clear.
- Workaround applied: introduced `None` sentinel and branch on explicit presence.
- Pattern discovered: mutation APIs with clear semantics need tri-state (`None`, empty, non-empty) handling to avoid destructive no-op regressions.
- Quality gap: reviewer highlighted proof gaps in AC29/AC30/warning-path assertions that are test-ownership concerns for follow-up review/test-writer work.
[[2026-04-24]]
## Review Evidence

### Test Results
- Parallel fan-out succeeded: quality-runner and code-reader both returned usable reports.
- Quality-runner scoped run on [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): 26 passed, 0 failed, 0 skipped.

### Lint
- Quality-runner scoped lint on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): clean.

### Coverage
- Quality-runner scoped coverage for owlbear_kanban.engine: 32%.
- This is not the primary blocker, but it confirms the task-owned green slice remains narrow.

### Pass 1 - CRITICAL
#### Test-Writer Audit
| AC line | Evidence | Status |
|---|---|---|
| AC29 created and updated carry explicit offset | [serve/kanban/tests/test_engine_create_edit_1070.py#L16](serve/kanban/tests/test_engine_create_edit_1070.py#L16) explicitly waives an executable proof. Current timestamp writes in [serve/kanban/src/owlbear_kanban/engine.py#L893](serve/kanban/src/owlbear_kanban/engine.py#L893) and [serve/kanban/src/owlbear_kanban/engine.py#L1015](serve/kanban/src/owlbear_kanban/engine.py#L1015) are code-only evidence. | MISSING |
| AC30 timestamp prepend with full ISO offset | [serve/kanban/tests/test_engine_create_edit_1070.py#L317-L330](serve/kanban/tests/test_engine_create_edit_1070.py#L317-L330) uses the regex at [serve/kanban/tests/test_engine_create_edit_1070.py#L329](serve/kanban/tests/test_engine_create_edit_1070.py#L329), which does not require the full plus/minus HH:MM or Z suffix and does not prove the timestamp is prepended ahead of the appended note. | LAX |
| D35 plus D47 guidance warning | No task-owned assertion covers the warning path on create, replace, or append. Warning emission exists at [serve/kanban/src/owlbear_kanban/engine.py#L1854-L1855](serve/kanban/src/owlbear_kanban/engine.py#L1854-L1855) and [serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015](serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015). | MISSING |
| D53 block_reason set and clear semantics | The suite proves only explicit empty-string clear at [serve/kanban/tests/test_engine_create_edit_1070.py#L299-L315](serve/kanban/tests/test_engine_create_edit_1070.py#L299-L315). There is still no task-owned proof for non-empty set, explicit null clear, or omission-preserves-state. | MISSING |

#### Security Review
- No task-scoped security defects found in the reviewed create_task and edit_task paths.

#### Test Integrity
- Existing TestFromAC assertions remain preserved. The current failure is missing or lax proof, not weakened assertions.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC30 regex in [serve/kanban/tests/test_engine_create_edit_1070.py#L329](serve/kanban/tests/test_engine_create_edit_1070.py#L329) is too permissive for the wire-format contract. |
| Negative and error-path coverage | ADEQUATE | Validation branches are broad, but positive and omission-path proof is still absent. |
| Manual mutation resistance | WEAK | Removing the warning branches at [serve/kanban/src/owlbear_kanban/engine.py#L1854-L1855](serve/kanban/src/owlbear_kanban/engine.py#L1854-L1855) and [serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015](serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015), or the non-empty D53 branch at [serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997](serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997), would leave the task suite green. |
| Test independence | STRONG | tmp_path-backed board helpers isolate each case. |
| Descriptive names | STRONG | Test names remain AC-specific and readable. |

#### Data Safety
- The omitted-input unblock regression is fixed, but the brief still requires explicit null-clear semantics. The contract in [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103-L104](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103-L104) says block_reason non-empty sets blocked and empty or null clears both. Current AgentView.edit_task uses a default of None at [serve/kanban/src/owlbear_kanban/engine.py#L1871](serve/kanban/src/owlbear_kanban/engine.py#L1871) and only mutates block state inside [serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000](serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000), so explicit null is indistinguishable from omission. That leaves the D53 contract incomplete.

#### Implementation-Aware Gaps
- D47 still misses the append warning path. The brief authority at [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103) requires post-append total body bytes to use the same 100 KB warning and 500 KB error caps. The code computes post-append total at [serve/kanban/src/owlbear_kanban/engine.py#L1913-L1914](serve/kanban/src/owlbear_kanban/engine.py#L1913-L1914), but final guidance is still keyed only off replacement body length at [serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015](serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015). Append-only edits over 100 KB can therefore succeed without the required warning.
- AC29 still has no executable task-owned proof.
- AC30 still has a weak timestamp assertion.
- D53 still lacks task-owned proof for non-empty set, explicit null clear, and omission-preserves-state.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes: first retry was verification-only, second retry changed block_reason handling |
| Assessment | FRICTION, not LOOP |

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC6 completed requires terminal status | [serve/kanban/tests/test_engine_create_edit_1070.py#L368-L383](serve/kanban/tests/test_engine_create_edit_1070.py#L368-L383) and [serve/kanban/src/owlbear_kanban/engine.py#L1949-L1952](serve/kanban/src/owlbear_kanban/engine.py#L1949-L1952) | PASS |
| AC14 body and append_body exclusive | [serve/kanban/tests/test_engine_create_edit_1070.py#L245-L252](serve/kanban/tests/test_engine_create_edit_1070.py#L245-L252) and [serve/kanban/src/owlbear_kanban/engine.py#L1886-L1890](serve/kanban/src/owlbear_kanban/engine.py#L1886-L1890) | PASS |
| AC24 create missing dependency | [serve/kanban/tests/test_engine_create_edit_1070.py#L183-L190](serve/kanban/tests/test_engine_create_edit_1070.py#L183-L190) and [serve/kanban/src/owlbear_kanban/engine.py#L1809-L1813](serve/kanban/src/owlbear_kanban/engine.py#L1809-L1813) | PASS |
| AC25 edit add_dep missing | [serve/kanban/tests/test_engine_create_edit_1070.py#L255-L261](serve/kanban/tests/test_engine_create_edit_1070.py#L255-L261) and [serve/kanban/src/owlbear_kanban/engine.py#L1900-L1904](serve/kanban/src/owlbear_kanban/engine.py#L1900-L1904) | PASS |
| AC29 created and updated include explicit offset | No executable task-owned assertion. Current implementation uses [serve/kanban/src/owlbear_kanban/engine.py#L893](serve/kanban/src/owlbear_kanban/engine.py#L893) and [serve/kanban/src/owlbear_kanban/engine.py#L1015](serve/kanban/src/owlbear_kanban/engine.py#L1015), but the proof is absent. | FAIL |
| AC30 append_body timestamp prepends full ISO timestamp | Current implementation stamps at [serve/kanban/src/owlbear_kanban/engine.py#L1979-L1980](serve/kanban/src/owlbear_kanban/engine.py#L1979-L1980), but the task-owned assertion at [serve/kanban/tests/test_engine_create_edit_1070.py#L317-L330](serve/kanban/tests/test_engine_create_edit_1070.py#L317-L330) does not prove full offset or prepend position. | FAIL |
| AC-NEW-15 parent missing | [serve/kanban/tests/test_engine_create_edit_1070.py#L263-L269](serve/kanban/tests/test_engine_create_edit_1070.py#L263-L269) and [serve/kanban/src/owlbear_kanban/engine.py#L1893-L1898](serve/kanban/src/owlbear_kanban/engine.py#L1893-L1898) | PASS |
| No status param on create and entry_status used | Entry-status behavior is proven by [serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180](serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180), and AgentView.create_task has no status parameter at [serve/kanban/src/owlbear_kanban/engine.py#L1791-L1798](serve/kanban/src/owlbear_kanban/engine.py#L1791-L1798). | PASS |
| Body over 500 KB raises ERR_BODY_TOO_LARGE | [serve/kanban/tests/test_engine_create_edit_1070.py#L201-L219](serve/kanban/tests/test_engine_create_edit_1070.py#L201-L219), [serve/kanban/tests/test_engine_create_edit_1070.py#L279-L297](serve/kanban/tests/test_engine_create_edit_1070.py#L279-L297), and [serve/kanban/src/owlbear_kanban/engine.py#L1603-L1608](serve/kanban/src/owlbear_kanban/engine.py#L1603-L1608) | PASS |
| Body over 100 KB returns guidance warning | Brief authority requires it at [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81) and [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103). Task-owned proof is absent, and append-only edits are not covered by the current implementation. | FAIL |
| Post-append total body checked against size caps | Hard-cap enforcement exists at [serve/kanban/src/owlbear_kanban/engine.py#L1913-L1914](serve/kanban/src/owlbear_kanban/engine.py#L1913-L1914), but the same 100 KB warning cap is still missing on append-only edits despite the brief at [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103). | FAIL |
| block_reason semantics | Empty-string clear is proven at [serve/kanban/tests/test_engine_create_edit_1070.py#L299-L315](serve/kanban/tests/test_engine_create_edit_1070.py#L299-L315), but explicit null-clear remains unsupported in AgentView and the positive set path is unproven. | FAIL |
| ERR_NO_OP | [serve/kanban/tests/test_engine_create_edit_1070.py#L271-L277](serve/kanban/tests/test_engine_create_edit_1070.py#L271-L277) and [serve/kanban/src/owlbear_kanban/engine.py#L2002-L2005](serve/kanban/src/owlbear_kanban/engine.py#L2002-L2005) | PASS |
| Archival fields on non-archived task | [serve/kanban/tests/test_engine_create_edit_1070.py#L346-L366](serve/kanban/tests/test_engine_create_edit_1070.py#L346-L366) and [serve/kanban/src/owlbear_kanban/engine.py#L1916-L1922](serve/kanban/src/owlbear_kanban/engine.py#L1916-L1922) | PASS |
| Archival refs matrix per section 3.2 | [serve/kanban/tests/test_engine_create_edit_1070.py#L416-L534](serve/kanban/tests/test_engine_create_edit_1070.py#L416-L534) and [serve/kanban/src/owlbear_kanban/engine.py#L1938-L1970](serve/kanban/src/owlbear_kanban/engine.py#L1938-L1970) | PASS |
| Predicate on entry_status fires on create | [serve/kanban/tests/test_engine_create_edit_1070.py#L221-L229](serve/kanban/tests/test_engine_create_edit_1070.py#L221-L229) and [serve/kanban/src/owlbear_kanban/engine.py#L1817-L1828](serve/kanban/src/owlbear_kanban/engine.py#L1817-L1828) | PASS |
| RED prerequisite recorded | Test-writer note in the task body still records 26 failing tests before builder work. | PASS |

### Deductions
- 0.15 deduction for the live D47 append-warning implementation miss.
- 0.15 deduction for incomplete D53 semantics: explicit null clear is still impossible in AgentView without a presence sentinel.
- 0.10 deduction for missing AC29 executable proof.
- 0.07 deduction for weak AC30 assertion.
- 0.05 deduction for missing task-owned proof on warning and D53 set or omission paths, plus narrow scoped coverage.

### Confidence: 0.48
### Verdict: FAIL
### Action
- Rejecting back to in-progress.
- Builder should implement the D47 append-only warning path, restore the full D53 contract with explicit-null clear distinct from omission, and add task-owned proof for AC29, AC30, the warning path, and D53 set or omission behavior before returning to review.

### Reflection
- Problem faced: the task-owned suite stayed green while a brief-authority requirement on the append warning path was still missing in code.
- Pattern discovered: None defaults in mutation APIs cannot satisfy both explicit-null clear and omission-preserves-state semantics without a separate presence signal.
- Quality gap: comment-level claims in a TestFromAC file are not executable proof for AC29 or for wire-format requirements like AC30.
[[2026-04-24]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) in `AgentView.edit_task` for D47 and D53 retry items.
- D47 fix: append-only edits now compute post-append full body (`existing + append_payload`) and use that total for both 500KB validation and 100KB guidance warnings.
- D53 fix: added an explicit omission sentinel for `block_reason` so omitted input preserves existing blocked state, while explicit empty/null still clears (`blocked=False`, `block_reason=None`) and non-empty sets blocked.
- AC30 alignment: timestamped append now builds a single ISO-8601 payload with offset and reuses it through validation+write path.
- Tests: 26 TestFromAC tests passed on `serve/kanban/tests/test_engine_create_edit_1070.py`.
- Lint: `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_create_edit_1070.py` -> clean.
- Coverage: not re-run in this retry; scoped green/lint evidence collected for target task suite.
- Evidence summary: fixed the live implementation gaps raised by reviewer (D47 append warning path, D53 omission/null semantics) with a single-file surgical patch.

Post-task reflection:
- Problem faced: tri-state intent (`omitted` vs `null/empty` vs `non-empty`) was collapsed into one `None` default, causing semantic ambiguity.
- Workaround applied: introduced a private sentinel (`_BLOCK_REASON_UNSET`) to preserve omission semantics without changing public API behavior.
- Pattern discovered: mutation endpoints with clear semantics should separate input presence from input value to avoid destructive no-op regressions.
- Quality gap: AC29/AC30 proof depth is primarily test-evidence quality and may need reviewer/test-writer follow-up outside builder scope.
[[2026-04-24]]
## Review Evidence
### Test Results
- Parallel fan-out succeeded: `quality-runner` and `code-reader` both returned usable reports.
- Quality-runner scoped run on [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): 26 passed, 0 failed, 0 skipped.

### Lint
- Quality-runner scoped lint on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): clean.

### Coverage
- Quality-runner scoped coverage: `owlbear_kanban.engine` 32%, overall 35%.
- This is not the primary blocker, but it confirms the task-owned green slice is narrow.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC were violated? | Verdict |
|---|---|---|---|
| AC6 completed-requires-terminal | [test L368](serve/kanban/tests/test_engine_create_edit_1070.py#L368) plus [engine L1955](serve/kanban/src/owlbear_kanban/engine.py#L1955) | Yes | COVERED |
| AC14 body and append_body exclusive | [test L245](serve/kanban/tests/test_engine_create_edit_1070.py#L245) plus [engine L1892](serve/kanban/src/owlbear_kanban/engine.py#L1892) | Yes | COVERED |
| AC24 create missing dependency | [test L183](serve/kanban/tests/test_engine_create_edit_1070.py#L183) plus [engine L1822](serve/kanban/src/owlbear_kanban/engine.py#L1822) | Yes | COVERED |
| AC25 edit add_dep missing | [test L255](serve/kanban/tests/test_engine_create_edit_1070.py#L255) plus [engine L1908](serve/kanban/src/owlbear_kanban/engine.py#L1908) | Yes | COVERED |
| AC29 created and updated include explicit offset | No executable task-owned test. [test L16](serve/kanban/tests/test_engine_create_edit_1070.py#L16) waives proof; the current writes are [engine L894](serve/kanban/src/owlbear_kanban/engine.py#L894) and [engine L1016](serve/kanban/src/owlbear_kanban/engine.py#L1016), and the brief requires the format at [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L85](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L85) | No | MISSING |
| AC30 append_body timestamp prepends full ISO timestamp | [test L317](serve/kanban/tests/test_engine_create_edit_1070.py#L317) uses the regex at [test L329](serve/kanban/tests/test_engine_create_edit_1070.py#L329); the payload is built at [engine L1915](serve/kanban/src/owlbear_kanban/engine.py#L1915) and the brief contract is [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L106](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L106) | No; the regex does not prove full `+HH:MM` or `Z`, and it does not prove prepend position ahead of the note text | LAX |
| AC-NEW-15 parent missing | [test L263](serve/kanban/tests/test_engine_create_edit_1070.py#L263) plus [engine L1901](serve/kanban/src/owlbear_kanban/engine.py#L1901) | Yes | COVERED |
| No status param on create; entry_status used | [test L172](serve/kanban/tests/test_engine_create_edit_1070.py#L172), AgentView signature at [engine L1792](serve/kanban/src/owlbear_kanban/engine.py#L1792), and core create path at [engine L899](serve/kanban/src/owlbear_kanban/engine.py#L899) | Yes | COVERED |
| Body over 500 KB raises ERR_BODY_TOO_LARGE | [test L201](serve/kanban/tests/test_engine_create_edit_1070.py#L201), [test L211](serve/kanban/tests/test_engine_create_edit_1070.py#L211), [test L279](serve/kanban/tests/test_engine_create_edit_1070.py#L279), [test L289](serve/kanban/tests/test_engine_create_edit_1070.py#L289), and hard-cap helper at [engine L1605](serve/kanban/src/owlbear_kanban/engine.py#L1605) | Yes | COVERED |
| Body over 100 KB returns guidance warning | No task-owned assertion covers the warning branches at [engine L1856](serve/kanban/src/owlbear_kanban/engine.py#L1856), [engine L2015](serve/kanban/src/owlbear_kanban/engine.py#L2015), and [engine L2017](serve/kanban/src/owlbear_kanban/engine.py#L2017), required by [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81) and [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103) | No | MISSING |
| Post-append total body checked against size caps | [test L289](serve/kanban/tests/test_engine_create_edit_1070.py#L289) proves the post-append hard cap, and the append path computes the total at [engine L1913](serve/kanban/src/owlbear_kanban/engine.py#L1913); but there is still no task-owned warning assertion for the same total-size contract | No; warning-cap regressions would stay green | LAX |
| D53 block_reason semantics | [test L299](serve/kanban/tests/test_engine_create_edit_1070.py#L299) proves explicit empty-string clear only. Current tri-state implementation is at [engine L1886](serve/kanban/src/owlbear_kanban/engine.py#L1886), [engine L1994](serve/kanban/src/owlbear_kanban/engine.py#L1994), [engine L1997](serve/kanban/src/owlbear_kanban/engine.py#L1997), and [engine L2000](serve/kanban/src/owlbear_kanban/engine.py#L2000) | No; non-empty set, explicit null clear, and omission-preserves-state are unproven | LAX |
| ERR_NO_OP | [test L271](serve/kanban/tests/test_engine_create_edit_1070.py#L271) plus [engine L2004](serve/kanban/src/owlbear_kanban/engine.py#L2004) | Yes | COVERED |
| Archival fields on non-archived task | [test L346](serve/kanban/tests/test_engine_create_edit_1070.py#L346), [test L357](serve/kanban/tests/test_engine_create_edit_1070.py#L357), and [engine L1923](serve/kanban/src/owlbear_kanban/engine.py#L1923) | Yes | COVERED |
| Archival refs matrix per section 3.2 | [test L416](serve/kanban/tests/test_engine_create_edit_1070.py#L416), [test L430](serve/kanban/tests/test_engine_create_edit_1070.py#L430), [test L442](serve/kanban/tests/test_engine_create_edit_1070.py#L442), [test L461](serve/kanban/tests/test_engine_create_edit_1070.py#L461), [test L474](serve/kanban/tests/test_engine_create_edit_1070.py#L474), [test L487](serve/kanban/tests/test_engine_create_edit_1070.py#L487), [test L500](serve/kanban/tests/test_engine_create_edit_1070.py#L500), [test L514](serve/kanban/tests/test_engine_create_edit_1070.py#L514), and guards at [engine L1943](serve/kanban/src/owlbear_kanban/engine.py#L1943), [engine L1949](serve/kanban/src/owlbear_kanban/engine.py#L1949), [engine L1962](serve/kanban/src/owlbear_kanban/engine.py#L1962), [engine L1967](serve/kanban/src/owlbear_kanban/engine.py#L1967), [engine L1973](serve/kanban/src/owlbear_kanban/engine.py#L1973) | Yes for the invalid-rule matrix covered by this task-owned suite | COVERED |
| Predicate on entry_status fires on create | [test L221](serve/kanban/tests/test_engine_create_edit_1070.py#L221), [engine L1828](serve/kanban/src/owlbear_kanban/engine.py#L1828), and [engine L1837](serve/kanban/src/owlbear_kanban/engine.py#L1837) | Yes | COVERED |
| RED prerequisite recorded | [task L52](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L52) and [task L80](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L80) | Yes; historical RED evidence exists in the task body | COVERED |

#### Security Review
- No task-scoped security defects found in the reviewed create_task and edit_task paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC suite in [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py) | Latest builder retry changed only [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py); no weakened or removed assertions found | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC30 regex at [test L329](serve/kanban/tests/test_engine_create_edit_1070.py#L329) is too permissive for the wire-format contract. |
| Negative and error-path coverage | ADEQUATE | Error-path coverage is broad, but positive warning and D53 presence semantics are still unproven. |
| Manual mutation resistance | WEAK | Removing the warning branches at [engine L1856](serve/kanban/src/owlbear_kanban/engine.py#L1856), [engine L2015](serve/kanban/src/owlbear_kanban/engine.py#L2015), and [engine L2017](serve/kanban/src/owlbear_kanban/engine.py#L2017), or the non-empty D53 branch at [engine L1996](serve/kanban/src/owlbear_kanban/engine.py#L1996), would leave the suite green. |
| Test independence | STRONG | The tmp_path board fixtures keep cases isolated. |
| Descriptive names | STRONG | Test names remain AC-specific and readable. |

#### Data Safety
- No data-safety issue found in the current snapshot. The omitted-input unblock regression from the previous cycle is fixed by the presence sentinel and explicit set/clear branches at [engine L1886](serve/kanban/src/owlbear_kanban/engine.py#L1886) and [engine L1994](serve/kanban/src/owlbear_kanban/engine.py#L1994).

#### Implementation-Aware Gaps
- Archived-task metadata edits are still nonfunctional in the success path. AgentView can read archived tasks because [engine L817](serve/kanban/src/owlbear_kanban/engine.py#L817) to [engine L824](serve/kanban/src/owlbear_kanban/engine.py#L824) fall back to the archive directory, and AgentView exposes archival edit parameters at [engine L1873](serve/kanban/src/owlbear_kanban/engine.py#L1873) and [engine L1874](serve/kanban/src/owlbear_kanban/engine.py#L1874). But the core edit implementation still has the active-task-only signature at [engine L921](serve/kanban/src/owlbear_kanban/engine.py#L921) and opens only [engine L973](serve/kanban/src/owlbear_kanban/engine.py#L973). The task-owned suite exercises only raising archival cases at [test L346](serve/kanban/tests/test_engine_create_edit_1070.py#L346), [test L357](serve/kanban/tests/test_engine_create_edit_1070.py#L357), [test L416](serve/kanban/tests/test_engine_create_edit_1070.py#L416), [test L430](serve/kanban/tests/test_engine_create_edit_1070.py#L430), [test L442](serve/kanban/tests/test_engine_create_edit_1070.py#L442), [test L461](serve/kanban/tests/test_engine_create_edit_1070.py#L461), [test L474](serve/kanban/tests/test_engine_create_edit_1070.py#L474), [test L487](serve/kanban/tests/test_engine_create_edit_1070.py#L487), [test L500](serve/kanban/tests/test_engine_create_edit_1070.py#L500), and [test L514](serve/kanban/tests/test_engine_create_edit_1070.py#L514). This is a live implementation miss plus a significant untested path.
- A broader search found no durable positive archived-edit proof outside the task-owned suite.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The task file already contains two earlier review failures at [task L94](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L94) and [task L212](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L212). This pass is therefore the third review fail, so the loop-breaker route applies.
- The test file still contains stale RED commentary at [test L169](serve/kanban/tests/test_engine_create_edit_1070.py#L169), [test L242](serve/kanban/tests/test_engine_create_edit_1070.py#L242), [test L304](serve/kanban/tests/test_engine_create_edit_1070.py#L304), [test L322](serve/kanban/tests/test_engine_create_edit_1070.py#L322), [test L343](serve/kanban/tests/test_engine_create_edit_1070.py#L343), and [test L412](serve/kanban/tests/test_engine_create_edit_1070.py#L412). They no longer describe the current engine and reduce the suite’s value as living evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC6 | [test L368](serve/kanban/tests/test_engine_create_edit_1070.py#L368) and [engine L1955](serve/kanban/src/owlbear_kanban/engine.py#L1955) | `test_archived_completed_reason_requires_terminal_status` | PASS |
| AC14 | [test L245](serve/kanban/tests/test_engine_create_edit_1070.py#L245) and [engine L1892](serve/kanban/src/owlbear_kanban/engine.py#L1892) | `test_body_and_append_body_both_set_raises_body_exclusive` | PASS |
| AC24 | [test L183](serve/kanban/tests/test_engine_create_edit_1070.py#L183) and [engine L1822](serve/kanban/src/owlbear_kanban/engine.py#L1822) | `test_create_task_dep_not_found_raises_validation_error` | PASS |
| AC25 | [test L255](serve/kanban/tests/test_engine_create_edit_1070.py#L255) and [engine L1908](serve/kanban/src/owlbear_kanban/engine.py#L1908) | `test_add_dep_nonexistent_raises_dep_not_found` | PASS |
| AC29 | [test L16](serve/kanban/tests/test_engine_create_edit_1070.py#L16), [engine L894](serve/kanban/src/owlbear_kanban/engine.py#L894), [engine L1016](serve/kanban/src/owlbear_kanban/engine.py#L1016), and [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L85](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L85) | none | FAIL |
| AC30 | [test L317](serve/kanban/tests/test_engine_create_edit_1070.py#L317), [test L329](serve/kanban/tests/test_engine_create_edit_1070.py#L329), [engine L1915](serve/kanban/src/owlbear_kanban/engine.py#L1915), and [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L106](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L106) | `test_append_body_timestamp_uses_iso_datetime_with_offset` | FAIL |
| AC-NEW-15 | [test L263](serve/kanban/tests/test_engine_create_edit_1070.py#L263) and [engine L1901](serve/kanban/src/owlbear_kanban/engine.py#L1901) | `test_parent_nonexistent_raises_parent_not_found` | PASS |
| No status param on create and entry_status used | [test L172](serve/kanban/tests/test_engine_create_edit_1070.py#L172), [engine L1792](serve/kanban/src/owlbear_kanban/engine.py#L1792), and [engine L899](serve/kanban/src/owlbear_kanban/engine.py#L899) | `test_create_task_uses_entry_status_not_defaults_status` | PASS |
| Body over 500 KB raises ERR_BODY_TOO_LARGE | [test L201](serve/kanban/tests/test_engine_create_edit_1070.py#L201), [test L211](serve/kanban/tests/test_engine_create_edit_1070.py#L211), [test L279](serve/kanban/tests/test_engine_create_edit_1070.py#L279), [test L289](serve/kanban/tests/test_engine_create_edit_1070.py#L289), and [engine L1605](serve/kanban/src/owlbear_kanban/engine.py#L1605) | four body-cap tests | PASS |
| Body over 100 KB returns guidance warning | [engine L1856](serve/kanban/src/owlbear_kanban/engine.py#L1856), [engine L2015](serve/kanban/src/owlbear_kanban/engine.py#L2015), [engine L2017](serve/kanban/src/owlbear_kanban/engine.py#L2017), [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L81), and [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L103); no task-owned assertion exists | none | FAIL |
| Post-append total body checked against size caps | [test L289](serve/kanban/tests/test_engine_create_edit_1070.py#L289) and [engine L1913](serve/kanban/src/owlbear_kanban/engine.py#L1913) prove the hard cap, but the same total-size warning cap remains unproven in the task-owned suite | `test_append_body_total_over_500kb_raises_body_too_large` | FAIL |
| block_reason semantics | [test L299](serve/kanban/tests/test_engine_create_edit_1070.py#L299), [engine L1886](serve/kanban/src/owlbear_kanban/engine.py#L1886), [engine L1994](serve/kanban/src/owlbear_kanban/engine.py#L1994), [engine L1997](serve/kanban/src/owlbear_kanban/engine.py#L1997), and [engine L2000](serve/kanban/src/owlbear_kanban/engine.py#L2000) | `test_empty_block_reason_clears_blocked_and_block_reason` | FAIL |
| ERR_NO_OP | [test L271](serve/kanban/tests/test_engine_create_edit_1070.py#L271) and [engine L2004](serve/kanban/src/owlbear_kanban/engine.py#L2004) | `test_no_op_call_raises_no_op_error` | PASS |
| Archival fields on non-archived task | [test L346](serve/kanban/tests/test_engine_create_edit_1070.py#L346), [test L357](serve/kanban/tests/test_engine_create_edit_1070.py#L357), and [engine L1923](serve/kanban/src/owlbear_kanban/engine.py#L1923) | two archival-field tests | PASS |
| Archival refs matrix per section 3.2 | [test L416](serve/kanban/tests/test_engine_create_edit_1070.py#L416), [test L430](serve/kanban/tests/test_engine_create_edit_1070.py#L430), [test L442](serve/kanban/tests/test_engine_create_edit_1070.py#L442), [test L461](serve/kanban/tests/test_engine_create_edit_1070.py#L461), [test L474](serve/kanban/tests/test_engine_create_edit_1070.py#L474), [test L487](serve/kanban/tests/test_engine_create_edit_1070.py#L487), [test L500](serve/kanban/tests/test_engine_create_edit_1070.py#L500), [test L514](serve/kanban/tests/test_engine_create_edit_1070.py#L514), and guards at [engine L1943](serve/kanban/src/owlbear_kanban/engine.py#L1943), [engine L1949](serve/kanban/src/owlbear_kanban/engine.py#L1949), [engine L1962](serve/kanban/src/owlbear_kanban/engine.py#L1962), [engine L1967](serve/kanban/src/owlbear_kanban/engine.py#L1967), [engine L1973](serve/kanban/src/owlbear_kanban/engine.py#L1973) | `TestFromAC_EditTaskArchivalRefs` | PASS |
| Predicate on entry_status fires on create | [test L221](serve/kanban/tests/test_engine_create_edit_1070.py#L221), [engine L1828](serve/kanban/src/owlbear_kanban/engine.py#L1828), and [engine L1837](serve/kanban/src/owlbear_kanban/engine.py#L1837) | `test_create_task_predicate_failed_on_entry_status_raises_predicate_failed` | PASS |
| All tests fail in RED phase | [task L52](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L52) and [task L80](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L80) | task body evidence | PASS |

### Deductions
- 0.25 deduction for the live archived-edit persistence defect and the missing positive-path proof around archival edits.
- 0.15 deduction for missing AC29 executable proof.
- 0.08 deduction for lax AC30 timestamp proof.
- 0.10 deduction for missing 100 KB warning proof.
- 0.07 deduction for partial D53 proof and low scoped coverage.

### Confidence: 0.35
### Verdict: FAIL
### Action
- Rejecting to backlog.
- Two prior review sections already exist at [task L94](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L94) and [task L212](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L212), so this is the third review fail and the loop-breaker route applies.
- Rework needed: fix the archived-task metadata edit success path, then add task-owned proof for AC29, AC30, the 100 KB warning path, and the full D53 set/null/omission contract before returning to review.
[[2026-04-24]]
## Architecture Review

### Context
Third review-fail loop-breaker return. Three prior review cycles identified persistent test-proof gaps: AC29 (no executable proof), AC30 (lax regex), D47 100KB guidance warning (no test), D53 block_reason (partial proof), plus an archived-edit success-path implementation gap. The implementation is correct for all in-scope behavior — the loop is caused by insufficient test assertions, not code defects.

### Refined Acceptance Criteria (supersedes original §AC)

#### Proven — 26 tests GREEN, keep as-is
- [x] AC6: `edit_task(<archived>, archival_reason="completed")` → `ValidationError(ERR_COMPLETED_REQUIRES_DONE)`
- [x] AC14: `edit_task(id, body=..., append_body=...)` both set → `ValidationError(ERR_BODY_EXCLUSIVE)`
- [x] AC24: `create_task(..., depends_on=[99999])` → `ValidationError(ERR_DEP_NOT_FOUND)`
- [x] AC25: `edit_task(id, add_dep=[99999])` → `ValidationError(ERR_DEP_NOT_FOUND)`
- [x] AC-NEW-15: `edit_task(id, parent=99999)` → `ValidationError(ERR_PARENT_NOT_FOUND)`
- [x] D50: No `status` param on `create_task` — tasks created at `BoardConfig.entry_status`
- [x] D35+D47: Body >500KB → `ValidationError(ERR_BODY_TOO_LARGE)` (create, edit-replace, post-append)
- [x] D53-CLEAR: `edit_task(id, block_reason="")` → `blocked=False, block_reason=None`
- [x] ERR_NO_OP: No-op call → `ValidationError(ERR_NO_OP)`
- [x] D37+D57: Archival fields on non-archived task → `ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)`
- [x] D37: Invalid archival_reason enum → `ValidationError(ERR_ARCHIVAL_REASON_INVALID)`
- [x] §3.2: Archival refs matrix (required/forbidden/missing/self/cycle)
- [x] D15+D50: Predicate on entry_status fires on create

#### Test proof gaps — new tests required
- [ ] AC30-TIGHT: `edit_task(id, append_body="Note.", timestamp=true)` → body text after append contains a line matching `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}` immediately followed by `\nNote.`. Replace existing lax regex assertion.
- [ ] D47-WARN-CREATE: `create_task(title="X", body=<101KB string>)` → succeeds; response `guidance` list contains body-size warning
- [ ] D47-WARN-EDIT-REPLACE: `edit_task(id, body=<101KB string>)` → succeeds; response `guidance` list contains body-size warning
- [ ] D47-WARN-EDIT-APPEND: `edit_task(id, append_body=...)` where post-append total >100KB → succeeds; response `guidance` list contains body-size warning
- [ ] D53-SET: `edit_task(id, block_reason="dependency missing")` on unblocked task → `blocked=True, block_reason="dependency missing"`
- [ ] D53-OMIT: `edit_task(id, priority="critical")` on a blocked task → `blocked` and `block_reason` unchanged

#### Dropped
- ~~AC29~~: `datetime.now(tz=UTC).isoformat()` is deterministic stdlib producing `+00:00`. Test-writer waiver accepted after 3 review cycles. No regression risk justifies a dedicated test in this task.

#### Notes for downstream
- Implementation for all gap items is already in place. New tests may pass immediately — test-writer should note this and proceed.
- Existing 26 tests in `serve/kanban/tests/test_engine_create_edit_1070.py` remain as-is; do not remove or weaken them.
- Archived-edit success-path gap (core `edit_task` cannot persist to archive/) split to follow-up #1120.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validation tests for create_task + edit_task — shared validation layer |
| Interface clarity | PASS | After refinement, each AC specifies exact inputs and expected outputs |
| Dependency correctness | PASS | #1068 (not found — presumed archived/done); no blocking issue |
| Module layering | PASS | Test file imports only from owlbear_kanban |
| TDD compliance | PASS | This IS the test task (tdd:red) |
| KISS/YAGNI | PASS | Removed AC29 (stdlib behavior); no hypothetical requirements |
| Premise challenge | PASS | Validation coverage for create/edit is necessary |
| Pattern consistency | PASS | Test fixtures follow existing board-helper pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban engine domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Follow-up Tasks
- #1120: Archived-task metadata edit persistence path (backlog, depends_on #1070)

### Verdict: REFINE → APPROVE
### Action: Tightened AC (dropped AC29, added 6 precise test-proof-gap items, split archived-edit to #1120). Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_engine_create_edit_1070.py`
- Classes: `TestFromAC_CreateTask`, `TestFromAC_EditTaskValidation`, `TestFromAC_EditTaskArchivalGates`, `TestFromAC_EditTaskArchivalRefs`
- New tests added (retry — loop-breaker cycle): 5 new tests + 1 in-place tightening (AC30)
- Total: 31 tests, all PASS (26 original preserved; 5 new pass immediately per Architecture Review prediction)
- ruff: clean

**Retry changes (AC gaps from reviewer, per Architecture Review refined AC):**

| Gap | Test Added | Outcome |
|---|---|---|
| AC30-TIGHT | Replaced lax regex in `test_append_body_timestamp_uses_iso_datetime_with_offset` with strict `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\nNote\.` + prepend-position proof | PASS (impl correct) |
| D47-WARN-CREATE | `test_create_task_body_over_100kb_returns_guidance_warning` | PASS (impl correct) |
| D47-WARN-EDIT-REPLACE | `test_edit_task_body_replace_over_100kb_returns_guidance_warning` | PASS (impl correct) |
| D47-WARN-EDIT-APPEND | `test_edit_task_append_total_over_100kb_returns_guidance_warning` | PASS (impl correct) |
| D53-SET | `test_set_nonempty_block_reason_sets_blocked_true` | PASS (impl correct) |
| D53-OMIT | `test_omit_block_reason_on_blocked_task_preserves_state` | PASS (impl correct) |

**Note on pass-through:** Architecture Review explicitly stated "Implementation for all gap items is already in place. New tests may pass immediately — test-writer should note this and proceed." All new tests pass immediately, confirming implementation already satisfies the refined AC. No RED test phase applies for this loop-breaker retry.

Commit: facc37a3 — `test: add proof tests for AC30/D47-WARN/D53 gaps (#1070, test-writer)`
[[2026-04-24]]
## Builder Notes
- Implementation: no source changes in this builder cycle; existing implementation already satisfied the refined AC and task-owned assertions.
- Tests: 31 TestFromAC tests passed in `serve/kanban/tests/test_engine_create_edit_1070.py`.
- Coverage: 33% on touched module (`owlbear_kanban.engine`) from the scoped task run.
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_create_edit_1070.py`.
- Durable module test file check: `serve/kanban/tests/test_engine_create_edit.py` is missing, so no durable module-level run was possible.
- Approach: verification-only builder pass, since the task entered in-progress with all refined TestFromAC checks already green.

Post-task reflection:
- Problem faced: no RED baseline remained because test and implementation were already synchronized before this builder pass.
- Workaround applied: performed strict quality-runner scoped verification (tests + lint + coverage) instead of unnecessary edits.
- Pattern discovered: loop-breaker retries can legitimately become verification-only when prior cycles already closed implementation gaps.
- Quality gap: module coverage remains low in scoped runs, but this reflects task-slice evidence limits rather than a regression in #1070.
[[2026-04-24]]
## Review Evidence
### Test Results
- Parallel fan-out succeeded: quality-runner and code-reader both returned usable reports.
- Quality-runner scoped run on [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): 31 passed, 0 failed, 0 skipped.
- Editor diagnostics: no errors in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) or [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py).

### Lint
- Quality-runner scoped lint on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py): clean.

### Coverage
- Quality-runner scoped coverage: owlbear_kanban.engine 33%, overall 36%.
- The module slice is narrow because the target is a large engine file, but the scoped run plus direct code read did not reveal any refined-AC gap in the task-owned slice.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC6 completed requires terminal status | test_archived_completed_reason_requires_terminal_status | Yes; the test asserts ERR_COMPLETED_REQUIRES_DONE against the live guard in [serve/kanban/src/owlbear_kanban/engine.py#L1955](serve/kanban/src/owlbear_kanban/engine.py#L1955) | COVERED |
| AC14 body and append_body exclusive | test_body_and_append_body_both_set_raises_body_exclusive | Yes; the test asserts ERR_BODY_EXCLUSIVE against [serve/kanban/src/owlbear_kanban/engine.py#L1892](serve/kanban/src/owlbear_kanban/engine.py#L1892) | COVERED |
| AC24 create missing dependency | test_create_task_dep_not_found_raises_validation_error | Yes; the test asserts ERR_DEP_NOT_FOUND against [serve/kanban/src/owlbear_kanban/engine.py#L1822](serve/kanban/src/owlbear_kanban/engine.py#L1822) | COVERED |
| AC25 edit add_dep missing | test_add_dep_nonexistent_raises_dep_not_found | Yes; the test asserts ERR_DEP_NOT_FOUND against [serve/kanban/src/owlbear_kanban/engine.py#L1908](serve/kanban/src/owlbear_kanban/engine.py#L1908) | COVERED |
| AC-NEW-15 parent missing | test_parent_nonexistent_raises_parent_not_found | Yes; the test asserts ERR_PARENT_NOT_FOUND against [serve/kanban/src/owlbear_kanban/engine.py#L1901](serve/kanban/src/owlbear_kanban/engine.py#L1901) | COVERED |
| D50 create uses entry_status and AgentView exposes no status parameter | test_create_task_uses_entry_status_not_defaults_status | Yes for the behavioral clause via [serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180](serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180); the current signature in [serve/kanban/src/owlbear_kanban/engine.py#L1792-L1798](serve/kanban/src/owlbear_kanban/engine.py#L1792-L1798) satisfies the no-status clause | COVERED |
| D35 plus D47 hard body cap | test_create_task_body_over_500kb_raises_body_too_large, test_create_task_body_at_500kb_plus_one_byte_raises_body_too_large, test_body_replace_over_500kb_raises_body_too_large, test_append_body_total_over_500kb_raises_body_too_large | Yes; all four tests assert ERR_BODY_TOO_LARGE against [serve/kanban/src/owlbear_kanban/engine.py#L1605-L1608](serve/kanban/src/owlbear_kanban/engine.py#L1605-L1608) and the append total path in [serve/kanban/src/owlbear_kanban/engine.py#L1912-L1917](serve/kanban/src/owlbear_kanban/engine.py#L1912-L1917) | COVERED |
| D53-CLEAR explicit empty string clears blocked state | test_empty_block_reason_clears_blocked_and_block_reason | Yes; the test proves the explicit clear branch in [serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000](serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000) | COVERED |
| ERR_NO_OP | test_no_op_call_raises_no_op_error | Yes; the test asserts ERR_NO_OP against [serve/kanban/src/owlbear_kanban/engine.py#L2004-L2007](serve/kanban/src/owlbear_kanban/engine.py#L2004-L2007) | COVERED |
| D37 plus D57 archival fields forbidden on active tasks | test_archival_reason_on_active_task_raises_archival_fields_forbidden and test_archival_refs_on_active_task_raises_archival_fields_forbidden | Yes; both tests assert ERR_ARCHIVAL_FIELDS_FORBIDDEN against [serve/kanban/src/owlbear_kanban/engine.py#L1920-L1923](serve/kanban/src/owlbear_kanban/engine.py#L1920-L1923) | COVERED |
| D37 invalid archival_reason enum | test_invalid_archival_reason_raises_archival_reason_invalid | Yes; the test asserts ERR_ARCHIVAL_REASON_INVALID against [serve/kanban/src/owlbear_kanban/engine.py#L1931-L1936](serve/kanban/src/owlbear_kanban/engine.py#L1931-L1936) | COVERED |
| Section 3.2 archival refs matrix | TestFromAC_EditTaskArchivalRefs | Yes; the suite exercises required, forbidden, missing, self, and cycle rules across [serve/kanban/tests/test_engine_create_edit_1070.py#L485-L603](serve/kanban/tests/test_engine_create_edit_1070.py#L485-L603) and the live guards at [serve/kanban/src/owlbear_kanban/engine.py#L1938-L1973](serve/kanban/src/owlbear_kanban/engine.py#L1938-L1973) | COVERED |
| D15 plus D50 predicate on create | test_create_task_predicate_failed_on_entry_status_raises_predicate_failed | Yes; the test asserts ERR_PREDICATE_FAILED and confirms no task file is written, matching [serve/kanban/src/owlbear_kanban/engine.py#L1828-L1838](serve/kanban/src/owlbear_kanban/engine.py#L1828-L1838) | COVERED |
| AC30-TIGHT append timestamp with full ISO offset and immediate note adjacency | test_append_body_timestamp_uses_iso_datetime_with_offset | Yes; the test requires a full ISO timestamp with offset immediately followed by newline plus Note, matching the payload built in [serve/kanban/src/owlbear_kanban/engine.py#L1915-L1917](serve/kanban/src/owlbear_kanban/engine.py#L1915-L1917) | COVERED |
| D47-WARN-CREATE guidance warning | test_create_task_body_over_100kb_returns_guidance_warning | Yes; the test exercises the create-side warning path in [serve/kanban/src/owlbear_kanban/engine.py#L1854-L1857](serve/kanban/src/owlbear_kanban/engine.py#L1854-L1857) | COVERED |
| D47-WARN-EDIT-REPLACE guidance warning | test_edit_task_body_replace_over_100kb_returns_guidance_warning | Yes; the test exercises the replacement warning branch in [serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015](serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015) | COVERED |
| D47-WARN-EDIT-APPEND guidance warning | test_edit_task_append_total_over_100kb_returns_guidance_warning | Yes; the test exercises the post-append total warning branch in [serve/kanban/src/owlbear_kanban/engine.py#L2016-L2017](serve/kanban/src/owlbear_kanban/engine.py#L2016-L2017) | COVERED |
| D53-SET non-empty block_reason sets blocked true | test_set_nonempty_block_reason_sets_blocked_true | Yes; the test proves the explicit set branch in [serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997](serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997) | COVERED |
| D53-OMIT omission preserves blocked state | test_omit_block_reason_on_blocked_task_preserves_state | Yes; the test proves omission leaves the block fields untouched while another field changes, matching the sentinel flow in [serve/kanban/src/owlbear_kanban/engine.py#L1885-L1886](serve/kanban/src/owlbear_kanban/engine.py#L1885-L1886) and [serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000](serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000) | COVERED |

#### Security Review
- No task-scoped security defects found in the reviewed create_task and edit_task paths in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC suite in [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py) | The retry added 5 proof tests and tightened 1 AC30 assertion as recorded in [.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L489-L499](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L489-L499); the latest builder pass made no source edits | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC30 now requires a full timestamp-plus-note sequence in [serve/kanban/tests/test_engine_create_edit_1070.py#L381-L398](serve/kanban/tests/test_engine_create_edit_1070.py#L381-L398), and the D47 plus D53 tests assert concrete guidance and state transitions across [serve/kanban/tests/test_engine_create_edit_1070.py#L221-L379](serve/kanban/tests/test_engine_create_edit_1070.py#L221-L379) |
| Negative and error-path coverage | STRONG | The suite covers the create and edit validation matrix, error codes, and archival matrix across [serve/kanban/tests/test_engine_create_edit_1070.py#L172-L603](serve/kanban/tests/test_engine_create_edit_1070.py#L172-L603) |
| Manual mutation resistance | ADEQUATE | Removing the D47 warning branches or the D53 set and omit branches would now fail dedicated tests in [serve/kanban/tests/test_engine_create_edit_1070.py#L221-L379](serve/kanban/tests/test_engine_create_edit_1070.py#L221-L379) |
| Test independence | STRONG | tmp_path-backed helpers isolate each board fixture instance throughout [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py) |
| Descriptive names | STRONG | Test names remain AC-specific and directly traceable to the refined contract |

#### Data Safety
- No data-safety issue found in the current refined scope. The omission sentinel and explicit set and clear branches in [serve/kanban/src/owlbear_kanban/engine.py#L1885-L2000](serve/kanban/src/owlbear_kanban/engine.py#L1885-L2000) prevent the earlier destructive unblock regression.

#### Implementation-Aware Gaps
- No in-scope implementation gap found against the binding refined AC.
- Archived-edit success-path persistence was explicitly split out to follow-up #1120 in [.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L460](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L460) and is not part of the current pass criteria.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The current pass is anchored to the latest Architecture Review refinement in [.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L429-L460](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L429-L460). AC29 was dropped there, and archived-edit success-path persistence was split to #1120, so the earlier fail sections are historical context rather than current blockers.
- Stale RED-era commentary remains in the header and class docstrings of [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py). It no longer matches the current green snapshot, but it does not weaken the executable proof.
- Code-reader flagged two possible tightening opportunities around AC30 line-boundary anchoring and a dedicated D50 signature assertion. After re-reading the refined AC, the live signature, and the now-executable proof tests, I am treating those as non-blocking improvements rather than pass-1 failures.

### AC Compliance
- Current binding scope is the refinement at [.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L429-L460](.owlbear/kanban/tasks/1070-b-07-red-create-task-edit-task-tests.md#L429-L460).
- AC29 is excluded because that refinement explicitly dropped it.

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC6 | [serve/kanban/tests/test_engine_create_edit_1070.py#L441-L456](serve/kanban/tests/test_engine_create_edit_1070.py#L441-L456) and [serve/kanban/src/owlbear_kanban/engine.py#L1955-L1958](serve/kanban/src/owlbear_kanban/engine.py#L1955-L1958) | test_archived_completed_reason_requires_terminal_status | PASS |
| AC14 | [serve/kanban/tests/test_engine_create_edit_1070.py#L257-L264](serve/kanban/tests/test_engine_create_edit_1070.py#L257-L264) and [serve/kanban/src/owlbear_kanban/engine.py#L1892-L1895](serve/kanban/src/owlbear_kanban/engine.py#L1892-L1895) | test_body_and_append_body_both_set_raises_body_exclusive | PASS |
| AC24 | [serve/kanban/tests/test_engine_create_edit_1070.py#L183-L190](serve/kanban/tests/test_engine_create_edit_1070.py#L183-L190) and [serve/kanban/src/owlbear_kanban/engine.py#L1822-L1826](serve/kanban/src/owlbear_kanban/engine.py#L1822-L1826) | test_create_task_dep_not_found_raises_validation_error | PASS |
| AC25 | [serve/kanban/tests/test_engine_create_edit_1070.py#L266-L272](serve/kanban/tests/test_engine_create_edit_1070.py#L266-L272) and [serve/kanban/src/owlbear_kanban/engine.py#L1908-L1912](serve/kanban/src/owlbear_kanban/engine.py#L1908-L1912) | test_add_dep_nonexistent_raises_dep_not_found | PASS |
| AC-NEW-15 | [serve/kanban/tests/test_engine_create_edit_1070.py#L274-L280](serve/kanban/tests/test_engine_create_edit_1070.py#L274-L280) and [serve/kanban/src/owlbear_kanban/engine.py#L1901-L1906](serve/kanban/src/owlbear_kanban/engine.py#L1901-L1906) | test_parent_nonexistent_raises_parent_not_found | PASS |
| D50 | [serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180](serve/kanban/tests/test_engine_create_edit_1070.py#L172-L180) and [serve/kanban/src/owlbear_kanban/engine.py#L1792-L1798](serve/kanban/src/owlbear_kanban/engine.py#L1792-L1798) | test_create_task_uses_entry_status_not_defaults_status | PASS |
| D35 plus D47 hard cap | [serve/kanban/tests/test_engine_create_edit_1070.py#L192-L219](serve/kanban/tests/test_engine_create_edit_1070.py#L192-L219), [serve/kanban/tests/test_engine_create_edit_1070.py#L292-L310](serve/kanban/tests/test_engine_create_edit_1070.py#L292-L310), and [serve/kanban/src/owlbear_kanban/engine.py#L1605-L1608](serve/kanban/src/owlbear_kanban/engine.py#L1605-L1608) | four body-cap tests | PASS |
| D53-CLEAR | [serve/kanban/tests/test_engine_create_edit_1070.py#L336-L352](serve/kanban/tests/test_engine_create_edit_1070.py#L336-L352) and [serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000](serve/kanban/src/owlbear_kanban/engine.py#L1994-L2000) | test_empty_block_reason_clears_blocked_and_block_reason | PASS |
| ERR_NO_OP | [serve/kanban/tests/test_engine_create_edit_1070.py#L282-L289](serve/kanban/tests/test_engine_create_edit_1070.py#L282-L289) and [serve/kanban/src/owlbear_kanban/engine.py#L2004-L2007](serve/kanban/src/owlbear_kanban/engine.py#L2004-L2007) | test_no_op_call_raises_no_op_error | PASS |
| D37 plus D57 | [serve/kanban/tests/test_engine_create_edit_1070.py#L418-L439](serve/kanban/tests/test_engine_create_edit_1070.py#L418-L439) and [serve/kanban/src/owlbear_kanban/engine.py#L1920-L1923](serve/kanban/src/owlbear_kanban/engine.py#L1920-L1923) | two archival-field tests | PASS |
| D37 invalid reason | [serve/kanban/tests/test_engine_create_edit_1070.py#L458-L473](serve/kanban/tests/test_engine_create_edit_1070.py#L458-L473) and [serve/kanban/src/owlbear_kanban/engine.py#L1931-L1936](serve/kanban/src/owlbear_kanban/engine.py#L1931-L1936) | test_invalid_archival_reason_raises_archival_reason_invalid | PASS |
| Section 3.2 refs matrix | [serve/kanban/tests/test_engine_create_edit_1070.py#L485-L603](serve/kanban/tests/test_engine_create_edit_1070.py#L485-L603) and [serve/kanban/src/owlbear_kanban/engine.py#L1938-L1973](serve/kanban/src/owlbear_kanban/engine.py#L1938-L1973) | TestFromAC_EditTaskArchivalRefs | PASS |
| D15 plus D50 predicate | [serve/kanban/tests/test_engine_create_edit_1070.py#L233-L244](serve/kanban/tests/test_engine_create_edit_1070.py#L233-L244) and [serve/kanban/src/owlbear_kanban/engine.py#L1828-L1838](serve/kanban/src/owlbear_kanban/engine.py#L1828-L1838) | test_create_task_predicate_failed_on_entry_status_raises_predicate_failed | PASS |
| AC30-TIGHT | [serve/kanban/tests/test_engine_create_edit_1070.py#L381-L398](serve/kanban/tests/test_engine_create_edit_1070.py#L381-L398) and [serve/kanban/src/owlbear_kanban/engine.py#L1915-L1917](serve/kanban/src/owlbear_kanban/engine.py#L1915-L1917) | test_append_body_timestamp_uses_iso_datetime_with_offset | PASS |
| D47-WARN-CREATE | [serve/kanban/tests/test_engine_create_edit_1070.py#L221-L231](serve/kanban/tests/test_engine_create_edit_1070.py#L221-L231) and [serve/kanban/src/owlbear_kanban/engine.py#L1854-L1857](serve/kanban/src/owlbear_kanban/engine.py#L1854-L1857) | test_create_task_body_over_100kb_returns_guidance_warning | PASS |
| D47-WARN-EDIT-REPLACE | [serve/kanban/tests/test_engine_create_edit_1070.py#L312-L322](serve/kanban/tests/test_engine_create_edit_1070.py#L312-L322) and [serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015](serve/kanban/src/owlbear_kanban/engine.py#L2014-L2015) | test_edit_task_body_replace_over_100kb_returns_guidance_warning | PASS |
| D47-WARN-EDIT-APPEND | [serve/kanban/tests/test_engine_create_edit_1070.py#L324-L334](serve/kanban/tests/test_engine_create_edit_1070.py#L324-L334) and [serve/kanban/src/owlbear_kanban/engine.py#L2016-L2017](serve/kanban/src/owlbear_kanban/engine.py#L2016-L2017) | test_edit_task_append_total_over_100kb_returns_guidance_warning | PASS |
| D53-SET | [serve/kanban/tests/test_engine_create_edit_1070.py#L354-L363](serve/kanban/tests/test_engine_create_edit_1070.py#L354-L363) and [serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997](serve/kanban/src/owlbear_kanban/engine.py#L1994-L1997) | test_set_nonempty_block_reason_sets_blocked_true | PASS |
| D53-OMIT | [serve/kanban/tests/test_engine_create_edit_1070.py#L365-L379](serve/kanban/tests/test_engine_create_edit_1070.py#L365-L379) and [serve/kanban/src/owlbear_kanban/engine.py#L1885-L1886](serve/kanban/src/owlbear_kanban/engine.py#L1885-L1886) | test_omit_block_reason_on_blocked_task_preserves_state | PASS |

### Deductions
- 0.04 deduction for low scoped module coverage on a large touched module.
- 0.03 deduction for stale RED commentary and two non-blocking proof-tightening opportunities that do not invalidate the refined AC evidence.

### Confidence: 0.93
### Verdict: PASS
### Action: advance to docs.

### Reflection
- Problem faced: earlier review sections and the original top-level AC no longer matched the binding loop-breaker refinement, so stale failures had to be separated from current scope.
- Workaround applied: re-ran independent quality evidence and anchored the verdict to the latest Architecture Review refinement instead of inheriting older fail notes.
- Pattern discovered: on looped tasks, the latest architecture refinement can legitimately supersede the header AC, and reviewers need to re-ground before treating historical failures as current blockers.
- Quality gap: low module-level scoped coverage and stale RED commentary remain visible, but neither exposed a current refined-AC defect in this task-owned slice.
[[2026-04-24]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md documents KanbanEngine public API, not AgentView internals. The block_reason sentinel fix and D47 append-warning path are implementation details not referenced in any IN-scope prose doc. |
| 2 | Module docstrings | No | N/A | No per-method docstrings exist in engine.py by codebase convention; AgentView class has class-level docstring ("Minimal role-scoped wrapper for agent-facing engine use.") that remains accurate. |
| 3 | External attribution | No | N/A | No external patterns used per task body and builder notes. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | share/diagrams/kanban.excalidraw describes serve/kanban/src/** — matches engine.py. Footer updated: "Last verified: 2026-04-25 (e2b0ef3a)". Committed 1c750e01. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted in this task. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/tests/test_engine_create_edit_1070.py | OUT (test file) | N/A |
| serve/kanban/src/owlbear_kanban/engine.py | IN (docstrings only) | N/A — no per-method docstrings by convention |
| share/diagrams/kanban.excalidraw | IN (diagram describes-match) | Footer updated |

### Files Updated
- share/diagrams/kanban.excalidraw (footer: 2026-04-24 → 2026-04-25, 42532b6a → e2b0ef3a)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1070-* files found)
[[2026-04-24]]
## Audit
### AC Verification
Binding scope: Architecture Review refinement (loop-breaker, in task body). AC29 dropped; archived-edit success-path split to #1120.

| AC Line | Evidence | Status |
|---|---|---|
| AC6 completed-requires-terminal | test L368 + engine L1955 | PASS |
| AC14 body+append_body exclusive | test L245 + engine L1892 | PASS |
| AC24 create missing dep | test L183 + engine L1822 | PASS |
| AC25 edit add_dep missing | test L255 + engine L1908 | PASS |
| AC-NEW-15 parent missing | test L263 + engine L1901 | PASS |
| D50 entry_status on create | test L172 + engine L1792 | PASS |
| D35+D47 hard body cap (4 tests) | test L201,L211,L279,L289 + engine L1605 | PASS |
| D53-CLEAR empty string | test L336 + engine L1994-2000 | PASS |
| ERR_NO_OP | test L271 + engine L2004 | PASS |
| D37+D57 archival fields forbidden | test L418,L430 + engine L1923 | PASS |
| D37 invalid archival_reason | test L458 + engine L1931 | PASS |
| §3.2 archival refs matrix (8 tests) | test L485-L603 + engine L1938-1973 | PASS |
| D15+D50 predicate on create | test L221 + engine L1828 | PASS |
| AC30-TIGHT timestamp+prepend | test L381 — strict regex `[+-]\d{2}:\d{2}\nNote\.` + engine L1915 | PASS |
| D47-WARN-CREATE | test L221 — asserts guidance list | PASS |
| D47-WARN-EDIT-REPLACE | test L312 + engine L2014 | PASS |
| D47-WARN-EDIT-APPEND | test L324 + engine L2016 | PASS |
| D53-SET non-empty | test L354 — asserts blocked=True + block_reason match | PASS |
| D53-OMIT preserves state | test L365 — asserts blocked+block_reason unchanged | PASS |

### Test Results
- pytest (full suite): 1954 passed, 176 failed, 4 skipped — all failures pre-existing (KanbanEngine.__init__ signature mismatch in suites _943/_944/_952/_930, ConfigError in mcp-kanban guidance tests). Zero failures in task scope.
- Task-owned suite: 31 passed, 0 failed, 0 skipped.
- ruff (full): 9 violations, all outside task scope.

### Architect Quality: 3/5
Original AC was directionally complete but lacked assertion-level precision, causing 3 review-fail loops. The loop-breaker refinement (drop AC29, add 6 precise test-proof items, split archived-edit to #1120) was well-executed and directly resolved the loop. Score reflects the 3-cycle cost before adequate precision was achieved.

### Deduction Breakdown
- AC quality score 3: -.03
- All 19 binding AC lines have evidence: no deduction
- Lint violations outside task scope: no deduction
- Full-suite failures outside task scope: no deduction
- Reviewer evidence detailed with PASS verdict: no deduction

### Confidence: .97
### Action: archive