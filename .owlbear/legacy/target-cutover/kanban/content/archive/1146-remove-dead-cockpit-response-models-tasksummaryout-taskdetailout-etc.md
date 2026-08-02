---
id: 1146
title: Remove dead cockpit response models (TaskSummaryOut, TaskDetailOut, etc.)
status: archived
priority: medium
created: 2026-04-27T18:30:12.019145+00:00
updated: 2026-04-27T23:53:33.440163+00:00
tags:
- scope:cockpit
parent:
depends_on:
- 1144
blocked: false
block_reason: 'reviewer crashed twice: no response returned'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
After #1082 rewrote cockpit routes to use engine models directly, five Pydantic models in owlbear_cockpit/models.py are dead code: TaskSummaryOut, TaskDetailOut, TaskListOut, SessionListOut, SessionOut. Only BoardOut is still used (GET /board endpoint in routes/read.py).

## Acceptance Criteria
- [ ] Remove unused models from serve/cockpit/src/owlbear_cockpit/models.py (keep BoardOut + its imports only; remove Field, model_validator if no longer needed)
- [ ] Remove dead test imports and test classes that validate removed models (see impact matrix below; re-verify matrix at build time since #1144 may have already removed some listed tests)
- [ ] Update stale comments and docstrings referencing removed model names in the files listed in the comment-only references table below
- [ ] All tests pass after removal; no new test failures

## Impact Matrix

### Production code
Only `models.py` changes. Routes already use engine models (`ListTasksResponse`, `ShowTaskResponse`, `SingleTaskResponse`, `SessionRecord` from `owlbear_kanban.models`). No route handler changes needed.

### Test files requiring cleanup

| File | Dead imports | Tests to remove |
|------|-------------|-----------------|
| tests/test_cockpit_read_api_930.py | TaskSummaryOut, TaskDetailOut, SessionOut | 4 importability tests + 3 BaseModel subclass tests (entire classes may collapse) |
| tests/test_cockpit_read_api.py | TaskDetailOut (2 imports) | `test_task_detail_out_model_has_claimed_field`, `test_task_detail_out_model_null_claimed_by_yields_claimed_false` |
| tests/test_occ_frontend_wire_1137.py | TaskSummaryOut (2 imports) | Entire `TestFromAC_TaskSummaryOutUpdatedField` class (2 tests) |

### Comment-only references (no import, cosmetic cleanup)

| File | Reference |
|------|-----------|
| tests/test_cockpit_mutation_race_1131.py | `_TASK_DETAIL_KEYS` comment + docstrings mentioning \"TaskDetailOut\" |
| tests/test_cockpit_mutation_api_1132.py | Comment references TaskDetailOut schema |
| tests/test_cockpit_mutation_api.py | Comment references TaskDetailOut shape |
| tests/test_cockpit_kanban_routes_1082.py | Comments reference TaskListOut, SessionListOut, SessionOut |

## Builder Guidance
- **Dependency: #1144 lands first.** This task depends on #1144 which modifies test_cockpit_read_api.py (claimed_by tests) and test_cockpit_kanban_routes_1082.py. Re-verify the impact matrix against the post-#1144 codebase before making changes.
- #1144 AC3 may already delete some TaskDetailOut tests listed above. Remove only what still exists.
- After removing models, check whether `Field` and `model_validator` imports in models.py are still needed by `BoardOut`. If not, remove them.

## Files
- serve/cockpit/src/owlbear_cockpit/models.py
- tests/test_cockpit_read_api_930.py
- tests/test_cockpit_read_api.py
- tests/test_occ_frontend_wire_1137.py
- tests/test_cockpit_mutation_race_1131.py (comments only)
- tests/test_cockpit_mutation_api_1132.py (comments only)
- tests/test_cockpit_mutation_api.py (comments only)
- tests/test_cockpit_kanban_routes_1082.py (comments only)

## Research
- Sources: codebase-only (grep + file reads across all consumers)
- Recommendation: Proceed with removal — all 5 models confirmed dead (confidence: .95)
- Follow-up tasks: none (task is self-contained and correctly scoped)
- Decision requests: none (T1 — dead code removal, no arch/capability change)
- AC expanded: original AC only listed test_cockpit_read_api.py; added test_cockpit_read_api_930.py and test_occ_frontend_wire_1137.py plus impact matrix with exact tests to remove

## Research Gate (trivial)
Items 1–4: N/A — trivial dead code removal. #1082 migrated all routes to engine models; 5 Pydantic response models have zero production consumers. Only BoardOut remains active (GET /board).

## Challenge Results
- Challenger: SKIPPED — trivial dead code removal, no recommendation to challenge
- Risk: negligible — all imports are test-only, production code already uses engine models exclusively
[[2026-04-27]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Removes dead models + their test/comment references. Single concern. |
| Interface clarity | PASS | AC specifies exact models to remove, exact files, exact test names. Impact matrix is thorough. |
| Dependency correctness | PASS | Added depends_on: [1144]. #1144 modifies overlapping test files (test_cockpit_read_api.py claimed_by tests). |
| Module layering | PASS | models.py is leaf module. Removal has no downstream import consumers. |
| TDD compliance | PASS | Subtractive task — tests are being removed alongside the code they test. AC4 requires green suite. |
| KISS/YAGNI | PASS | Pure dead code removal. No additions. |
| Premise challenge | PASS | Verified: grep confirms zero production imports of all 5 models. Only BoardOut is used in routes/read.py. |
| Pattern consistency | PASS | Follows standard dead code cleanup. |
| Security surface | PASS | No new boundaries. Purely subtractive. |
| Single domain | PASS | All changes in cockpit domain. |

### Challenge Results
- Challenger: reconsider (0.69)
- Concerns: (1) sequencing overlap with #1144, (2) impact matrix incomplete for comment references, (3) AC4 evidence quality
- Architect response: (1) accepted — added depends_on: [1144] and builder guidance to re-verify matrix post-#1144; (2) partially accepted — comment-only references were already listed but tightened AC3 to explicitly scope to those files; (3) rejected — AC4 is a post-implementation gate, not a pre-implementation claim.

### Refinements Applied
1. Added depends_on: [1144] — prevents merge conflicts on shared test files
2. Tightened AC1: explicitly notes Field/model_validator import cleanup
3. Tightened AC2: re-verify matrix at build time (post-#1144 drift)
4. Tightened AC3: scoped to listed comment-only reference files (not open-ended)
5. Added Builder Guidance section with #1144 sequencing notes
6. Expanded Files section to include comment-only reference files

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC, added dependency on #1144, added builder guidance. Advanced to todo.

[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_models_1146.py
- Classes: TestFromAC_DeadModelsRemoved, TestFromAC_ModelsImportsClean, TestFromAC_TestImports930Clean, TestFromAC_TestReadApiClean, TestFromAC_Test1137Clean, TestFromAC_CommentRefs1131Clean, TestFromAC_CommentRefs1132Clean, TestFromAC_CommentRefsMutationApiClean, TestFromAC_CommentRefs1082Clean
- Tests per category: happy 7 (ImportError + BoardOut-only structural), edge 2 (import cleanup), boundary 0, structural/source-scan 15
- Total: 24 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 (remove 5 dead models) | test_task_summary_out_raises_import_error, test_task_detail_out_raises_import_error, test_task_list_out_raises_import_error, test_session_out_raises_import_error, test_session_list_out_raises_import_error, test_models_module_has_exactly_one_pydantic_model_class, test_board_out_is_the_remaining_pydantic_model |
| AC1 (Field/model_validator removal) | test_models_py_does_not_import_field, test_models_py_does_not_import_model_validator |
| AC2 (930 dead imports) | test_930_does_not_import_task_summary_out, test_930_does_not_import_task_detail_out, test_930_does_not_import_session_out |
| AC2 (read_api dead methods) | test_read_api_no_dead_method_has_claimed_field, test_read_api_no_dead_method_null_claimed_by |
| AC2 (1137 dead class) | test_1137_no_task_summary_out_updated_field_class, test_1137_does_not_import_task_summary_out |
| AC3 (1131 comments) | test_1131_module_docstring_no_task_detail_out, test_1131_task_detail_keys_comment_no_task_detail_out |
| AC3 (1132 comments) | test_1132_no_task_detail_out_docstring |
| AC3 (mutation_api comments) | test_mutation_api_no_task_detail_out_shape_comment |
| AC3 (1082 comments) | test_kanban_routes_no_task_list_out_in_comments, test_kanban_routes_no_task_detail_out_in_comments, test_kanban_routes_no_session_list_out_in_comments, test_kanban_routes_no_session_out_in_comments |
| AC4 (all tests pass) | verified by builder after cleanup |
[[2026-04-27]]
## Builder Notes
- Implementation: removed dead cockpit response models and imports in serve/cockpit/src/owlbear_cockpit/models.py; retained only BoardOut.
- Test cleanup: removed dead imports/assertions from tests/test_cockpit_read_api_930.py; removed obsolete methods from tests/test_cockpit_read_api.py; removed obsolete class from tests/test_occ_frontend_wire_1137.py.
- Comment/doc cleanup: replaced stale removed-model name references in tests/test_cockpit_mutation_race_1131.py, tests/test_cockpit_mutation_api_1132.py, tests/test_cockpit_mutation_api.py, tests/test_cockpit_kanban_routes_1082.py.
- Tests: 24 TestFromAC tests passed in tests/test_cockpit_models_1146.py.
- Coverage: 100% on owlbear_cockpit.models (6 statements, 0 missed).
- ruff: clean on all changed files.
- Durable module-level file check: no standalone tests/test_cockpit_models.py exists, so durable module-level run is not applicable.
- Commit: refactor: remove dead cockpit response models (#1146, builder) [f498330a].

## Post-task Reflection
- Main risk was collateral breakage from stale symbol references in unrelated test docs/comments; focused source scans kept edits scoped.
- AC matrix remained accurate post-#1144; only listed targets needed code changes.
- Fastest reliable path was subtractive edits first (models/imports), then exact-string cleanup to satisfy structural tests.
- No additional edge-case test gaps blocked implementation; existing TestFromAC coverage was sufficient to complete GREEN.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner (task suite): pytest 24 passed, 0 failed on tests/test_cockpit_models_1146.py
- quality-runner (changed/impacted suites): pytest 208 passed, 2 failed across the touched file set
- failing tests:
  - tests/test_cockpit_mutation_race_1131.py::TestFromAC_SchemaBaseline::test_move_200_response_has_all_14_taskdetailout_keys -> Missing task-detail keys in move response: {'claimed_by'}
  - tests/test_cockpit_mutation_race_1131.py::TestFromAC_SchemaBaseline::test_edit_200_response_has_all_14_taskdetailout_keys -> Missing task-detail keys in edit response: {'claimed_by'}

### Lint
- ruff: clean on serve/cockpit/src/owlbear_cockpit/models.py and all touched test files

### Coverage
- owlbear_cockpit.models: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 Remove unused cockpit response models; keep BoardOut only | tests/test_cockpit_models_1146.py::TestFromAC_DeadModelsRemoved and ::TestFromAC_ModelsImportsClean; live file serve/cockpit/src/owlbear_cockpit/models.py:5-12 | Yes | COVERED |
| AC2 Remove dead test imports/classes in listed files | tests/test_cockpit_models_1146.py::TestFromAC_TestImports930Clean, ::TestFromAC_TestReadApiClean, ::TestFromAC_Test1137Clean | Partially. Direct removals are checked, but proof is mostly substring-based and does not guard broader stale-contract fallout in touched legacy suites. | LAX |
| AC3 Update stale comments/docstrings in listed comment-only files | tests/test_cockpit_models_1146.py::TestFromAC_CommentRefs1131Clean, ::TestFromAC_CommentRefs1132Clean, ::TestFromAC_CommentRefsMutationApiClean, ::TestFromAC_CommentRefs1082Clean | Yes for the explicit comment/doc targets. | COVERED |
| AC4 All tests pass after removal; no new test failures | No task-owned AC4 proof. Broader changed/impacted-suite run failed in tests/test_cockpit_mutation_race_1131.py. | No | MISSING |

#### Security Review
- No issues found. The runtime change is purely subtractive in serve/cockpit/src/owlbear_cockpit/models.py:5-12 and adds no new boundary, secret, deserialization, path, or injection surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Legacy removals in tests/test_cockpit_read_api.py and tests/test_occ_frontend_wire_1137.py | Dead imports/methods/class removed per AC2 | PRESERVED (task-authorized cleanup) |
| Task-owned TestFromAC suite in tests/test_cockpit_models_1146.py | No evidence of builder weakening/removal | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC1 checks are strong: ImportError assertions plus exact one-model check in tests/test_cockpit_models_1146.py. |
| Negative/error-path coverage | ADEQUATE | Removed-model imports explicitly assert ImportError in tests/test_cockpit_models_1146.py. |
| Manual mutation reasoning | WEAK | The broader impacted-suite run exposed stale 14-key TaskDetailOut assumptions in tests/test_cockpit_mutation_race_1131.py:132-135 and :283-306, but the task-owned suite never exercised that path. |
| Test independence | STRONG | Task-owned checks are isolated source scans/import checks. |
| Descriptive names | STRONG | Task-owned class/method names are clear and AC-mapped. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- The production cleanup itself is correct: serve/cockpit/src/owlbear_cockpit/models.py now contains only BoardOut at :5-12.
- The failing durable suite in tests/test_cockpit_mutation_race_1131.py still encodes the old TaskDetailOut-style 14-key shape via _TASK_DETAIL_KEYS at :132-135 and schema-baseline tests at :283-306.
- That legacy expectation is stale against the shared contract: serve/kanban/src/owlbear_kanban/models.py:322-327 explicitly drops claimed_by from Brief-B projections, and cockpit mutation routes declare response_model=SingleTaskResponse at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:99, :238, and :276.
- Because task 1146 scoped tests/test_cockpit_mutation_race_1131.py as comment/doc cleanup only, reconciling those stale schema-baseline assertions exceeds the latest refined task proof/authority.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Non-blocking stale removed-model references still appear in changed files outside the explicit comment-only table: tests/test_occ_frontend_wire_1137.py:8 and tests/test_cockpit_read_api.py:498, :506-507, :587, :595.
- Those are not the gate failure; the gate failure is the red impacted-suite run plus missing AC4 proof.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | serve/cockpit/src/owlbear_cockpit/models.py:5-12 only imports BaseModel and defines BoardOut; task suite passed 24/24 with 100% coverage | tests/test_cockpit_models_1146.py::TestFromAC_DeadModelsRemoved; ::TestFromAC_ModelsImportsClean | PASS |
| AC2 | Direct removals landed: no dead imports remain in tests/test_cockpit_read_api_930.py; dead methods/class are gone from tests/test_cockpit_read_api.py and tests/test_occ_frontend_wire_1137.py; proof is narrower than the full impacted surface | tests/test_cockpit_models_1146.py::TestFromAC_TestImports930Clean; ::TestFromAC_TestReadApiClean; ::TestFromAC_Test1137Clean | PASS |
| AC3 | Explicit comment-only targets are clean; grep found no remaining removed-model names in tests/test_cockpit_mutation_api_1132.py, tests/test_cockpit_mutation_api.py, or tests/test_cockpit_kanban_routes_1082.py | tests/test_cockpit_models_1146.py::TestFromAC_CommentRefs1131Clean; ::TestFromAC_CommentRefs1132Clean; ::TestFromAC_CommentRefsMutationApiClean; ::TestFromAC_CommentRefs1082Clean | PASS |
| AC4 | Broader changed/impacted-suite run failed 2 tests in tests/test_cockpit_mutation_race_1131.py because move/edit 200 responses no longer include claimed_by | quality-runner impacted-suite run | FAIL |

### Deductions
- -0.12 AC4 not satisfied: changed/impacted-suite run is red.
- -0.08 Task-owned proof gap: no AC4 guard, and stale legacy contract in tests/test_cockpit_mutation_race_1131.py escaped the RED suite.
- -0.03 Cleanup signal drift: touched files outside the explicit comment-only table still contain removed-model names in comments/docstrings.

### Verdict
- FAIL | confidence 0.77

### Action
- Reject to backlog.
- Reason: this is not a source-code regression in serve/cockpit/src/owlbear_cockpit/models.py; it is a test/AC-quality mismatch. The touched durable suite tests/test_cockpit_mutation_race_1131.py still encodes the obsolete TaskDetailOut wire contract, while the canonical shared model explicitly drops claimed_by. The next cycle needs an architect/test-writer reconciliation of that stale durable-suite expectation and explicit AC4 proof before builder retry.
[[2026-04-27]]

## Architecture Review (Cycle 2)

### Reviewer Feedback Summary
Cycle 1 FAIL (0.77): 2 tests in test_cockpit_mutation_race_1131.py failing because `_TASK_DETAIL_KEYS` frozenset (:132-135) includes `claimed_by` which `SingleTaskResponse` explicitly excludes (`Field(exclude=True)` + `data.pop("claimed_by")` at serve/kanban/src/owlbear_kanban/models.py:327). The constant encodes the dead `TaskDetailOut` schema — a pre-existing defect exposed when #1146 touched the file for comment cleanup. Additionally, residual dead-model name references in comments at test_occ_frontend_wire_1137.py:8 and test_cockpit_read_api.py:498,506-507,587,595 were missed in cycle 1.

### AC Amendments (supersede original where they differ)

**AC3 expanded:**
- Original scope: "Update stale comments and docstrings referencing removed model names in the [comment-only] files"
- Amended scope: "Update stale comments, docstrings, and test-utility constants referencing removed model names or their schemas. Includes:
  - `_TASK_DETAIL_KEYS` in test_cockpit_mutation_race_1131.py:132-135: remove `claimed_by` from the frozenset, update '14-key' references to '13-key' in the adjacent comment (:131) and class docstring (:276)
  - Residual comment references in test_occ_frontend_wire_1137.py (:8 module docstring 'TaskSummaryOut') and test_cockpit_read_api.py (:498, :506-507 'TaskSummaryOut'; :587, :595 'TaskDetailOut')"

**AC4 tightened:**
- Amended: "All tests pass after removal; no new test failures. Proof: quality-runner impacted-suite run on ALL Files-listed test files must be green."

### Impact Matrix Update

Moved `test_cockpit_mutation_race_1131.py` from "Comment-only references" to "Test files requiring cleanup":

| File | Dead references | Changes |
|------|----------------|---------|
| tests/test_cockpit_mutation_race_1131.py | `_TASK_DETAIL_KEYS` includes stale `claimed_by`; "14-key" count stale; "TaskDetailOut" in comments/docstrings | Remove `claimed_by` from frozenset; update "14" → "13" in comment (:131) and docstring (:276); clean TaskDetailOut references per cycle 1 |

Added to comment-only references table:

| File | Reference |
|------|-----------|
| tests/test_occ_frontend_wire_1137.py | Module docstring (:8) references "TaskSummaryOut" |
| tests/test_cockpit_read_api.py | Section comments (:498, :587) and docstrings (:506-507, :595) reference "TaskSummaryOut" / "TaskDetailOut" |

### Test-Writer Guidance
Add task-owned proof in test_cockpit_models_1146.py for the `_TASK_DETAIL_KEYS` fix:
- Test that `claimed_by` is NOT in `_TASK_DETAIL_KEYS` (guards AC3 constant fix)
- Test that the comment on the line immediately before `_TASK_DETAIL_KEYS` does NOT contain "14" (guards count update)
Add task-owned proof for the new comment-reference files:
- Test that test_occ_frontend_wire_1137.py module docstring does NOT contain "TaskSummaryOut"
- Test that test_cockpit_read_api.py does NOT contain "TaskSummaryOut" or "TaskDetailOut" in comment/docstring lines

### Builder Guidance (amended)
- Fix `_TASK_DETAIL_KEYS` FIRST — remove `claimed_by`, update "14" → "13" — this unblocks the 2 red schema-baseline tests
- Clean residual comment references in test_occ_frontend_wire_1137.py and test_cockpit_read_api.py (pure docstring/comment edits, no behavioral changes)
- Run impacted-suite via quality-runner on ALL files in the Files section to verify AC4

### Evaluation (Cycle 2)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes remove references to 5 dead models. _TASK_DETAIL_KEYS fix is the dead TaskDetailOut schema constant. |
| Interface clarity | PASS | AC3/AC4 now specify exact files, lines, and proof requirements. |
| Dependency correctness | PASS | #1144 archived/done. No other dependencies. |
| Module layering | PASS | All changes in test files and cockpit models.py (leaf module). |
| TDD compliance | PASS | Task-owned test suite exists. Test-writer guidance added for new proof. |
| KISS/YAGNI | PASS | Minimal scope: remove dead code, fix stale constant, clean references. |
| Premise challenge | PASS | All 5 models confirmed dead. _TASK_DETAIL_KEYS encodes dead schema. |
| Pattern consistency | PASS | Standard dead code cleanup. |
| Security surface | PASS | Purely subtractive. No new boundaries. |
| Single domain | PASS | All cockpit domain. |

### Challenge Results
- Challenger: reconsider (0.38)
- Concerns: (1) task body doesn't reflect refinements, (2) 1131 fix is executable not comment-only, (3) no AC-owned proof for constant fix, (4) ambiguous read_api scoping
- Architect response: (1) accepted — refinements written into body; (2) accepted — moved 1131 from comment-only to test cleanup table; (3) accepted — added test-writer guidance for task-owned proof; (4) partially accepted — scoped to exact lines, all in comments/docstrings

### Verdict: APPROVE (after REFINE)
### Action Taken: Expanded AC3 scope to include _TASK_DETAIL_KEYS constant fix and 2 additional comment-reference files. Tightened AC4 proof requirement. Moved test_cockpit_mutation_race_1131.py from comment-only to test cleanup. Added test-writer and builder guidance. Advanced to todo.
[[2026-04-27]]
## Architecture Review (Cycle 2) — Summary\nRefined AC3 to include _TASK_DETAIL_KEYS constant fix (remove claimed_by, update 14→13) and 2 additional comment-reference files. Tightened AC4 with explicit impacted-suite proof requirement. Moved test_cockpit_mutation_race_1131.py from comment-only to test cleanup. Added test-writer guidance for task-owned proof of constant fix. Challenger reconsider (0.38) — all 3 critical concerns addressed via refinement.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_models_1146.py
- Retry: added 5 new failing tests across 3 new TestFromAC_ classes to cover Cycle 2 AC3 expansions
- New classes: TestFromAC_TaskDetailKeysConstantFix (2 tests), TestFromAC_CommentRefs1137DocstringClean (1 test), TestFromAC_CommentRefsReadApiClean (2 tests)
- Tests per category (new only): structural/source-scan 5
- Total: 29 tests — 24 cycle-1 PASS (existing, preserved), 5 cycle-2 FAIL
- ruff: clean
- Commit: 984259bf

### AC Coverage (Cycle 2 additions)
| AC | Tests |
|----|-------|
| AC3: _TASK_DETAIL_KEYS does not contain claimed_by | test_task_detail_keys_does_not_contain_claimed_by |
| AC3: comment before _TASK_DETAIL_KEYS does not say "14" | test_task_detail_keys_preceding_comment_does_not_reference_14 |
| AC3: test_occ_frontend_wire_1137.py module docstring no TaskSummaryOut | test_1137_module_docstring_no_task_summary_out |
| AC3: test_cockpit_read_api.py no TaskSummaryOut in comments | test_read_api_no_task_summary_out_in_comments |
| AC3: test_cockpit_read_api.py no TaskDetailOut in comments | test_read_api_no_task_detail_out_in_comments |
[[2026-04-27]]
## Builder Notes
- Implementation: updated stale schema/comment references in tests/test_cockpit_mutation_race_1131.py, tests/test_occ_frontend_wire_1137.py, and tests/test_cockpit_read_api.py to match the dead-model cleanup contract.
- Fixes applied:
  - Removed `"claimed_by"` from `_TASK_DETAIL_KEYS` in mutation race tests and updated related 14-key wording to 13-key.
  - Reworded 1137 module docstring AC bullet to remove dead `TaskSummaryOut` model reference.
  - Reworded read API section comments/docstrings to remove dead `TaskSummaryOut` / `TaskDetailOut` references.
- Tests (task suite): 29 passed, 0 failed in tests/test_cockpit_models_1146.py.
- Tests (AC4 impacted suite): 236 passed, 0 failed across:
  - tests/test_cockpit_models_1146.py
  - tests/test_cockpit_read_api_930.py
  - tests/test_cockpit_read_api.py
  - tests/test_occ_frontend_wire_1137.py
  - tests/test_cockpit_mutation_race_1131.py
  - tests/test_cockpit_mutation_api_1132.py
  - tests/test_cockpit_mutation_api.py
  - tests/test_cockpit_kanban_routes_1082.py
- Coverage: 100% on owlbear_cockpit.models (6 statements, 0 missed).
- ruff: clean on all changed files and target model file.
- Commit: test: align stale schema/comment refs for #1146 (builder) [90778b1b].

## Post-task Reflection
- The prior red failures were contract-drift in test constants/comments, not runtime behavior regressions.
- The smallest safe fix was textual alignment in the exact files named by cycle-2 AC refinement.
- Running both task-scoped and impacted-suite quality-runner checks prevented repeating the earlier false-green gap on AC4 evidence.

[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner (task-owned suite): pytest 29 passed, 0 failed on `tests/test_cockpit_models_1146.py`
- quality-runner (AC4 impacted-suite scope): pytest 236 passed, 0 failed across the task file plus the 7 files listed in the task body
- quality-runner (discrepancy check): pytest 7 passed, 0 failed on `tests/test_cockpit_mutation_race_1131.py`
- An earlier failing quality-runner report was not reproduced on targeted rerun; final verdict uses the reproduced green reruns above

### Lint
- ruff: clean on `serve/cockpit/src/owlbear_cockpit/models.py` and all scoped task files

### Coverage
- `owlbear_cockpit.models`: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 Remove unused models from `serve/cockpit/src/owlbear_cockpit/models.py`; keep only `BoardOut`; remove `Field`/`model_validator` if unused | `tests/test_cockpit_models_1146.py::TestFromAC_DeadModelsRemoved`, `::TestFromAC_ModelsImportsClean` | Yes. Importing any removed model raises `ImportError`; source scans fail if `Field`/`model_validator` remain; direct source read shows only `BaseModel` import and `BoardOut` definition in `serve/cockpit/src/owlbear_cockpit/models.py:5-12`. | COVERED |
| AC2 Remove dead test imports/classes validating removed models | `tests/test_cockpit_models_1146.py::TestFromAC_TestImports930Clean`, `::TestFromAC_TestReadApiClean`, `::TestFromAC_Test1137Clean` | Yes. The task suite fails if the named dead imports/methods/class remain; direct no-match scans also confirmed the old imports/names are gone from `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api.py`, and `tests/test_occ_frontend_wire_1137.py`. | COVERED |
| AC3 Update stale comments/docstrings/constants in scoped files | `tests/test_cockpit_models_1146.py::TestFromAC_CommentRefs1131Clean`, `::TestFromAC_CommentRefs1132Clean`, `::TestFromAC_CommentRefsMutationApiClean`, `::TestFromAC_CommentRefs1082Clean`, `::TestFromAC_TaskDetailKeysConstantFix`, `::TestFromAC_CommentRefs1137DocstringClean`, `::TestFromAC_CommentRefsReadApiClean` | Yes for the refined AC scope. `_TASK_DETAIL_KEYS` no longer contains `claimed_by`, the adjacent comment no longer says `14`, and exact removed-model references are gone from the scoped comment/docstring files. | COVERED |
| AC4 All tests pass after removal; no new test failures | quality-runner impacted-suite rerun | Yes. Reproduced current-state run is green: 236 passed, 0 failed, plus clean ruff and 100% coverage on `owlbear_cockpit.models`. | COVERED |

#### Security Review
- No issues found. The only production change surface is the subtractive schema module `serve/cockpit/src/owlbear_cockpit/models.py`; no new secrets, injection sinks, path handling, deserialization, or dependency changes were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned `TestFromAC_*` suite in `tests/test_cockpit_models_1146.py` | Current file still contains the cycle-1 and cycle-2 proof classes described in task history, including the `_TASK_DETAIL_KEYS` fix checks and residual comment/docstring checks | PRESERVED |
| Legacy cleanup targets in `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api.py`, `tests/test_occ_frontend_wire_1137.py` | Dead imports/methods/class removed as authorized by AC2; surviving tests still cover live contracts | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC1 uses exact `ImportError` and exact source checks; AC2/AC3 use exact no-match assertions against the named dead imports, classes, and comment/docstring references. |
| Negative/error-path coverage | ADEQUATE | Removed-model imports are exercised as error paths in `TestFromAC_DeadModelsRemoved`. |
| Manual mutation reasoning | ADEQUATE | Reintroducing a removed model import, the deleted test ids/class, or `claimed_by` in `_TASK_DETAIL_KEYS` would fail the task suite; AC4 is additionally guarded by the reproduced impacted-suite rerun. |
| Test independence | STRONG | The task suite uses isolated imports and file-text scans; no shared mutable fixtures are required. |
| Descriptive names | STRONG | Task-owned classes and methods remain AC-mapped and specific. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No blocking untested paths found in task scope. The production module is a 1-model schema file, and the architect-scoped impacted-suite rerun is green.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `tests/test_cockpit_mutation_race_1131.py:28-29` and the legacy test ids at `:283` / `:296` still use historical `14/taskdetailout` wording.
- I am treating that as non-blocking drift, not an AC miss: the refined AC required the explicit `_TASK_DETAIL_KEYS` constant/comment/class-docstring fixes, those are present, and the impacted suite is green.
- This is a divergence from the code-reader’s stricter interpretation; after direct file verification and reproduced test runs, I do not find a blocking contract failure.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/src/owlbear_cockpit/models.py:5-12` only imports `BaseModel` and defines `BoardOut`; no `Field`/`model_validator` matches remain | `tests/test_cockpit_models_1146.py::TestFromAC_DeadModelsRemoved`; `::TestFromAC_ModelsImportsClean` | PASS |
| AC2 | No matches for dead imports/test ids in `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api.py`, or `tests/test_occ_frontend_wire_1137.py`; impacted suite rerun is green | `tests/test_cockpit_models_1146.py::TestFromAC_TestImports930Clean`; `::TestFromAC_TestReadApiClean`; `::TestFromAC_Test1137Clean` | PASS |
| AC3 | `_TASK_DETAIL_KEYS` excludes `claimed_by` in `tests/test_cockpit_mutation_race_1131.py:132-136`; task-owned cycle-2 checks at `tests/test_cockpit_models_1146.py:357`, `:373`, `:400`, `:425`, and `:433` all pass; exact removed-model names are absent from the scoped comment/docstring files | `tests/test_cockpit_models_1146.py::TestFromAC_CommentRefs1131Clean`; `::TestFromAC_TaskDetailKeysConstantFix`; `::TestFromAC_CommentRefs1137DocstringClean`; `::TestFromAC_CommentRefsReadApiClean` | PASS |
| AC4 | quality-runner reproduced green scoped evidence: pytest 236 passed, 0 failed; ruff clean; `owlbear_cockpit.models` coverage 100% | quality-runner impacted-suite rerun | PASS |

### Deductions
- -0.03 earlier quality-runner failure output was stale/non-reproduced and required a targeted rerun before a trustworthy verdict.
- -0.02 minor historical wording drift remains in one durable test file outside the refined AC proof surface.

### Verdict
- PASS | confidence 0.95

### Action
- Advance to docs.

### Post-task Reflection
- Initial evidence was contradictory; targeted reruns were necessary before trusting the gate result.
- For this repo, task-owned suite + architect-scoped impacted-suite is the right evidence set for dead-code cleanup; broader stale terminal context can mislead.
- Exact no-match scans were useful to verify subtractive cleanup beyond the green pytest report.

[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Grep across all README files: zero matches for removed model names (TaskSummaryOut, TaskDetailOut, TaskListOut, SessionListOut, SessionOut). serve/cockpit/README.md does not reference these models. |
| 2 | Module docstrings | Yes | Updated | serve/cockpit/src/owlbear_cockpit/models.py module docstring updated: "Pydantic response models for the cockpit read API." → "Pydantic response model for the cockpit GET /api/board endpoint." (plural → singular, scoped to /api/board). BoardOut class docstring is accurate as-is. |
| 3 | External attribution | No | N/A | Codebase-only research (confirmed in task body). No external sources used. |
| 4 | Research doc | No | N/A | Task body states "Sources: codebase-only". No research .md file produced. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | share/diagrams/cockpit.excalidraw has describes: serve/cockpit/src/**. Changed files include serve/cockpit/src/owlbear_cockpit/models.py. Footer updated: 2026-04-28 (c06b12e2) → 2026-04-28 (a14038d2). |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No IN-scope docs deleted. All file removals were Python test imports/methods/classes and model code — not doc files. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/src/owlbear_cockpit/models.py | IN (docstrings) | Updated module docstring |
| tests/test_cockpit_read_api_930.py | OUT (test file) | N/A |
| tests/test_cockpit_read_api.py | OUT (test file) | N/A |
| tests/test_occ_frontend_wire_1137.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_race_1131.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_api_1132.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_api.py | OUT (test file) | N/A |
| tests/test_cockpit_kanban_routes_1082.py | OUT (test file) | N/A |
| share/diagrams/cockpit.excalidraw | IN (diagram describes-match) | Footer updated |

### Files Updated
- serve/cockpit/src/owlbear_cockpit/models.py (module docstring)
- share/diagrams/cockpit.excalidraw (footer: 2026-04-28 a14038d2)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1146-* scratch files found)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 Remove unused models; keep BoardOut only; remove Field/model_validator | models.py:1-13 contains only BaseModel import and BoardOut class. No Field, no model_validator. Task suite 29/29 green. | PASS |
| AC2 Remove dead test imports/classes in listed files | Reviewer verified dead imports removed from test_cockpit_read_api_930.py, test_cockpit_read_api.py, test_occ_frontend_wire_1137.py. Task suite structural scans confirm. | PASS |
| AC3 Update stale comments/docstrings/constants (expanded cycle 2) | _TASK_DETAIL_KEYS excludes claimed_by, 14 changed to 13, dead model names removed from all scoped comment/docstring files. 5 cycle-2 proof tests pass. | PASS |
| AC4 All tests pass after removal | Reviewer impacted-suite: 236 passed, 0 failed. Full suite: 2737 passed; ~110 failures all pre-existing background debt (kanban corruption/storage, mcp-kanban, mcp-knowledge, react compiler) with zero cockpit-domain failures. | PASS |

### Test Results
- pytest (full suite): 2737 passed, ~110 failed (all pre-existing, none in task scope)
- ruff: clean on all cockpit files; 8 violations in non-cockpit packages (pre-existing)

### Architect Quality: 4/5
Cycle 1 AC was well-structured with impact matrix and exact file/test targets. AC3 scoping was initially too narrow (missed _TASK_DETAIL_KEYS constant and additional comment files), requiring cycle 2 refinement. Cycle 2 addressed all reviewer feedback comprehensively. Minor gap filled by iteration.

### Deduction Breakdown
- -0.01 reviewer needed targeted rerun to resolve stale evidence (inherited verification friction)
- -0.01 cycle 2 required due to initial AC3 scope gap (architect iteration overhead, resolved)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e222d4e8 | test | test_cockpit_models_1146.py | #1146 |
| f498330a | refactor | models.py, test files | #1146 |
| 984259bf | test | test_cockpit_models_1146.py | #1146 |
| 90778b1b | test | mutation_race, 1137, read_api | #1146 |
| a6179d77 | docs | models.py, cockpit.excalidraw | #1146 |
| 3d69d846 | chore | kanban task file | #1146 |