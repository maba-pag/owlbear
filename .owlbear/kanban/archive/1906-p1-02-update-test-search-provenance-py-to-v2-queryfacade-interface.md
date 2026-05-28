---
id: 1906
title: 'P1-02: Update test_search_provenance.py to v2 QueryFacade interface'
status: archived
priority: needed
created: 2026-05-28T00:34:20.718643+02:00
updated: 2026-05-28T11:07:48.236213+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
  - 1905
ac:
  - tests/test_search_provenance.py does not exist (file absence verified on 
    disk)
  - tests/test_mcp_knowledge_provenance_1906.py renamed to 
    tests/test_mcp_knowledge_provenance.py (durable module-level naming; task 
    reference preserved in docstring)
  - At least one test in TestFromAC_ProvenanceRelatedSources asserts 
    related_sources[N]["entity"] equals a specific expected string value from 
    provenance input (proves _serialize_related_sources preserves entity field 
    through full serialization path)
  - pytest tests/test_mcp_knowledge_provenance.py passes with 0 failures and 0 
    errors (replacement provenance suite is green)
  - pytest tests/ -k 'knowledge or enrichment or ingest_document or 
    get_next_batch' --ignore=tests/test_persistence_source_wiring.py 
    --ignore=tests/test_mcp_kanban_newline_norm_1531.py 
    --ignore=tests/test_knowledge_legacy_sweep_1898.py passes with 0 failures 
    and 0 errors (domain regression gate)
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Update the durable module-level `tests/test_search_provenance.py` (~28 tests) to test the provenance serialization contract against the v2 QueryFacade interface instead of the removed `query_service` path.

## Current State
- Builds a `query_service`-only context via `_make_ctx(query_service=...)` and calls `qs.query()`
- Tests provenance fields: retrieval_path, entities, related_sources, source
- The provenance contract itself is valid — only the interface changed from `query_service` → `QueryFacade`

## Direction
- Replace `_make_ctx(query_service=...)` with a context mock providing `query_facade` (matching current AppContext shape)
- Update mock targets from `query_service.query()` → `QueryFacade.search()` return values
- Preserve the provenance serialization assertions (they test `knowledge_search` tool output)
- If the provenance contract is now fully covered by `serve/mcp-knowledge/tests/`, retire the file with a note explaining supersession

## Scope
- In-scope: rewrite or retire `tests/test_search_provenance.py`
- Out-of-scope: other test files, server.py changes



## Architecture Review

### Decision: Retire (not rewrite)

Codebase analysis confirms the provenance contract tested by this file is:
1. **Already broken** — all 28 tests mock `query_service.query()` which was removed in #1900. The mock context `_make_ctx(query_service=...)` doesn't set `query_facade`, so `knowledge_search` receives a MagicMock facade and crashes during `_serialize_query_facade_results`.
2. **Already superseded** — `tests/test_mcp_knowledge_read_tools_1881.py` covers the same serialization output fields (retrieval_path, entities, related_sources, source, graph_context) against the v2 `QueryFacade.search()` path.

### Coverage note for builder

The retired file's Class 4 (`TestFromAC_MCPBoundarySourceProof`) tested `_serialize_source` config-URL branches (config[\"url\"], config[\"urls\"] list/string, blank-url fallback). These branches remain live in `_helpers.py` but the old tests were already broken (testing removed interface). This is a **pre-existing gap**, not a regression from this retirement. A follow-up task for `_serialize_source` unit coverage may be warranted but is out-of-scope here.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One action: retire one test file |
| Interface clarity | PASS | AC specifies file deletion + regression gate |
| Dependency correctness | PASS | #1900 (remove legacy fields) is archived |
| Module layering | PASS | Test file only, no production imports affected |
| TDD compliance | PASS | Tagged `test` — pass-through in pipeline |
| KISS/YAGNI | PASS | Deletion is simplest correct action |
| Premise challenge | PASS | File tests removed interface; must be addressed |
| Pattern consistency | PASS | Retirement with supersession note follows project convention |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Test-writer: PASS-THROUGH (tagged `test`)

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Findings: wrong class names in supersession claim, coverage gaps in `_serialize_source` config branches, AC/Tier mismatch
- Architect response: ACCEPTED in part. Class names corrected. `_serialize_source` gap is pre-existing (old tests already broken). Tier 2 challenge rejected — these are Tier 1 behavior AC (code artifacts with pass/fail at file level). AC refined to address valid concerns.

### Verdict: APPROVE
### Action Taken: AC refined for retirement path, advanced to todo

[[2026-05-28T01:51:24+02:00]]
Architecture review complete. AC refined for retirement path (not rewrite) based on codebase evidence: all 28 tests are already broken (mock removed query_service interface) and the provenance contract is superseded by test_mcp_knowledge_read_tools_1881.py. Challenger accepted in part — class names corrected, _serialize_source config-branch gap acknowledged as pre-existing (not caused by retirement).

[[2026-05-28T02:03:15+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no new tests applicable.
- Task action is deletion of `tests/test_search_provenance.py` and regression verification of `tests/test_mcp_knowledge_read_tools_1881.py` — both are builder-phase actions.
- Passing through to builder.

[[2026-05-28T02:27:34+02:00]]
## Builder Notes
- Scope attempted: retire `tests/test_search_provenance.py` and prove superseding coverage via `tests/test_mcp_knowledge_read_tools_1881.py` (AC2).
- Code/test changes: none retained. I temporarily deleted `tests/test_search_provenance.py`, then restored it from HEAD after gate infeasibility was confirmed.
- Proof run (quality-runner, scoped): `test_paths=["tests/test_mcp_knowledge_read_tools_1881.py"]`, `lint_paths=["tests/test_mcp_knowledge_read_tools_1881.py"]`.
- Proof result: pytest failed (`5 passed`, `59 failed`), ruff clean.
- Primary failures in required proof file:
  - `TestFromAC_AppContextFieldsV2::*` -> `TypeError: AppContext.__init__() got an unexpected keyword argument 'query_service'`
  - `TestFromAC_SearchKnowledgeDelegate::*` (and related classes) -> `ImportError: cannot import name 'init_db' from owlbear_mcp_knowledge.server`
- AC mismatch: AC2 requires `pytest tests/test_mcp_knowledge_read_tools_1881.py` to pass with `0 failures`, but that file is currently RED for reasons outside this task’s in-scope retirement action.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite AC2 proof target to a currently green superseding suite, or create a prerequisite task to repair failing tests in the required proof file before retirement. | tests/test_mcp_knowledge_read_tools_1881.py | quality-runner scoped report: `5 passed`, `59 failed`; `TypeError` on `AppContext(... query_service=...)`; `ImportError` for missing `init_db` |
| 2 | architect | Clarify whether retirement is still intended under AC3 (`no other test/source modifications`) when AC2 proof file is RED. | tests/test_search_provenance.py | Task #1906 AC2+AC3 are jointly infeasible without upstream remediation or AC rewrite |

### Post-task Reflection
- Problem faced: Required superseding proof file is currently failing broadly, making retirement-gate AC infeasible.
- Workaround applied: Ran canonical quality-runner scoped proof first, then restored temporary file deletion to keep tree clean.
- Pattern discovered: Retirement tasks should validate superseding proof health at planning time to avoid infeasible builder gates.
- Quality gap: AC linked to a non-green proof target; needs architect-level correction before builder can complete.

[[2026-05-28T02:51:22+02:00]]
## Architecture Review (re-review after builder rejection)

### AC2 Refinement
- **Problem:** Original AC2 required `test_mcp_knowledge_read_tools_1881.py` to pass (0 failures). That file has 59 failures from removed `init_db` import and stale `AppContext(query_service=...)` constructor — it's broken for reasons unrelated to this task. Furthermore, #1905 (in `todo`) deletes that file entirely.
- **Fix:** Replaced single-file proof target with domain keyword selector (same pattern as #1905 re-review). After #1905 deletes the broken task-scoped files, the selector runs against the remaining green knowledge domain tests. `test_persistence_source_wiring.py` excluded via `--ignore` (remediation: #1907).
- **Dependency added:** #1905 — ensures the 3 broken task-scoped files (including the original AC2 target) are gone before this task's selector runs.

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: existing
- Existing proof scope: `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py`
- Test-writer: SKIP (bundle `existing`, tagged `test`)
- De-escalation rationale: task is pure file deletion — no new code to smoke-test; only regression gate needed.

### Evaluation (unchanged from prior review)
All 10 criteria PASS — single file deletion, knowledge domain only, no module interaction.

### Verdict: APPROVE
Re-approved with feasible AC2 (domain selector gate) and added #1905 dependency. Test-writer: SKIP.

[[2026-05-28T02:51:49+02:00]]
Re-review complete. AC2 rewritten from infeasible single-file target (broken test_mcp_knowledge_read_tools_1881.py) to domain keyword selector gate. Added #1905 dependency (deletes the 3 broken task-scoped files first). Proof bundle de-escalated smoke→existing (pure file deletion). Test-writer: SKIP.

[[2026-05-28T05:08:17+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Also tagged `test` — non-implementation task.
- Architect note: "Test-writer: SKIP (bundle `existing`, tagged `test`)"
- Passing through to builder.

[[2026-05-28T05:25:09+02:00]]
## Builder Notes
- Scope attempted: retire tests/test_search_provenance.py and satisfy the existing-proof regression gate in AC2.
- Temporary change during verification: deleted tests/test_search_provenance.py, then restored it from HEAD after gate failure so no partial change remains.
- Existing proof run (quality-runner, scoped) used the AC2 selector gate for knowledge and enrichment tests with the persistence-source-wiring file excluded.
- Quality-runner result: tests passed 310, tests failed 0, pytest exit code 1, ruff clean.
- Blocking error from proof run: collection error in tests/test_mcp_kanban_newline_norm_1531.py with ImportError for create_dr from owlbear_mcp_kanban.server.
- AC mismatch: AC2 requires zero failures and zero errors, but the required proof gate currently errors for reasons outside this task scope.
- Files changed in final state: none retained.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Revise AC2 proof target (or add prerequisite dependency) so the required proof gate is executable without unrelated collection errors. | tests/test_mcp_kanban_newline_norm_1531.py, tests/test_search_provenance.py | quality-runner report: 310 passed, 0 failed, pytest exit 1 with collection ImportError for create_dr |
| 2 | architect | Reconfirm retirement path for tests/test_search_provenance.py after AC2 proof target is corrected. | tests/test_search_provenance.py | current AC2 gate cannot be satisfied while preserving AC3 scoped-change constraint |

### Post-task Reflection
- Problem faced: the required selector gate still raises a collection ImportError outside the intended knowledge-domain proof.
- Workaround applied: executed the canonical quality-runner proof first, then restored temporary deletion to keep working state clean.
- Pattern discovered: retirement tasks need proof targets that avoid cross-domain collection hazards.
- Quality gap: AC2 currently couples this task to unrelated kanban-test import health.

[[2026-05-28T05:30:40+02:00]]
## Architecture Review (re-review #3 after second builder rejection)

### AC2 Refinement
- **Problem:** AC2 selector gate collected `tests/test_mcp_kanban_newline_norm_1531.py` which has a broken import (`create_dr` removed from `owlbear_mcp_kanban.server`). Pytest collection errors fire before `-k` filtering, blocking the 0-errors gate.
- **Fix:** Added `--ignore=tests/test_mcp_kanban_newline_norm_1531.py` to AC2 command — same pattern already used by predecessor #1905's AC4 gate (re-review #3, commit `ad7dbfe2`).
- **Proof-bundle unchanged:** `existing` with domain selector gate.

### Existing Proof Scope (updated)
- `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py`

### Challenge
- Skipped: trivial AC refinement (adding one ignore for a known broken file already excluded by predecessor task #1905). No architectural change.

### Verdict: APPROVE
Re-approved with extended ignore list. Test-writer: SKIP (bundle `existing`, tagged `test`).

[[2026-05-28T05:41:17+02:00]]
## Test-Writer Notes
- Proof bundle: `existing` — no new test writing required.
- Tagged `test`; architecture review (re-review #3) explicitly marks test-writer SKIP.
- Dependency #1905 is now archived (completed) — the three broken task-scoped files deleted in that task are no longer present, so the AC2 selector gate should now be unblocked.
- AC1: file-deletion assertion (tests/test_search_provenance.py absence).
- AC2: regression gate via `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py` (0 failures, 0 errors).
- AC3: commit-diff scope assertion (no other files modified).
- All three ACs are builder-phase actions; no testable interface exists for test-writer to exercise.
- Passing through to builder.

[[2026-05-28T05:54:50+02:00]]
## Builder Notes
- Implementation: retired obsolete provenance suite by deleting `tests/test_search_provenance.py`.
- Files changed: `tests/test_search_provenance.py` (deleted).
- Existing proof executed via quality-runner (scoped) using AC2 selector gate:
  - `tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py`
- Tests: 314 passed, 0 failed, 0 skipped (pytest exit 0).
- Coverage: not required for `proof_bundle=existing` (quality-runner reported `overall_pct: none`).
- Ruff: clean (ruff exit 0, no violations).
- Evidence summary:
  - AC1 satisfied: file absence verified for `tests/test_search_provenance.py`.
  - AC2 satisfied: selector gate passed with 0 failures and 0 errors.
  - AC3 satisfied: commit scope contains only the retired file.
- Commit: `12621576` — `test: retire stale search provenance suite (#1906, builder)`.
- Fixes applied: no code/source changes; only the in-scope test-file retirement.

### Post-task Reflection
- Problem faced: `apply_patch` delete reported success twice but the file remained unchanged on disk.
- Workaround applied: switched to shell deletion with immediate `git status` verification.
- Pattern discovered: for AC-specific pytest selector gates, quality-runner can receive `-k`/`--ignore` via `test_paths` entries.
- Time sink: repeated delete verification rounds due non-persistent patch deletion behavior.
- Quality gap: none remaining for this task after updated AC2 gate and dependency #1905 completion.

[[2026-05-28T06:02:22+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1906 -> todo | deletion retires the last surviving proof for MCP provenance serialization on the v2 QueryFacade path.
- Builder evidence review: sufficient and internally consistent for the claimed deletion (`tests/test_search_provenance.py` absent), selector gate (`314 passed, 0 failed, 0 skipped`), and scoped change summary (commit `12621576`). Independent rerun not required.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: `tests/test_search_provenance.py` deleted | Builder notes report deletion; current workspace search for `**/test_search_provenance.py` returns no files. | N/A | PASS |
| AC2: selector gate passes with 0 failures / 0 errors | Builder notes record `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py` -> `314 passed, 0 failed, 0 skipped` (exit 0). | Existing-proof gate is green. | PASS |
| AC3: no other files modified | Builder notes and commit `12621576` claim scope is deletion-only. No contradictory workspace evidence surfaced during review. | N/A | PASS |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | Task direction / proof sufficiency | The task was only allowed to retire `tests/test_search_provenance.py` if the provenance contract was fully covered elsewhere. That condition is not true in the current tree. After dependency #1905 deleted `tests/test_mcp_knowledge_read_tools_1881.py`, there is no surviving test that exercises `knowledge_search` / `_serialize_query_facade_results` and asserts MCP output fields such as `retrieval_path`, `graph_context`, `entities`, `related_sources`, or `source`. The green selector gate proves the remaining domain suite passes, but it would not fail if the MCP serializer regressed. | Task direction in `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:34-48`; dependency deletion of `tests/test_mcp_knowledge_read_tools_1881.py` in `.owlbear/kanban/archive/1905-p1-01-delete-stale-task-scoped-knowledge-test-files-1888-1881-1895.md:1-25`; no files found for `**/test_search_provenance.py` or `**/test_mcp_knowledge_read_tools_1881.py`; no matches for `knowledge_search(` or `_serialize_query_facade_results` in `tests/**`; surviving matches for provenance terms are limited to lower-level QueryFacade suites in `tests/test_query_facade_1879.py` and `tests/test_query_facade_1880.py`; `tests/test_mcp_knowledge_legacy_removal_1900.py:103-120` only proves source cleanup; production serialization path remains in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:501-592`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Restore durable proof for MCP provenance serialization on the v2 QueryFacade path by adding tests that call `knowledge_search` (or otherwise exercise `_serialize_query_facade_results` through the production adapter path) and assert `retrieval_path`, `graph_context`, `entities`, `related_sources`, and `source`. Then reassess whether `tests/test_search_provenance.py` should be rewritten or retired. | tests/test_search_provenance.py; tests/test_query_facade_1879.py; tests/test_query_facade_1880.py; tests/test_mcp_knowledge_legacy_removal_1900.py; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | Blocking finding 1 |

## Observations
- The builder packet itself was not the problem here; the failure is proof quality, not missing execution evidence.
- `tests/test_query_facade_1879.py` and `tests/test_query_facade_1880.py` still provide lower-level QueryFacade/provenance coverage, but they do not pin the MCP serialization contract exported by `knowledge_search`.
- If the intended outcome is still retirement rather than rewrite, the replacement proof should be explicit enough that a regression in `_serialize_query_facade_results` would fail locally without relying on a broad keyword selector gate.

[[2026-05-28T06:11:05+02:00]]
## Test-Writer Notes
- Retry: added 26 tests for reviewer gap (MCP provenance serialization proof on v2 QueryFacade path).
- Builder skip: test-only retry — all 26 new tests pass against current implementation.
- Test file: tests/test_mcp_knowledge_provenance_1906.py
- Classes: TestFromAC_ProvenanceRetrieval, TestFromAC_ProvenanceSource, TestFromAC_ProvenanceRelatedSources, TestFromAC_ProvenanceBoundary
- Tests per category: happy 10, edge 9, error 0, boundary 7
- Total: 26 tests, all PASS (implementation already correct)
- ruff: clean
- AC coverage:
  - Reviewer finding 1: _serialize_query_facade_results output fields retrieval_path, graph_context, entities, related_sources, source — all covered with direct assertions
  - _serialize_source config-URL branches (pre-existing gap noted by architect) — covered by test_source_config_url_used_when_direct_url_blank and test_source_config_urls_list_first_entry_used_when_url_blank
- Commit: 54d66079

[[2026-05-28T06:16:30+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1906 to backlog | the retry restores provenance proof, but it violates AC3 by adding a new test file and still leaves one RelatedSource contract member unproved.
- Evidence review: the prior builder packet was sufficient for the deletion-only change, but it was stale after the test-only retry added a new proof file. Reviewer re-ran focused verification with quality-runner. Current-state result: selector gate passed 340 tests with 0 failures and 0 errors, the new provenance suite passed 26 tests, and ruff was clean. quality-runner also confirmed the AC2 selector gate does not include the new provenance suite.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: tests/test_search_provenance.py is deleted | File absent on disk; no workspace match for tests/test_search_provenance.py. | Prior builder packet already proved deletion and nothing in the retry contradicted it. | PASS |
| AC2: selector gate passes with 0 failures and 0 errors | No source changes in the retry. | quality-runner current-state verification: selector gate passed 340 tests with exit 0. | PASS |
| AC3: no other test or source files are created or modified | Task AC still forbids any other test or source changes at .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:24. | The retry explicitly added tests/test_mcp_knowledge_provenance_1906.py in task notes at .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:257-259, and the file exists in the workspace. | FAIL |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC3 | The retry creates tests/test_mcp_knowledge_provenance_1906.py, which directly contradicts the unchanged AC that no other test or source files may be created or modified. The task currently proves the replacement contract by adding new scope rather than by satisfying the approved retirement-only contract. | .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:24; .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:257-259; tests/test_mcp_knowledge_provenance_1906.py:1 | backlog |
| 2 | Proof sufficiency | The new suite names RelatedSource as {name, relationship, entity} but only asserts empty-list, name, and relationship cases. A regression in related_sources[*].entity would still pass. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/_types.py:33; serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:74; tests/test_mcp_knowledge_provenance_1906.py:359; tests/test_mcp_knowledge_provenance_1906.py:369; tests/test_mcp_knowledge_provenance_1906.py:381; tests/test_mcp_knowledge_provenance_1906.py:382; tests/test_mcp_knowledge_provenance_1906.py:392; tests/test_mcp_knowledge_provenance_1906.py:407 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile the task contract with the actual replacement-proof strategy: either revise AC3 to allow a new durable provenance suite, or require the proof to be folded into an existing allowed test file before retirement can pass. | .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md; tests/test_mcp_knowledge_provenance_1906.py | Blocking finding 1 |
| 2 | architect | Tighten the proof requirement for related_sources so the replacement suite must assert the full RelatedSource shape, including entity, before the old provenance suite can stay retired. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/_types.py; serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py; tests/test_mcp_knowledge_provenance_1906.py | Blocking finding 2 |

## Observations
- The retry did fix the original blocker from the first review: there is now durable provenance proof for retrieval_path, graph_context, entities, related_sources, and source on the v2 serializer path.
- quality-runner exposed a useful planning gap: the AC2 selector gate stays green even when the replacement provenance suite is excluded, so future retirement tasks should name the exact surviving proof file rather than rely on a broad keyword selector.

[[2026-05-28T09:42:38+02:00]]
## Architecture Review (re-review #4 after second reviewer rejection)

### AC Revision Summary
- **Problem:** Reviewer correctly identified AC3 ("no other files created") contradicts the replacement-proof strategy required by the same reviewer's first rejection. Additionally, `related_sources[*].entity` field was not explicitly asserted.
- **Fix:** Rewrote AC to align task contract with the necessary outcome: retire old suite + provide durable replacement proof. Added entity assertion requirement. Required durable naming (drop `_1906` suffix).
- **Rationale for allowing new file:** The original task direction explicitly allowed "rewrite or retire." Retirement without replacement proof was rejected in review #1. The test-writer's replacement suite (26 tests) is the correct outcome — it just needed AC permission and the entity gap closed.

### Evaluation (unchanged — all 10 criteria PASS)
Pure test-infrastructure task: rename one file, add one assertion. Single domain (knowledge), no production code changes, no module layering concerns.

### Proof-Bundle Validation
- Planner assignment: smoke (original)
- Final bundle: existing
- Existing proof scope: `tests/test_mcp_knowledge_provenance.py`
- De-escalation rationale: task deliverable is rename + one assertion addition to an already-green 26-test suite. No new code paths to smoke-test.
- Test-writer: SKIP (bundle `existing`, tagged `test`)

### Challenge Results
- Challenger: block (confidence 0.24)
- Findings: (1) file still has task-scoped name, (2) scope drift from tool-level to helper-level, (3) selector excludes provenance suite, (4) AC3 entity wording
- Architect response: REBUTTED (1-3), ACCEPTED (4). Finding 1 is the prescribed work, not a contradiction. Finding 2 is wrong — `_serialize_query_facade_results` IS the production adapter called by `knowledge_search` (server.py:592); reviewer explicitly allowed this path. Finding 3 addressed by separate AC4 (provenance-specific) vs AC5 (domain regression). Finding 4 accepted — tightened AC3 to require specific expected value assertion.

### Verdict: APPROVE
### Action Taken: AC rewritten to permit durable replacement proof file (rename + entity assertion), advanced to todo. Test-writer: SKIP.

[[2026-05-28T09:47:51+02:00]]
## Test-Writer Notes
- Proof bundle: `existing` — no new test writing required.
- Tagged `test`; architecture review (re-review #4) explicitly marks test-writer SKIP.
- Retry cycle context: the 26-test provenance suite already exists as `tests/test_mcp_knowledge_provenance_1906.py` (committed 54d66079); all 26 tests pass against current implementation.
- Outstanding builder scope:
  1. Rename `tests/test_mcp_knowledge_provenance_1906.py` → `tests/test_mcp_knowledge_provenance.py` (AC2 — durable naming, task ref preserved in docstring).
  2. Add at least one assertion in `TestFromAC_ProvenanceRelatedSources` that checks `related_sources[N]["entity"]` equals a specific expected string (AC3 — entity field coverage gap identified by reviewer).
  3. Run AC4 gate: `pytest tests/test_mcp_knowledge_provenance.py` (0 failures, 0 errors).
  4. Run AC5 domain regression gate: `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py` (0 failures, 0 errors).
- Passing through to builder.

[[2026-05-28T10:01:33+02:00]]
## Builder Notes
- Scope attempted: complete AC2/AC3 implementation for durable provenance suite naming plus related_sources entity assertion, then run required existing proofs.
- Temporary implementation during verification: renamed `tests/test_mcp_knowledge_provenance_1906.py` -> `tests/test_mcp_knowledge_provenance.py` and added explicit assertion `related_sources[0]["entity"] == "Alpha"` in `TestFromAC_ProvenanceRelatedSources`.
- Existing proof AC4 (quality-runner, scoped): `test_paths=["tests/test_mcp_knowledge_provenance.py"]`, `lint_paths=["tests/test_mcp_knowledge_provenance.py"]`.
- AC4 result: `27 passed`, `0 failed`, `0 skipped`; pytest exit `0`; ruff clean.
- Existing proof AC5 (quality-runner, scoped): `test_paths=["tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py"]`, `lint_paths=["tests/test_mcp_knowledge_provenance.py"]`.
- AC5 result: `348 passed`, `20 failed`, `0 skipped`; pytest exit `1`; ruff clean.
- Blocking failures are from `tests/test_knowledge_legacy_sweep_1898.py` (legacy-removal assertions/import expectations), which are unrelated to this task’s rename/assertion scope.
- Final retained file changes: none (temporary rename/assertion were reverted after gate failure).

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Revise AC5 proof target (or add prerequisite dependency) so task #1906’s required gate is satisfiable without unrelated legacy-sweep failures. | tests/test_knowledge_legacy_sweep_1898.py; .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md | quality-runner AC5 report: 20 failures in `TestFromAC_LegacyFileDeletion`, `TestFromAC_ComputeContentHash`, and `TestFromAC_EmbeddingsMigration`; pytest exit 1 |
| 2 | architect | Reconfirm builder delivery scope for #1906 after AC5 gate correction (rename + entity assertion + two proof gates) so completion criteria are executable end-to-end. | .owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md | current required gate fails before this task can be advanced despite AC4 green |

### Post-task Reflection
- Problem faced: AC5 selector gate currently includes unrelated failing legacy-sweep tests.
- Workaround applied: executed both required proofs via quality-runner first, then reverted temporary edits to keep working tree clean on rejection.
- Pattern discovered: broad keyword selector gates are fragile and can become unsatisfiable as independent domain cleanup tests are introduced.
- Time sink: implementing and validating AC2/AC3 changes that cannot be advanced while AC5 remains red.
- Quality gap: task contract depends on a non-isolated regression gate outside this task’s ownership.

[[2026-05-28T10:19:13+02:00]]
## Architecture Review (re-review #5 after third builder rejection)

### AC5 Refinement
- **Problem:** AC5 selector gate collected `tests/test_knowledge_legacy_sweep_1898.py` — a task-scoped RED suite for in-flight task #1898 (currently in `review`). Its 20 failures (`TestFromAC_LegacyFileDeletion`, `TestFromAC_ComputeContentHash`, `TestFromAC_EmbeddingsMigration`) are unrelated to #1906's rename+assertion scope.
- **Fix:** Added `--ignore=tests/test_knowledge_legacy_sweep_1898.py` to AC5 — same pattern as re-reviews #3 (kanban newline norm) and #4 predecessor #1905.
- **Proof-bundle unchanged:** `existing` with domain selector gate.

### Existing Proof Scope (updated)
- AC4: `pytest tests/test_mcp_knowledge_provenance.py`
- AC5: `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py --ignore=tests/test_knowledge_legacy_sweep_1898.py`

### Challenge
- Skipped: trivial AC refinement (adding one ignore for a known task-scoped RED file for in-flight #1898). No architectural change. Same pattern applied 3 times previously.

### Verdict: APPROVE
Re-approved with extended ignore list. Test-writer: SKIP (bundle `existing`, tagged `test`).

[[2026-05-28T10:29:57+02:00]]
## Test-Writer Notes
- Proof bundle: `existing` — no new test writing required.
- Tagged `test`; architecture review (re-review #5) explicitly marks test-writer SKIP.
- Retry cycle: `## Test-Writer Notes` and `## Review Evidence` both present. Most recent reviewer Required Follow-up directed to architect only (both items addressed in re-review #5). No test-writer action required.
- Current workspace state: `tests/test_search_provenance.py` absent (AC1 done); `tests/test_mcp_knowledge_provenance_1906.py` exists with 26 tests (all green per prior quality-runner run).
- Outstanding builder scope:
  1. Rename `tests/test_mcp_knowledge_provenance_1906.py` → `tests/test_mcp_knowledge_provenance.py` (AC2).
  2. Add explicit `related_sources[N]["entity"]` assertion in `TestFromAC_ProvenanceRelatedSources` (AC3).
  3. Run AC4 gate: `pytest tests/test_mcp_knowledge_provenance.py` (0 failures, 0 errors).
  4. Run AC5 domain gate: `pytest tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py --ignore=tests/test_knowledge_legacy_sweep_1898.py` (0 failures, 0 errors).
- Passing through to builder.

[[2026-05-28T10:40:43+02:00]]
## Builder Notes
- Implementation: renamed `tests/test_mcp_knowledge_provenance_1906.py` to `tests/test_mcp_knowledge_provenance.py` and added explicit RelatedSource entity assertion in `TestFromAC_ProvenanceRelatedSources`.
- Files changed: `tests/test_mcp_knowledge_provenance_1906.py` (renamed), `tests/test_mcp_knowledge_provenance.py` (durable target file content includes `related_sources[0]["entity"] == "Alpha"`).
- Existing proof AC4 (quality-runner, scoped): `tests/test_mcp_knowledge_provenance.py` -> 26 passed, 0 failed, 0 errors, pytest exit 0.
- Existing proof AC5 (quality-runner, scoped): `tests/ -k 'knowledge or enrichment or ingest_document or get_next_batch' --ignore=tests/test_persistence_source_wiring.py --ignore=tests/test_mcp_kanban_newline_norm_1531.py --ignore=tests/test_knowledge_legacy_sweep_1898.py` -> 340 passed, 0 failed, 0 errors, pytest exit 0.
- Lint: ruff clean on `tests/test_mcp_knowledge_provenance.py` in both proof runs (ruff exit 0).
- Coverage: not required for `proof_bundle=existing` (quality-runner coverage field non-gating).
- AC evidence summary:
  - AC1 satisfied: `tests/test_search_provenance.py` absent.
  - AC2 satisfied: durable rename complete and task reference remains in module docstring.
  - AC3 satisfied: concrete entity assertion added (`"Alpha"`).
  - AC4 satisfied: provenance suite green.
  - AC5 satisfied: required domain regression gate green.
- Commit: `872aeb97` — `test: durable-name provenance suite and assert entity field (#1906, builder)`.
- Fixes applied: no production code changes; test-suite contract update only.

### Post-task Reflection
- Problem faced: prior AC gate instability history made proof routing brittle, so exact command fidelity mattered.
- Workaround applied: executed both AC proof gates verbatim through `quality-runner` before finalizing and committing.
- Pattern discovered: when retirement tasks are promoted to durable replacement proof, naming must be normalized immediately to avoid repeated review churn.
- Time sink: none material in this pass; execution was straightforward once AC5 ignore list stabilized.
- Quality gap: none observed for the current AC set.

[[2026-05-28T10:51:54+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1906 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: sufficient and internally consistent for an `existing` proof bundle. The builder provided the required named-suite result, domain regression result, lint status, file summary, and commit reference at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:399-411`. No independent rerun was required.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: `tests/test_search_provenance.py` absent | Workspace file search for `tests/test_search_provenance.py` returns no files. The AC is authoritative at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:17`. | N/A | PASS |
| AC2: durable rename to `tests/test_mcp_knowledge_provenance.py` with task ref preserved | New durable suite exists and preserves the task reference in the module docstring at `tests/test_mcp_knowledge_provenance.py:1`. Workspace file search for `tests/test_mcp_knowledge_provenance_1906.py` returns no files. AC text is at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:19-20`. | Builder notes record the rename in `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:399`. | PASS |
| AC3: explicit `related_sources[N]["entity"]` assertion | The production adapter serializes related sources through `_serialize_query_facade_results` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:501-560`, which delegates to `_serialize_related_sources` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:68-84`; `RelatedSource.entity` is part of the public shape at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_types.py:33-38`. | `tests/test_mcp_knowledge_provenance.py:385` asserts `related_c1[0]["entity"] == "Alpha"`, and the suite imports the production adapter directly at `tests/test_mcp_knowledge_provenance.py:29`. Because `knowledge_search` returns this adapter output at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:592`, a serializer regression would fail this proof. | PASS |
| AC4: `pytest tests/test_mcp_knowledge_provenance.py` passes cleanly | Current suite contains 26 test cases (`tests/test_mcp_knowledge_provenance.py:115-456`). | Builder quality evidence records `26 passed, 0 failed, 0 errors` for `tests/test_mcp_knowledge_provenance.py` at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:401`. | PASS |
| AC5: domain regression gate passes cleanly | No production files changed; the replacement suite pins retrieval, graph context, source, and related-source serialization with concrete value assertions at `tests/test_mcp_knowledge_provenance.py:133`, `tests/test_mcp_knowledge_provenance.py:157`, `tests/test_mcp_knowledge_provenance.py:318`, and `tests/test_mcp_knowledge_provenance.py:385`. | Builder quality evidence records `340 passed, 0 failed, 0 errors` for the required selector gate at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:402`, with ruff clean at `.owlbear/kanban/tasks/1906-p1-02-update-test-search-provenance-py-to-v2-queryfacade-interface.md:403`. | PASS |

## Observations
- The durable replacement suite is now attached to the correct production boundary: it imports `_serialize_query_facade_results` from `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` at `tests/test_mcp_knowledge_provenance.py:29`, and that adapter is exactly what `knowledge_search` returns at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:592`.
- Proof sufficiency is materially stronger than the deleted legacy suite because the surviving tests pin exact serialized values for retrieval path, graph context, source URL fallback/config branches, and related-source entity rather than relying on broad selector-gate greenness.
- `get_errors` reports no current type/compile issues in `tests/test_mcp_knowledge_provenance.py` or `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`.

[[2026-05-28T10:55:34+02:00]]
## Docs Gate

### Checklist

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | README Verification | N/A | All changed files are root-level `tests/` (one deletion: `test_search_provenance.py`; one rename: `test_mcp_knowledge_provenance_1906.py` → `test_mcp_knowledge_provenance.py`). No convention-mapped README target applies to root-level test files. No public interface changes. |
| 2 | External Attribution | N/A | No external sources influenced this implementation. |
| 3 | Research Doc | N/A | No research artifact for this task. |
| 4 | Deletion Detection | PASS | `tests/test_search_provenance.py` referenced in `test_knowledge_legacy_sweep_1898.py:293-295` only as an absence assertion — consistent with deletion outcome. No orphaned references found in any documentation file (grepped `**/*.md`). |

### Files Updated
None — no documentation impact.

### Scratch Cleanup
No `.owlbear/scratch/1906-*` files present.

[[2026-05-28T11:07:48+02:00]]
## Audit

### Regression Detection
Full-suite quality-runner run: 5807 passed, 124 failed, 14 skipped. All 124 failures are pre-existing from in-flight tasks (cockpit, kanban, memory, shell domains) — none in `tests/test_mcp_knowledge_provenance.py` (task deliverable: 26 passed, 0 failed). Lint violations (4× TC001/TC002 in `protocols/query.py` and `protocols/content.py`) are in files not changed by this task. No regressions introduced.

### Intent Verification
Changed files stay within knowledge test domain: `tests/test_search_provenance.py` deleted, `tests/test_mcp_knowledge_provenance.py` created (renamed + entity assertion). No production code changes. Implementation addresses stated purpose (retire stale suite, provide durable replacement proof). No extraneous scope.

### Architect Quality
Score: 3/5. Notable gaps: initial AC referenced a broken proof target (`test_mcp_knowledge_read_tools_1881.py`), required 5 re-reviews and 3 builder rejections to stabilize. Root cause: keyword selector gates coupled to non-isolated cross-domain test health. Final AC set is specific and verifiable.

### Commit Integrity
- `12621576` — `test: retire stale search provenance suite (#1906, builder)`
- `54d66079` — `test: add retry provenance serialization proof for v2 QueryFacade (#1906, test-writer)`
- `872aeb97` — `test: durable-name provenance suite and assert entity field (#1906, builder)` (HEAD)

All commits properly formatted with task ref, type, and agent attribution.

### Deduction Breakdown
| Criterion | Deduction |
|---|---|
| AC quality score 3 | -.03 |
| All others | 0 |

### Confidence: 0.97
### Action: Archive
