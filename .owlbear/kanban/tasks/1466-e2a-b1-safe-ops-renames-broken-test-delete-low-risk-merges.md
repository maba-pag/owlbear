---
id: 1466
title: 'E2a-B1: Safe ops — renames, broken-test delete, low-risk merges'
status: backlog
priority: important
created: 2026-05-09T07:21:35.470966+00:00
updated: 2026-05-09T07:24:15.245946+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1415
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Research: `.owlbear/research/1463-python-root-test-cleanup.md`
Supersedes: #1463

## Scope

Safe, low-risk operations from research doc §5:

1. **21 renames** (git mv, drop `_{id}` suffix) — full list in §5a
2. **Delete** `test_decisions_1218.py` (broken RED-phase test, see §3.3)
3. **Merge** `test_cockpit_read_api_1223.py` → `test_cockpit_read_api.py` (9 tests, LOW risk)
4. **Merge** `test_pipeline_diagram_1299.py` → `test_pipeline_diagram.py` (2 tests, LOW risk)

### Rename list (§5a)

| Current → Target |
|---|
| test_support_module_migration_1176 → test_support_module_migration |
| test_state_machine_1304 → test_state_machine |
| test_reviewer_rewrite_1407 → test_reviewer_rewrite |
| test_pick_tasks_resolve_1184 → test_pick_tasks_resolve |
| test_path_neutrality_1285 → test_path_neutrality |
| test_occ_frontend_wire_1137 → test_occ_frontend_wire |
| test_memory_tools_1272 → test_memory_tools |
| test_memory_models_1268 → test_memory_models |
| test_mcp_lifecycle_1173 → test_mcp_lifecycle |
| test_kanban_config_path_validation_1351 → test_kanban_config_path_validation |
| test_engine_rebind_containment_1357 → test_engine_rebind_containment |
| test_engine_occ_1341 → test_engine_occ |
| test_engine_lazy_agent_map_1221 → test_engine_lazy_agent_map |
| test_engine_end_work_fail_1125 → test_engine_end_work_fail |
| test_engine_end_work_1080 → test_engine_end_work |
| test_engine_dep_lookup_1207 → test_engine_dep_lookup |
| test_engine_ble001_1202 → test_engine_ble001 |
| test_edit_task_contract_1348 → test_edit_task_contract |
| test_doc_writer_quality_1422 → test_doc_writer_quality |
| test_cockpit_react_compiler_1015 → test_cockpit_react_compiler |
| test_cockpit_cache_populate_1402 → test_cockpit_cache_populate |

## AC (td:0)

- [ ] All 21 renames completed via `git mv` (no copy+delete)
- [ ] `test_decisions_1218.py` deleted
- [ ] Unique tests from `test_cockpit_read_api_1223.py` merged into `test_cockpit_read_api.py`; source deleted
- [ ] Unique tests from `test_pipeline_diagram_1299.py` merged into `test_pipeline_diagram.py`; source deleted
- [ ] Duplicate test-name collisions resolved by renaming incoming test to `test_{name}_1466`
- [ ] Fixture collisions: keep target's if identical, rename source's if different
- [ ] `uv run pytest tests/ --collect-only -q` collects ≥ 3272 tests
- [ ] `uv run pytest tests/ -x` passes with no new failures
- [ ] `test_kanban_topology_1439.py` untouched

## Out of scope

- High-risk merges (cockpit_decisions_api, cockpit_mutation_api, mcp_kanban) — #1467, #1468, #1469
- Small-group merges (40 files → 16 targets) — #1470


## AC Correction (architect)
**Replace** the AC line `uv run pytest tests/ -x passes with no new failures` with:
- Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline before any changes using `uv run pytest tests/ -q --tb=no -n 0 --ignore=tests/test_decisions_1218.py | tail -1`)

**Replace** `collects ≥ 3272 tests` with:
- Collected test count ≥ pre-task collect-only baseline (capture using `uv run pytest tests/ --collect-only -q --ignore=tests/test_decisions_1218.py | tail -1`)

**Replace** collision rename suffix `_1466` with the source file's original task ID (e.g., `test_{name}_1223` for tests coming from `_1223.py`) for traceability.