---
id: 1582
title: Retire bookmark/scope/consolidation dead code from knowledge module
status: in-progress
priority: needed
created: 2026-05-15T16:22:28.247084+00:00
updated: 2026-05-16T04:19:25.560284+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
parent:
depends_on:
  - 1576
blocked: false
block_reason:
claimed_at:
archival_reason:
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
- [ ] AC-11: `uv run pytest tests/ serve/mcp-knowledge/tests/ -x` passes with zero failures after cleanup.

Out of scope: evaluator.py module deletion (classified as "keep" in #1576), schema table removal (#1583), stub labeling and README updates (#1584).

Proof bundle: existing
Existing proof scope: tests/test_mcp_knowledge_tool_surface.py, tests/test_enrichment_persistence_1557.py, tests/test_knowledge_guard_removal_1579.py, tests/test_browser_fetcher_wiring.py, tests/test_persistence_source_wiring.py, tests/test_knowledge_ingest_source_identity_1556.py, tests/test_server.py, tests/test_core_removal.py, serve/mcp-knowledge/tests/
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
