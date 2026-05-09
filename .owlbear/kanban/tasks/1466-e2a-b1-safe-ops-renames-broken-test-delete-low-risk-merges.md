---
id: 1466
title: 'E2a-B1: Safe ops — renames, broken-test delete, low-risk merges'
status: docs
priority: important
created: 2026-05-09T07:21:35.470966+00:00
updated: 2026-05-09T10:09:47.879525+00:00
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
[[2026-05-09]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: safe mechanical test file operations (renames, delete, 2 low-risk merges) |
| Interface clarity | PASS | AC lines are verifiable. AC Correction section (already in body) refines test-count and failure-count gates to baseline-relative — builder must apply those corrections. |
| Dependency correctness | PASS | No deps needed — first batch of safe ops, no ordering constraints |
| Module layering | N/A | No code changes — file operations only |
| TDD compliance | PASS | All td:0 mechanical ops. `quality` tag present for test-writer pass-through. |
| KISS/YAGNI | PASS | Minimal scope — renames, 1 delete, 2 low-risk merges |
| Premise challenge | PASS | 21 stale suffixed files confirmed present; targets confirmed absent. Research §3.3 justifies deletion. |
| Pattern consistency | PASS | Drops task-ID suffixes per C2 durable naming convention |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Merge Collision Analysis (codebase-verified)
**Merge 1 (cockpit_read_api_1223 → cockpit_read_api):** 3 fixture collisions (`board_dir`, `engine`, `client`) — all DIFFERENT implementations. Source's fixtures are simpler (no cache, empty board). AC line "rename source's if different" applies. 0 test-name collisions among 9 incoming tests.

**Merge 2 (pipeline_diagram_1299 → pipeline_diagram):** 0 fixture collisions, 0 test-name collisions. 2 incoming tests, safe merge.

### AC Corrections (validated)
The "AC Correction (architect)" section already in the body is sound:
1. Baseline-relative test collection count replaces hardcoded ≥3272 — correct, avoids false fail if baseline drifts
2. Baseline-relative failure count replaces `-x` pass — correct, accommodates pre-existing failures
3. Source-file task ID suffix (e.g. `_1223`) replaces `_1466` — correct, preserves origin traceability

Builder: apply these corrections when executing — they supersede the original AC lines.

### Test Depth
- All AC lines: (td:0) — mechanical file operations
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Reason: Mechanical cleanup with no architectural decisions

### Design Diverge
- Skipped — single approach (file operations), no competing designs

### Verdict: APPROVE
### Action Taken
- Verified all 21 source files exist, all 21 target paths are clear
- Verified merge collision risk for both merge targets
- Validated AC Correction section — builder applies corrections over original AC lines
- `quality` tag present for test-writer pass-through
- Advancing to todo
[[2026-05-09]]
Architecture review complete. All 21 rename sources verified present, all targets clear. Merge collision analysis: cockpit_read_api has 3 fixture collisions (all different, covered by existing AC), pipeline_diagram clean. AC Corrections validated — builder applies baseline-relative gates and source-file task ID suffixes. All td:0, test-writer SKIP. Advancing to todo.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — all AC lines are `(td:0)` mechanical file operations (renames, delete, 2 merges).
- Architecture review explicitly marked: Test-writer: SKIP.
- No testable Python interfaces. Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation:
  - Completed 21 safe `git mv` renames dropping task-id suffixes.
  - Deleted `tests/test_decisions_1218.py`.
  - Merged unique tests from `tests/test_cockpit_read_api_1223.py` into `tests/test_cockpit_read_api.py`, then deleted source file.
  - Merged unique tests from `tests/test_pipeline_diagram_1299.py` into `tests/test_pipeline_diagram.py`, then deleted source file.
  - Updated dependent path-reference tests to renamed durable file paths:
    - `tests/test_cockpit_view_1224.py`
    - `tests/test_cockpit_models.py`
    - `tests/test_storage_re_exports.py`
- AC correction baselines captured pre-change:
  - Collect-only baseline: `3299 tests collected`
  - Failure baseline: `427 failed, 2868 passed, 4 skipped`
- Verification evidence (quality-runner):
  - `uv run pytest tests/ --collect-only -q --ignore=tests/test_decisions_1218.py | tail -1`
    - `3299 tests collected in 1.12s` (meets `>= 3299`)
  - `uv run pytest tests/ -q --tb=no -n 0 --ignore=tests/test_decisions_1218.py | tail -1`
    - `427 failed, 2868 passed, 4 skipped in 69.16s` (meets `<= 427`)
  - Focused merged-target regression:
    - `uv run pytest tests/test_cockpit_read_api.py tests/test_pipeline_diagram.py -q --tb=line -n 0`
    - `119 passed, 0 failed`
- Lint status:
  - Not run in this task (td:0 mechanical file operations; acceptance gates are baseline-relative pytest metrics).
- Guardrail checks:
  - `tests/test_kanban_topology_1439.py` untouched (clean in `git status --porcelain`).
- Commits:
  - `d23dd134` chore: apply ws-cleanup safe ops (#1466, builder)
  - `0e81a895` chore: finalize ws-cleanup deletions (#1466, builder)
- Outcome: all corrected AC gates satisfied; advancing to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- Quality-runner collect-only gate excluding the deleted RED file: 3376 collected. Builder baseline was 3299. PASS.
- Quality-runner full failure-count gate excluding the deleted RED file: 427 failed, 2945 passed, 4 skipped. Builder baseline was 427 failed. PASS.
- Quality-runner focused regression on the two merged durable suites: 119 passed, 0 failed.

### Lint Results
- Ruff clean on the five touched durable tests: tests/test_cockpit_read_api.py, tests/test_pipeline_diagram.py, tests/test_cockpit_view_1224.py, tests/test_cockpit_models.py, tests/test_storage_re_exports.py.

### Coverage
- Skipped. td:0 mechanical cleanup task.

### Structural Review
- Git evidence: commit d23dd134 records all 21 rename operations as R100 entries and modifies the two merge targets plus the three durable path-reference tests.
- Git evidence: commit 0e81a895 deletes tests/test_decisions_1218.py, tests/test_cockpit_read_api_1223.py, and tests/test_pipeline_diagram_1299.py.
- Dirty-tree check on all 29 changed files: clean.
- Untouched-file guard: tests/test_kanban_topology_1439.py appears in neither builder commit diff.
- Test preservation: TestFromAC_SessionsEnvelope1223 is present in tests/test_cockpit_read_api.py with all 9 source tests preserved. True fixture collisions board_dir, engine, and client were resolved with _1223 suffixed source fixtures. No weakening observed.
- Test preservation: TestFromAC_OrchestratorSupervisoryRole1299 is present in tests/test_pipeline_diagram.py with both source tests preserved. No weakening observed.
- Builder process quality: one builder cycle, two task-scoped commits, no loop pattern.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All 21 renames completed via git mv | commit d23dd134 shows 21 R100 rename entries | PASS |
| test_decisions_1218.py deleted | commit 0e81a895 deletes the file; file absent from HEAD | PASS |
| Unique tests from cockpit_read_api_1223 merged into durable target; source deleted | 9 source tests preserved in tests/test_cockpit_read_api.py; source deleted in 0e81a895 | PASS |
| Unique tests from pipeline_diagram_1299 merged into durable target; source deleted | 2 source tests preserved in tests/test_pipeline_diagram.py; source deleted in 0e81a895 | PASS |
| Duplicate test-name collisions resolved with source-task suffix when needed | No test-name collisions found in either merge, so no renames required | PASS |
| Fixture collisions handled correctly | True same-name collisions were board_dir, engine, and client; suffixed source fixtures present in durable target | PASS |
| Collected test count meets or exceeds baseline | 3376 collected versus 3299 baseline | PASS |
| Post-cleanup failure count does not exceed baseline | 427 failed versus 427 baseline | PASS |
| test_kanban_topology_1439.py untouched | file absent from both builder commit diffs | PASS |

### Deductions
- 0.03 confidence deduction for shared-branch drift: current suite totals increased by 77 passing tests versus the builder's captured baseline, but the architect-corrected gates are baseline-relative and still satisfied.
- 0.01 confidence deduction for source-to-target preservation relying on git-history inspection plus current file verification rather than a single inline diff artifact.

### Verdict
PASS with confidence 0.96.

### Action
Advance to docs.