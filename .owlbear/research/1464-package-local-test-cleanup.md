# Package-Local Test Cleanup (serve/*/tests/)

> **Owning task:** #1464 — E2b: Delete/merge stale package-local Python tests (43 files in serve/*/tests/)
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

Task-scoped test files with `_NNNN.py` suffixes in `serve/*/tests/` need cleanup: delete duplicates, rename singles, merge multiples. This research validates the count, categorizes each file's cleanup action, and checks for durable-file overlap.

**Question:** What is the safest categorization (delete/rename/merge) for each of the 43 task-scoped files?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `find serve/*/tests/ -name 'test_*_[0-9]*.py'` | 1.0 | 43 task-scoped files confirmed |
| S2 | `find serve/*/tests/ -name 'test_*.py'` (non-task) | 1.0 | 29 durable files identified |
| S3 | Durable vs task-scoped test function overlap | 1.0 | Coverage overlap for kanban + mcp-kanban |
| S4 | `.owlbear/research/1415-stale-test-cleanup.md` | .90 | Parent research — approach validated |

## 3. Analysis

### 3.1 File Distribution by Package

| Package | Task-scoped | Durable | Action breakdown |
|---------|:-:|:-:|:---|
| kanban | 22 | 12 | 9 rename, 5 merge-into-durable, 8 merge-new (4 groups) |
| mcp-kanban | 13 | 5 | 6 rename, 7 merge-guidance (1 group) |
| knowledge | 2 | 4 | 2 merge-new (1 group) |
| mcp-browser | 1 | 0 | 1 rename |
| mcp-knowledge | 4 | 7 | 4 rename |
| tools | 1 | 1 | 1 rename |
| **Total** | **43** | **29** | **21 rename, 10 merge-new, 5 merge-durable, 7 merge-guidance** |

### 3.2 RENAME — 21 files (drop `_NNNN` suffix, no other changes)

Sole task-scoped file for its module, no durable equivalent exists.

| # | Current file | Target | Pkg |
|---|---|---|---|
| 1 | test_engine_archived_edit_1120.py | test_engine_archived_edit.py | kanban |
| 2 | test_engine_atomicity_1104.py | test_engine_atomicity.py | kanban |
| 3 | test_engine_crash_safety_1101.py | test_engine_crash_safety.py | kanban |
| 4 | test_engine_create_edit_1070.py | test_engine_create_edit.py | kanban |
| 5 | test_engine_end_work_1077.py | test_engine_end_work.py | kanban |
| 6 | test_engine_list_show_1071.py | test_engine_list_show.py | kanban |
| 7 | test_engine_reads_1069.py | test_engine_reads.py | kanban |
| 8 | test_mtime_cache_942.py | test_mtime_cache.py | kanban |
| 9 | test_yaml12_loader_940.py | test_yaml12_loader.py | kanban |
| 10 | test_ssrf_preflight_950.py | test_ssrf_preflight.py | mcp-browser |
| 11 | test_mcp_create_dr_1182.py | test_mcp_create_dr.py | mcp-kanban |
| 12 | test_mcp_kanban_dir_1349.py | test_mcp_kanban_dir.py | mcp-kanban |
| 13 | test_mcp_models_1084.py | test_mcp_models.py | mcp-kanban |
| 14 | test_mcp_mutation_tools_1087.py | test_mcp_mutation_tools.py | mcp-kanban |
| 15 | test_mcp_server_1090.py | test_mcp_server.py | mcp-kanban |
| 16 | test_tool_annotations_494.py | test_tool_annotations.py | mcp-kanban |
| 17 | test_null_safety_539.py | test_null_safety.py | mcp-knowledge |
| 18 | test_outputschema_541.py | test_outputschema.py | mcp-knowledge |
| 19 | test_ssrf_fix_946.py | test_ssrf_fix.py | mcp-knowledge |
| 20 | test_tool_annotations_501.py | test_tool_annotations.py | mcp-knowledge |
| 21 | test_doc_index_1018.py | test_doc_index.py | tools |

### 3.3 MERGE-NEW — 10 files → 5 durable files

Multiple task files for same module, no durable exists. Combine into one new file.

| Group | Files | Target | Pkg |
|---|---|---|---|
| A | test_engine_init_1067 + _1068 | test_engine_init.py | kanban |
| B | test_engine_pick_tasks_1074 + _1076 | test_engine_pick_tasks.py | kanban |
| C | test_engine_coverage_1068 + _1110 | test_engine_coverage.py | kanban |
| D | test_idtofilename_cache_943 + _944 | test_idtofilename_cache.py | kanban |
| E | test_ssrf_fix_947 + _948 | test_ssrf_fix.py | knowledge |

### 3.4 MERGE-INTO-DURABLE — 5 files → existing durables

Task file has unique tests not in durable. Merge unique tests into durable, delete task file.

| Task file | Merge into | Unique tests | Pkg |
|---|---|---|---|
| test_engine_move_claim_1075 | test_engine_move_claim.py | CAS primitive, edge cases | kanban |
| test_list_sessions_952 | test_list_sessions.py | detail string formatting | kanban |
| test_storage_1050 | test_storage.py | extended frontmatter/timestamp tests | kanban |
| test_storage_1059 | test_storage.py | module structure, import verification | kanban |
| test_storage_io_1055 | test_storage_io.py | directory exclusion, regular-file check | kanban |

### 3.5 MERGE-GUIDANCE — 7 files → replace durable

The 7 guidance task files (mcp-kanban) supersede `test_guidance.py` with refined AC tests.

| Files | Target | Notes |
|---|---|---|
| test_guidance_{edit_task,end_work,move_task,rules}_973 + test_guidance_rules_987 + test_guidance_server_980 + test_mcp_guidance_1089 | test_guidance.py | Durable has 12 tests; task files collectively have 50+. Full replacement. |

### 3.6 Risk Assessment

| Risk | Severity | Mitigation |
|---|:---:|---|
| Test loss from bad merge | Medium | Run suite before/after each batch; compare pass counts |
| Import/fixture conflicts on merge | Low | Mechanical — deduplicate imports, reconcile fixture names |
| conftest.py breakage | Low | Only `serve/kanban/tests/conftest.py` exists; no changes needed |
| Cross-package interference | None | Each package tested independently |

## 4. Recommendation

Execute in 3 batches by operation type (confidence: .90):

1. **Renames first** (21 files) — safest, zero-risk `git mv`
2. **Merge-new** (10 files → 5 durables) — concatenate, deduplicate imports
3. **Merge-into-durable + merge-guidance** (12 files) — highest care needed

Run `uv run pytest serve/{pkg}/tests/ -q` before and after each batch per package.

Challenge: SKIPPED — T1 autonomous mechanical cleanup, no architectural recommendation.

## 5. Follow-up Tasks

This task proceeds directly to backlog — the categorization above IS the implementation spec. No sub-decomposition needed (single builder task, mechanical operations).
