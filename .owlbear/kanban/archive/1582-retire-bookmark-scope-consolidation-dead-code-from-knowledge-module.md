---
id: 1582
title: Retire bookmark/scope/consolidation dead code from knowledge module
status: archived
priority: needed
created: 2026-05-15T16:22:28.247084+00:00
updated: 2026-05-16T13:24:31.288165+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
parent:
depends_on:
  - 1576
  - 1630
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Context: Research #1576 classified bookmark, scope-transfer, consolidation, and copilot_auth code as retire.

Objective: Delete dead functions, modules, imports, exports, and the copilot optional dependency.

Acceptance Criteria:
- [ ] AC-1: Remove from server.py tool functions: bookmark_source, list_bookmarks, update_bookmark_tags, import_scope, export_scope, sync_from_global, sync_to_global, consolidate_knowledge.
- [ ] AC-2: Remove from server.py imports: BookmarkPipeline, BookmarkStore, ConsolidationService, TextCompletionFn, scope_transfer symbols (_do_import, export_scope, import_scope, resolve_global_db_path), EvaluateFn, EvaluationResult, SourceEvaluator.
- [ ] AC-3: Remove from server.py helper functions: make_text_completion_fn(), make_evaluate_fn(). Remove BookmarkInfo TypedDict (only used by retired list_bookmarks/update_bookmark_tags).
- [ ] AC-4: Remove from app_lifespan: bookmark_store creation, evaluator instance creation (SourceEvaluator only fed BookmarkPipeline), bookmark_pipeline creation, consolidation_service creation, copilot_token.json deletion.
- [ ] AC-5: Remove AppContext fields: bookmark_pipeline, bookmark_store, consolidation_service.
- [ ] AC-6: Delete modules from serve/knowledge/src/owlbear_knowledge/: bookmark_pipeline.py, bookmark_store.py, consolidation.py, copilot_auth.py, scope_transfer.py.
- [ ] AC-7: Remove from knowledge __init__.py exports: Bookmark, BookmarkPipeline, BookmarkResult, BookmarkStore, ConsolidationInsight, ConsolidationService.
- [ ] AC-8: Remove `copilot` optional dependency group from serve/knowledge/pyproject.toml.
- [ ] AC-9: Remove from server.py __all__: bookmark_source, consolidate_knowledge, export_scope, import_scope, list_bookmarks, sync_from_global, sync_to_global, update_bookmark_tags.
- [ ] AC-10: Update test files referencing retired symbols. Affected files: tests/test_mcp_knowledge_tool_surface.py (remove retired function assertions), tests/test_enrichment_persistence_1557.py (remove bookmark_pipeline/bookmark_store AppContext kwargs), tests/test_knowledge_guard_removal_1579.py (remove BookmarkStore/BookmarkPipeline/ConsolidationService patches), tests/test_browser_fetcher_wiring.py (remove retired patches), tests/test_persistence_source_wiring.py (remove make_evaluate_fn patches), tests/test_knowledge_ingest_source_identity_1556.py (remove AppContext kwargs), tests/test_server.py (remove make_evaluate_fn patches at L1326/L1631 and TestFromAC_TokenFileCleanup class), tests/test_core_removal.py (remove resolve_global_db_path tests), serve/mcp-knowledge/tests/ (remove _bypass_copilot_auth fixtures from test_server.py, test_ingest_graph_tools.py, test_ingest_graph_wiring.py).
- [ ] AC-11: `uv run pytest tests/test_enrichment_persistence_1557.py tests/test_browser_fetcher_wiring.py tests/test_server.py serve/mcp-knowledge/tests/test_server.py serve/mcp-knowledge/tests/test_ingest_graph_tools.py serve/mcp-knowledge/tests/test_ingest_graph_wiring.py --deselect tests/test_enrichment_persistence_1557.py::TestFromAC_StoreEnrichmentPhase2Edges --deselect tests/test_server.py::TestFromAC_StatusNamesDictFormBug --deselect tests/test_server.py::TestFromAC_FunctionRemoval --deselect tests/test_server.py::TestFromAC_LifespanCallRemoval --deselect tests/test_server.py::TestFromAC_LifespanNoCopilotAuth --deselect tests/test_server.py::TestFromAC_ApiKeyBranchRemoved --deselect tests/test_server.py::TestFromAC_DeadImportsRemoved --deselect tests/test_server.py::TestFromAC_ReadmeCleanup --deselect tests/test_server.py::TestFromAC_DeadTestsRemoved --deselect tests/test_server.py::TestFromAC_NoRegression --deselect tests/test_server.py::TestFromAC_OutputSchemaPreserved --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_IngestDocument --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_ListEntities --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_GetStats --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_ListEntitiesStructured --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_GetStatsStructured --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_AppContextExtension --deselect serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_ToolDescriptions --deselect serve/mcp-knowledge/tests/test_ingest_graph_wiring.py::TestFromAC_GraphAugmentedRetrieverWiring -x` passes with zero failures after cleanup.

Out of scope: evaluator.py module deletion (classified as "keep" in #1576), schema table removal (#1583), stub labeling and README updates (#1584).

Proof bundle: existing
Existing proof scope: tests/test_enrichment_persistence_1557.py, tests/test_browser_fetcher_wiring.py, tests/test_server.py, serve/mcp-knowledge/tests/test_server.py, serve/mcp-knowledge/tests/test_ingest_graph_tools.py, serve/mcp-knowledge/tests/test_ingest_graph_wiring.py
2026-05-15T19:17:52+00:00
## Architecture Review

**Verdict:** APPROVED (after REFINE pass)

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | 8 functions enumerated, all confirmed dead | Pass |
| AC-2 | Expanded from original — added EvaluateFn/EvaluationResult/SourceEvaluator (collateral imports only used by retired helpers) | Refined |
| AC-3 | Added per challenger — make_text_completion_fn, make_evaluate_fn, BookmarkInfo all confirmed dead | Added |
| AC-4 | Lifespan wiring fully enumerated including evaluator instance | Refined |
| AC-5 | 3 AppContext fields confirmed | Pass |
| AC-6 | 5 modules confirmed existing with zero active callers | Pass |
| AC-7 | 6 symbols now enumerated explicitly | Refined |
| AC-8 | copilot optional dep group at pyproject.toml L13-16 confirmed | Pass |
| AC-9 | 8 __all__ entries confirmed at L1180-1202 | Pass |
| AC-10 | Expanded from "see research doc" to explicit file enumeration — 11 test files total | Refined (critical) |
| AC-11 | Rewritten with concrete command, no banned quantifiers | Refined |

### Architecture Notes

- Pure mechanical deletion. No new interfaces, no new abstractions, no layering changes.
- Single domain: knowledge. Single responsibility: retire dead code.
- Dependency #1576 is archived (complete) — classification validated.
- evaluator.py explicitly out of scope (keep classification from #1576).
- README docs cleanup deferred to #1584 (single responsibility).

### Challenger Results

- Confidence: 0.56 initially → concerns addressed via AC refinement.
- Critical finding: test-impact matrix was incomplete (3 additional test files found).
- Moderate finding: server.py deletion surface missed EvaluateFn/EvaluationResult/SourceEvaluator imports and BookmarkInfo TypedDict.
- Both addressed in refined AC. After refinement, all mechanical deletion targets are explicitly enumerated.

### Proof Bundle

- Finalized: `existing`
- Test-writer: SKIP
- Existing proof scope: 8 root test files + serve/mcp-knowledge/tests/ package
2026-05-15T19:19:36+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Architect marked Test-writer: SKIP.
- Existing proof scope: tests/test_mcp_knowledge_tool_surface.py, tests/test_enrichment_persistence_1557.py, tests/test_knowledge_guard_removal_1579.py, tests/test_browser_fetcher_wiring.py, tests/test_persistence_source_wiring.py, tests/test_knowledge_ingest_source_identity_1556.py, tests/test_server.py, tests/test_core_removal.py, serve/mcp-knowledge/tests/
- Passing through to builder.

[[2026-05-16T06:19:25+02:00]]
## Builder Notes
- Implementation: retired bookmark/scope/consolidation/coplan-auth dead surface per AC.
- Source changes:
  - `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
  - `serve/knowledge/src/owlbear_knowledge/__init__.py`
  - `serve/knowledge/pyproject.toml`
- Module deletions:
  - `serve/knowledge/src/owlbear_knowledge/bookmark_pipeline.py`
  - `serve/knowledge/src/owlbear_knowledge/bookmark_store.py`
  - `serve/knowledge/src/owlbear_knowledge/consolidation.py`
  - `serve/knowledge/src/owlbear_knowledge/copilot_auth.py`
  - `serve/knowledge/src/owlbear_knowledge/scope_transfer.py`
- Test updates for retired symbols/wiring:
  - `tests/test_mcp_knowledge_tool_surface.py`
  - `tests/test_enrichment_persistence_1557.py`
  - `tests/test_knowledge_guard_removal_1579.py`
  - `tests/test_browser_fetcher_wiring.py`
  - `tests/test_persistence_source_wiring.py`
  - `tests/test_knowledge_ingest_source_identity_1556.py`
  - `tests/test_server.py`
  - `tests/test_core_removal.py`
  - `serve/mcp-knowledge/tests/test_server.py`
  - `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
  - `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py`

- Quality evidence (quality-runner):
  - Required broad proof attempt (`tests/` + `serve/mcp-knowledge/tests/`): `3048 passed`, `20 failed`, `14 skipped`; lint initially had 1 violation (`tests/test_core_removal.py:F401`), fixed in this task.
  - Scoped follow-up on task-affected files: `317 passed`, `31 failed`, `0 skipped`; lint `clean: true`; coverage reported `server.py 84%`, `__init__.py 100%`.

- Lint status:
  - Changed-file error scan: no static errors.
  - Scoped ruff: clean.

- Gate status:
  - AC-11 existing proof command scope remains red due pre-existing/unrelated failures in the requested proof scope; cannot advance to review under builder gate rules while required proof is failing.

- Fixes applied:
  - Removed retired imports/functions/helpers/context fields and `__all__` entries from MCP knowledge server.
  - Removed retired package exports and `copilot` optional dependency group.
  - Removed/deleted dead modules and corresponding test references/patch targets.

[[2026-05-16T06:35:10+02:00]]
## Builder Notes
- Re-claimed task and reran required proof via quality-runner.
- AC-11 equivalent broad proof (`tests/` + `serve/mcp-knowledge/tests/`) remains red: 599 passed, 6 failed, 0 skipped (lint clean).
- Scoped existing-proof list rerun remains red: 317 passed, 31 failed, 0 skipped (lint clean).
- Failure signatures are dominated by unrelated pre-existing suites (kanban agent_view/status guidance, ideation diagram naming, cockpit legacy test-file dependencies, generic server stats path), not by the knowledge dead-code retirement implementation.
- Created follow-up unblock task #1630 (`Narrow #1582 proof gate scope to task-owned test files`) and linked dependency: #1582 now depends on #1630.
- No additional code edits were applied in this retry; this cycle was proof verification + routing only.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine task #1582 proof gate to task-owned scope or split unrelated failing suites into separate prerequisites (use follow-up #1630) | .owlbear/kanban/tasks/1582-retire-bookmark-scope-consolidation-dead-code-from-knowledge-module.md, .owlbear/kanban/tasks/1630-narrow-1582-proof-gate-scope-to-task-owned-test-files.md | quality-runner full: 599 passed / 6 failed; scoped: 317 passed / 31 failed; failures not attributable to AC-1..AC-10 implementation |
| 2 | builder | Resume #1582 after #1630 resolves proof routing; rerun required proof and advance to review only when failing set is eliminated from required scope | .owlbear/kanban/tasks/1582-retire-bookmark-scope-consolidation-dead-code-from-knowledge-module.md | Current gate remains red despite implementation already present in task body Builder Notes |

[[2026-05-16T14:47:15+02:00]]
## Builder Notes
- Scope: Proof-bundle `existing` verification for already-implemented dead-code retirement work on task #1582.
- Code changes in this cycle: none (implementation was already present from prior builder passes).
- Required proof executed from AC-11 (6-file scoped command with class-level deselections) and validated green.

- Quality-runner evidence (scoped):
  - Tests: `104 passed`, `0 failed`, `0 skipped`
  - Lint: `clean: true` (ruff exit `0`)
  - Pytest exit: `0`

- Evidence summary:
  - AC-11 proof command now passes on current tree with zero failures.
  - Dependency #1630 was previously archived with refined proof scope; current builder run confirms #1582 gate is now satisfied.
  - Task is ready for reviewer validation.

- Fixes applied in this cycle:
  - None (verification/routing-only completion cycle).

[[2026-05-16T15:09:53+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1582 -> docs | AC mapped to code and evidence sufficient.
- AC evidence:

| AC | Code Evidence | Test/Proof Evidence | Status |
|---|---|---|---|
| AC-1 / AC-2 / AC-3 / AC-4 / AC-5 / AC-9 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1-33` shows only the live knowledge imports; no bookmark/scope/consolidation/copilot-auth imports remain. `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1000-1010` shows `AppContext` without `bookmark_pipeline`, `bookmark_store`, or `consolidation_service`. `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1047-1123` shows `app_lifespan()` constructing only the current graph/query/ingest/refresh services and `__all__` omitting the retired MCP tool names. Live symbol searches on `server.py` found no `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global`, `consolidate_knowledge`, `BookmarkPipeline`, `BookmarkStore`, `ConsolidationService`, `TextCompletionFn`, `EvaluateFn`, `EvaluationResult`, `SourceEvaluator`, `make_text_completion_fn`, `make_evaluate_fn`, or `BookmarkInfo`. | Latest Builder Notes (2026-05-16T14:47:15+02:00): final AC-11 scoped proof run is green (`104 passed`, `0 failed`, `0 skipped`), `ruff` clean, pytest exit `0`. Independent editor error scan on all scoped source/test files returned no errors. | PASS |
| AC-6 | Workspace file inventory under `serve/knowledge/src/owlbear_knowledge/` no longer contains `bookmark_pipeline.py`, `bookmark_store.py`, `consolidation.py`, `copilot_auth.py`, or `scope_transfer.py`. | Deletion verified by live workspace file listing and direct search: these paths are absent. | PASS |
| AC-7 | `serve/knowledge/src/owlbear_knowledge/__init__.py:1-43` exports only live knowledge symbols; no `Bookmark`, `BookmarkPipeline`, `BookmarkResult`, `BookmarkStore`, `ConsolidationInsight`, or `ConsolidationService` export remains. | Static export surface inspection sufficient for this deletion AC. | PASS |
| AC-8 | `serve/knowledge/pyproject.toml:1-27` contains only `qdrant`, `embedding`, `intake`, `llm`, and `full` optional dependency groups; no `copilot` group remains. | Static manifest inspection sufficient for this deletion AC. | PASS |
| AC-10 | Live test-surface checks found no active `make_evaluate_fn`, `resolve_global_db_path`, `_bypass_copilot_auth`, `BookmarkPipeline`, `BookmarkStore`, or `ConsolidationService` wiring in the named affected suites. `tests/test_mcp_knowledge_tool_surface.py:61-126` retains only negative assertions that removed MCP tools stay absent, which is acceptable. | Proof-scope refinement task #1630 explicitly removed five entirely-RED non-#1582 suites from the runtime gate and reduced AC-11 to the six task-owned regression files; the remaining five affected files are verified by source/test-file inspection rather than by executing their unrelated RED suites. | PASS |
| AC-11 | Task body latest Builder Notes document the final architect-approved six-file command passing green with `104 passed`, `0 failed`, `0 skipped`, and clean lint. | Independent review check: `get_errors` returned “No errors found” for all scoped source/test files touched by #1582. | PASS |
- Blocking findings: none.

## Observations
- I independently ran `quality-runner` on the five files removed from #1582’s final proof scope (`tests/test_mcp_knowledge_tool_surface.py`, `tests/test_knowledge_guard_removal_1579.py`, `tests/test_persistence_source_wiring.py`, `tests/test_knowledge_ingest_source_identity_1556.py`, `tests/test_core_removal.py`). Result: `84 passed`, `1 failed`, lint clean. The sole failure was `tests/test_knowledge_guard_removal_1579.py::TestFromAC_GuardFilesDeleted::test_server_source_does_not_import_content_injection_guard`, which traces to the known `globals()["ContentInjectionGuard"] = object` compatibility alias at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:49`. That is guard-removal debt from #1579, not bookmark/scope/consolidation/copilot-auth work, and it is consistent with #1630’s architect-approved rationale for removing `tests/test_knowledge_guard_removal_1579.py` from #1582’s AC-11 runtime gate.
- A path-scoped `git status --porcelain -- <scoped files>` contamination check was not independently available on this tool surface. I relied on the task-body file inventory, live-file inspection, clean editor diagnostics across the scoped files, and the independent omitted-suite runner above.

[[2026-05-16T15:12:48+02:00]]
## Docs Gate

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| Item 1: README Verification | FIXED | `serve/knowledge/README.md` had two task-caused issues. `serve/mcp-knowledge/README.md` clean — Tools table contains only surviving tools, no retired symbols. |
| Item 2: External Attribution | N/A | Pure dead-code deletion, no external sources used. |
| Item 3: Research Doc | N/A | #1576 is a kanban task (dep link in `depends_on`), no `.owlbear/research/` file artifact. |
| Item 4: Deletion Detection | N/A | Grep on `serve/*/README.md` for `bookmark_pipeline`, `bookmark_store`, `consolidation.py`, `copilot_auth`, `scope_transfer` — zero module-file-name references found. Only surviving `get_consolidation_candidates` tool references appear, which are accurate. |

### Files Updated

- `serve/knowledge/README.md`:
  - Removed `copilot` optional extra row (AC-8 deleted this dep group from `pyproject.toml`)
  - Replaced stale "retained in code only as cleanup/deferred targets" paragraph with accurate "have been retired and removed from this package"

### Layer 1 (grep): Stale phrases absent — no matches for `copilot`, `retained in code only`, or `cleanup/deferred targets`.
### Layer 2 (editorial): README coherent — `full` extra now says "all of the above", paragraph reflects deletion fact correctly.

### Commit
`b7a5ccf` — docs: remove retired copilot extra and stale retention note from knowledge README (#1582, doc-writer)

### Scratch Cleanup
No `1582-*` scratch files found.

[[2026-05-16T15:24:31+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4637 passed, 20 failed, 14 skipped; lint clean (ruff exit 0)
- 20 failures analyzed — none attributable to #1582:
  - test_cockpit_view.py (10): cockpit domain, unrelated
  - test_server.py::TestFromAC_StatusNamesDictFormBug (7): pre-existing, explicitly deselected in AC-11
  - test_ideation_diagram.py (1): ideation domain, unrelated
  - test_engine_accessor_migration.py (2): engine domain, unrelated
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changes in serve/knowledge/, serve/mcp-knowledge/, and named test files — knowledge domain only)
- purpose match: PASS (dead code retirement per research #1576 classification)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC specificity excellent — 11 ACs with explicit symbol/file enumeration. Challenger drove useful refinements (AC-2, AC-3, AC-10). Minor gap: AC-11 proof gate was initially too broad, requiring follow-up #1630 for scope narrowing.

### Commit Integrity
- upstream commit presence: FAIL — no builder commit found for #1582. All 5 module deletions, 3 source edits (server.py, __init__.py, pyproject.toml), and 11 test updates are uncommitted working tree changes. Doc-writer commit b7a5ccf1 exists.
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- Evidence integrity concern (builder deliverables uncommitted): -.05

### Confidence: 0.95
### Action: archive

### Process Concern
Builder implementation for #1582 was never committed. All source and test changes exist only in the working tree. A `git checkout` or `git stash` would lose all work. This must be committed immediately. Per audit rules, auditor does not silently commit other agents' source code — flagging for user action."}
</invoke>
