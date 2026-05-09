# Python Root Test Cleanup — Validated File Lists

> **Owning task:** #1463 — E2a: Delete/merge stale Python root tests (82 files in tests/)
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

Parent brief (#1415) estimated 82 stale task-scoped files in `tests/`. This research validates the count, corrects the categorization, and produces exact file lists for the builder.

**Question:** Are the AC counts accurate? What's the precise execution plan?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `tests/test_*_*.py` filesystem scan | 1.0 | 84 task-scoped files found |
| S2 | Kanban board (MCP + archive) | 1.0 | 83 archived/done, 1 active (#1439) |
| S3 | `.owlbear/research/1415-stale-test-cleanup.md` | .90 | Parent categorization — validated and corrected |
| S4 | `owlbear_cockpit.routes.decisions` source | 1.0 | `_validate_decision_id()` confirms #1218 security concern addressed |

## 3. Analysis

### 3.1 Updated Counts (parent brief → validated)

| Category | Brief | Actual | Delta | Reason |
|----------|:-----:|:------:|:-----:|--------|
| Delete (durable exists) | 20 | 22 | +2 | #1448 done, #1450 archived since brief |
| Rename (single, no durable) | 21 | 21 | 0 | |
| Merge (multi-file groups) | 40 | 40 | 0 | |
| Active (retain) | 2 | 1 | −1 | #1448 done; only #1439 active |
| **Total task-scoped** | **83** | **84** | **+1** | |

Baseline: 3272 collected tests (excluding test_decisions_1218.py). Suite must pass ≥ 3272 after cleanup.

### 3.2 Critical Finding: DELETE ≠ Simple Delete

Task-scoped files in the "durable exists" group contain significant unique tests:

| Module | Durable tests | Task-scoped tests | Risk |
|--------|:-----:|:-----:|------|
| cockpit_decisions_api | 10 | 72 (6 files) | HIGH — must merge unique tests into durable first |
| cockpit_mutation_api | 53 | 105 (7 files) | HIGH — must merge unique tests |
| mcp_kanban | 67 | 53 (7 files) | MEDIUM — likely overlap but verify |
| cockpit_read_api | 71 | 9 (1 file) | LOW — probably subset |
| pipeline_diagram | 22 | 2 (1 file) | LOW — probably subset |

**Strategy:** For each file: check if all `def test_*` names exist in durable. If not, merge unique tests into durable, then delete task file. This makes the "delete" batch operationally similar to the "merge" batch.

### 3.3 test_decisions_1218.py — P3 AC

- **Status:** Permanently broken. Imports `_find_decision_path` which never existed.
- **History:** RED-phase test for task #1218 (archived). The security concern (path traversal on `decision_id`) was implemented as `_validate_decision_id()` with regex + 422.
- **Coverage:** Path traversal validation is tested in `test_cockpit_decisions_api_1384.py` and `_1385.py` (both in the merge-into-durable batch).
- **Verdict:** Delete. 0 test regression risk.

### 3.4 Execution Order

1. **Rename (21 files)** — `git mv`, zero risk, immediate win
2. **Delete-with-merge (22 files)** — merge unique tests into durable, then delete
3. **Merge (40 files / 16 groups)** — create durable file per group
4. **Delete test_decisions_1218.py** — broken, covered elsewhere
5. **Full suite verification** — must pass ≥ 3272 tests

## 4. Recommendation (confidence: .90)

Proceed as T1 autonomous cleanup. The work is mechanical — no architecture decisions. The only risk is coverage regression during merge, mitigated by running the full suite after each batch.

**AC correction needed:** P1 "20 files deleted" → "22 files merged-then-deleted" (accounts for #1448/#1450 completing).

Challenge: SKIPPED — T1 mechanical cleanup, no architectural recommendation.

## 5. File Lists

### 5a. RENAME — 21 files (drop `_{id}` suffix)

| Current | Target |
|---------|--------|
| test_support_module_migration_1176.py | test_support_module_migration.py |
| test_state_machine_1304.py | test_state_machine.py |
| test_reviewer_rewrite_1407.py | test_reviewer_rewrite.py |
| test_pick_tasks_resolve_1184.py | test_pick_tasks_resolve.py |
| test_path_neutrality_1285.py | test_path_neutrality.py |
| test_occ_frontend_wire_1137.py | test_occ_frontend_wire.py |
| test_memory_tools_1272.py | test_memory_tools.py |
| test_memory_models_1268.py | test_memory_models.py |
| test_mcp_lifecycle_1173.py | test_mcp_lifecycle.py |
| test_kanban_config_path_validation_1351.py | test_kanban_config_path_validation.py |
| test_engine_rebind_containment_1357.py | test_engine_rebind_containment.py |
| test_engine_occ_1341.py | test_engine_occ.py |
| test_engine_lazy_agent_map_1221.py | test_engine_lazy_agent_map.py |
| test_engine_end_work_fail_1125.py | test_engine_end_work_fail.py |
| test_engine_end_work_1080.py | test_engine_end_work.py |
| test_engine_dep_lookup_1207.py | test_engine_dep_lookup.py |
| test_engine_ble001_1202.py | test_engine_ble001.py |
| test_edit_task_contract_1348.py | test_edit_task_contract.py |
| test_doc_writer_quality_1422.py | test_doc_writer_quality.py |
| test_cockpit_react_compiler_1015.py | test_cockpit_react_compiler.py |
| test_cockpit_cache_populate_1402.py | test_cockpit_cache_populate.py |

### 5b. DELETE-WITH-MERGE — 22 files (merge unique tests into durable first)

**Durable: test_cockpit_decisions_api.py** (10 tests) ← merge from:
- test_cockpit_decisions_api_1189.py (8 tests)
- test_cockpit_decisions_api_1190.py (26 tests)
- test_cockpit_decisions_api_1194.py (3 tests)
- test_cockpit_decisions_api_1345.py (5 tests)
- test_cockpit_decisions_api_1384.py (23 tests)
- test_cockpit_decisions_api_1385.py (7 tests)

**Durable: test_cockpit_mutation_api.py** (53 tests) ← merge from:
- test_cockpit_mutation_api_1132.py (28 tests)
- test_cockpit_mutation_api_1134.py (9 tests)
- test_cockpit_mutation_api_1135.py (14 tests)
- test_cockpit_mutation_api_1239.py (12 tests)
- test_cockpit_mutation_api_1243.py (19 tests)
- test_cockpit_mutation_api_1344.py (5 tests)
- test_cockpit_mutation_api_1448.py (18 tests)

**Durable: test_cockpit_read_api.py** (71 tests) ← merge from:
- test_cockpit_read_api_1223.py (9 tests)

**Durable: test_mcp_kanban.py** (67 tests) ← merge from:
- test_mcp_kanban_1091.py (3 tests)
- test_mcp_kanban_1092.py (7 tests)
- test_mcp_kanban_1126.py (1 test)
- test_mcp_kanban_1196.py (12 tests)
- test_mcp_kanban_1197.py (5 tests)
- test_mcp_kanban_1360.py (8 tests)
- test_mcp_kanban_1450.py (17 tests)

**Durable: test_pipeline_diagram.py** (22 tests) ← merge from:
- test_pipeline_diagram_1299.py (2 tests)

### 5c. MERGE — 40 files into 16 new durable files

| Target durable file | Source files | Total tests |
|---------------------|:-----:|:-----:|
| test_server.py | _1170, _1172, _1198, _1199, _1317, _1358 | 6 files |
| test_decisions.py | _1180, _1181, _1195, _1218 | 4 files |
| test_cockpit_view.py | _1224, _1240, _1244 | 3 files |
| test_mcp_memory.py | _1266, _1267, _1269 | 3 files |
| test_storage.py | _1205, _1206 | 2 files |
| test_memory_engine.py | _1270, _1271 | 2 files |
| test_mcp_knowledge_phase2_tools.py | _1329, _1330 | 2 files |
| test_init_exports.py | _1213, _1350 | 2 files |
| test_engine_dead_code.py | _1112, _1204 | 2 files |
| test_engine_create_edit.py | _1072, _1203 | 2 files |
| test_corruption.py | _1057, _1368 | 2 files |
| test_cockpit_pds_build_compat.py | _1364, _1365 | 2 files |
| test_cockpit_events.py | _1234, _1262 | 2 files |
| test_cockpit_error_envelope.py | _1370, _1371 | 2 files |
| test_cockpit_cache_sse.py | _1346, _1401 | 2 files |
| test_browser_fetcher_wiring.py | _1325, _1326 | 2 files |

**Note:** test_decisions_1218.py is in this group but should be DELETED (not merged) — see §3.3.

### 5d. RETAIN — 1 file

- test_kanban_topology_1439.py — task #1439 is active (`todo`)
