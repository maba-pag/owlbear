---
id: 1470
title: 'E2a-B5: Small-group merges — 40 files into 16 new durables'
status: backlog
priority: important
created: 2026-05-09T07:21:35.702938+00:00
updated: 2026-05-09T07:24:14.978830+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1415
depends_on:
- 1467
- 1468
- 1469
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Research: `.owlbear/research/1463-python-root-test-cleanup.md` §5c
Supersedes: #1463 (partial)

## Scope

Merge 40 task-scoped files into 16 NEW durable targets (all 2–3 file groups, no existing durable). Create each target, merge sources, delete sources.

**Note:** `test_decisions_1218.py` is listed in §5c under test_decisions group but should be DELETED (not merged) — broken import, see §3.3. If not already deleted by #1466, delete it here.

### Merge targets (§5c)

| Target | Sources | Files |
|--------|---------|:-----:|
| test_server.py | _1170, _1172, _1198, _1199, _1317, _1358 | 6 |
| test_decisions.py | _1180, _1181, _1195 (skip _1218) | 3 |
| test_cockpit_view.py | _1224, _1240, _1244 | 3 |
| test_mcp_memory.py | _1266, _1267, _1269 | 3 |
| test_storage.py | _1205, _1206 | 2 |
| test_memory_engine.py | _1270, _1271 | 2 |
| test_mcp_knowledge_phase2_tools.py | _1329, _1330 | 2 |
| test_init_exports.py | _1213, _1350 | 2 |
| test_engine_dead_code.py | _1112, _1204 | 2 |
| test_engine_create_edit.py | _1072, _1203 | 2 |
| test_corruption.py | _1057, _1368 | 2 |
| test_cockpit_pds_build_compat.py | _1364, _1365 | 2 |
| test_cockpit_events.py | _1234, _1262 | 2 |
| test_cockpit_error_envelope.py | _1370, _1371 | 2 |
| test_cockpit_cache_sse.py | _1346, _1401 | 2 |
| test_browser_fetcher_wiring.py | _1325, _1326 | 2 |

## AC (td:0)

- [ ] 16 new durable files created, each containing all `def test_*` from their source files
- [ ] Duplicate test-name collisions within each group resolved by renaming to `test_{name}_1470`
- [ ] Fixture collisions within each group: pick one, rename the other if different
- [ ] All 40 source files deleted after merge (39 merged + 1 deleted outright)
- [ ] Per-target checkpoint after EACH target: `uv run pytest tests/{target}.py --collect-only -q` — stop and investigate if count < sum of source test counts
- [ ] `test_decisions_1218.py` deleted (not merged)
- [ ] Full suite: `uv run pytest tests/ --collect-only -q` count does not decrease vs pre-task baseline
- [ ] `uv run pytest tests/ -x` passes with no new failures
- [ ] `test_kanban_topology_1439.py` untouched

## Out of scope

- Merges into existing durables (cockpit_decisions_api, cockpit_mutation_api, mcp_kanban) — #1467, #1468, #1469
- Renames — handled in #1466


## AC Correction (architect)
**Replace** all `pytest -x` AC lines with delta-based verification:
- Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline before any changes)
- Collected test count ≥ pre-task collect-only baseline

**Replace** collision rename suffix `_1470` with the source file's original task ID for traceability.

**Note:** `test_decisions_1218.py` should already be deleted by #1466. If still present, delete it here (do not merge).