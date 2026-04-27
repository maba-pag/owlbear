---
id: 1146
title: Remove dead cockpit response models (TaskSummaryOut, TaskDetailOut, etc.)
status: in-progress
priority: someday
created: 2026-04-27T18:30:12.019145+00:00
updated: 2026-04-27T20:42:47.923178+00:00
tags:
- scope:cockpit
parent:
depends_on:
- 1144
blocked: false
block_reason:
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