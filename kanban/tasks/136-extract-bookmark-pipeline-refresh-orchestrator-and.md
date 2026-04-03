---
id: 136
title: Extract bookmark pipeline, refresh orchestrator, and bookmark MCP tools
status: todo
priority: nice-to-have
created: 2026-03-29T12:07:36.7065824+02:00
updated: 2026-04-03T03:49:41.4074656+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 33
    - 135
    - 223
blocked: true
block_reason: 'TestFromAC conflict: task-136 requires refresh_all to call list_enabled; task-554 TestFromAC_RefreshAll::test_calls_list_all_not_list_enabled requires list_all and asserts list_enabled MUST NOT be called. Architect must retire or update task-554 tests.'
class: standard
---

## Objective
Extract Group B modules from v1 that depend on IngestPipeline (#33).

## Acceptance Criteria
- [ ] BookmarkResult model + BookmarkPipeline class extracted to packages/knowledge/src/owlbear_knowledge/bookmark_pipeline.py
  - Constructor: BookmarkPipeline(bookmark_store: BookmarkStore, evaluator: SourceEvaluator, ingest_pipeline: IngestPipeline | None = None, web_read_fn: Callable[[str], Awaitable[str | None]], ingest_threshold: float = 0.7)
  - web_read_fn is REQUIRED (no default) â€” knowledge package must not own HTTP fetching; _default_web_read is NOT extracted
  - process(url, reason, scope, project_context, cancel) returns BookmarkResult
  - Cooperative cancellation via CancelSignal (from #135) at each stage boundary: dedup, extract, evaluate, ingest, store
- [ ] RefreshResult model + RefreshOrchestrator class extracted to packages/knowledge/src/owlbear_knowledge/refresh.py
  - Constructor: RefreshOrchestrator(store: KnowledgeSourceStore, pipeline: IngestPipeline, crawl_handler: CrawlHandler | None = None, workspace_root: Path | None = None)
  - refresh(source, cancel) dispatches by SourceType (url_list, crawl, file_glob)
  - refresh_all(scope, cancel) iterates enabled sources with cooperative cancellation
  - file_glob handler uses sandbox_path (from #135) for path-traversal prevention
  - _update_source_record persists refresh timestamp and error summary on source record
- [ ] KnowledgeSourceStore.list_enabled(scope) method added to source_store.py â€” returns enabled sources filtered by optional scope, ordered by priority DESC
- [ ] bookmark_source and list_bookmarks registered as MCP tools in packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py, following the v2 pattern established by #152
  - bookmark_source(ctx, url, reason=None) wraps BookmarkPipeline.process()
  - list_bookmarks(ctx, tag=None, min_score=None) wraps BookmarkStore.list()
  - AppContext extended with bookmark_pipeline and bookmark_store fields, initialized in app_lifespan, accessed via ctx.request_context.lifespan_context
- [ ] bookmark_toolset.py is NOT extracted as a module â€” MCP tools replace it
- [ ] packages/knowledge __init__.py exports updated: BookmarkResult, BookmarkPipeline, RefreshResult, RefreshOrchestrator

## Context
Split from #130 (Group B â€” depends on #33 IngestPipeline). See docs/research/extract-knowledge-secondary-features.md S3.

## Dependencies
- Depends on #33 (entity extraction + graph builders â€” provides IngestPipeline/IngestResult Protocol)
- Depends on #135 (provides CancelSignal, sandbox_path, SourceEvaluator, EvaluationResult)

[[2026-03-29]] Sun 16:17
## Architecture Review
**Verdict:** REFINE (AC tightened, ready for approval)

### AC Assessment
- BookmarkPipeline extraction: Original was vague on target path, no constructor spec, silent on _default_web_read v1 deps. Rewrote with target file path, full constructor sig, web_read_fn REQUIRED, _default_web_read dropped.
- RefreshOrchestrator extraction: Original was vague on target path, no sig, no mention of list_enabled gap. Rewrote with target file path, full constructor sig, added list_enabled AC.
- MCP tool registration: Original had adequate intent. Refined with tool signatures and AppContext extension requirement.
- Unit tests: Was bundled with impl, redundant with test-writer pipeline stage. Removed (pipeline test-writer handles RED phase).
- No bookmark_toolset extraction: Clear negative constraint. Kept as-is.
- __init__.py exports: Was missing from original. Added BookmarkResult, BookmarkPipeline, RefreshResult, RefreshOrchestrator.

### Architecture Notes
- BookmarkPipeline and RefreshOrchestrator share the knowledge extraction domain and deps (#33 IngestPipeline, #135 CancelSignal). MCP tool registration is ancillary (2 thin wrappers replacing bookmark_toolset.py).
- v2 pattern: existing stores (BookmarkStore, KnowledgeSourceStore) are sync sqlite3 facades. BookmarkPipeline and RefreshOrchestrator are async orchestrators.
- KnowledgeSourceStore.list_enabled() missing in v2 (only list_all exists). Added as ancillary AC.
- _default_web_read has v1-only deps (httpx, owlbear.web_extract, owlbear.core.retry). Making web_read_fn required avoids HTTP deps in knowledge package. Follows extractor.py stub pattern.
- MCP tools follow existing AppContext + Protocol pattern in mcp-knowledge server.py (v2 pattern established by #152; tools.py was v1 approach via #72).

### Changes Made
- Added formal depends_on [33, 135]
- Rewrote body with tightened AC (6 verifiable lines with sub-criteria)
- Removed redundant unit tests AC (pipeline test-writer handles RED)
- Added list_enabled() store method as explicit AC
- Added __init__.py exports AC

### Dependencies
- Verified: #33 (ideation) provides IngestPipeline/IngestResult Protocol
- Verified: #135 (backlog) provides CancelSignal, sandbox_path, SourceEvaluator
- Both deps unresolved but correctly tracked via depends_on

[[2026-04-02]] Thu 22:49
## Test-Writer Notes
- Test file: tests/test_bookmark_pipeline_136.py
- Classes: TestFromAC_BookmarkResultModel, TestFromAC_BookmarkPipelineConstructor, TestFromAC_BookmarkPipelineProcess, TestFromAC_RefreshResultModel, TestFromAC_RefreshOrchestratorConstructor, TestFromAC_RefreshOrchestratorRefresh, TestFromAC_RefreshOrchestratorFileGlob, TestFromAC_UpdateSourceRecord, TestFromAC_ListEnabled, TestFromAC_MCPBookmarkTools, TestFromAC_InitExports
- Tests per category: happy 25, edge 12, error 10, boundary 7
- Total: 54 tests, all FAIL
- ruff: clean
- AC coverage:
  - BookmarkResult+BookmarkPipeline in bookmark_pipeline.py: TestFromAC_BookmarkResultModel (6), TestFromAC_BookmarkPipelineConstructor (4), TestFromAC_BookmarkPipelineProcess (8)
  - RefreshResult+RefreshOrchestrator in refresh.py: TestFromAC_RefreshResultModel (4), TestFromAC_RefreshOrchestratorConstructor (2), TestFromAC_RefreshOrchestratorRefresh (5), TestFromAC_RefreshOrchestratorFileGlob (2), TestFromAC_UpdateSourceRecord (2)
  - KnowledgeSourceStore.list_enabled(scope): TestFromAC_ListEnabled (5)
  - bookmark_source + list_bookmarks MCP tools + AppContext: TestFromAC_MCPBookmarkTools (8)
  - packages/knowledge __init__.py exports: TestFromAC_InitExports (8)
  - bookmark_toolset.py NOT extracted (negative constraint): test_default_web_read_not_exported_from_module

[[2026-04-02]] Thu 23:47
## Builder Notes
- Files changed: bookmark_pipeline.py (new), source_store.py (list_enabled added), refresh.py (_handle_file_glob sandbox), tools.py (new), __init__.py (exports)
- Tests: 53/54 task-136 tests pass; 1 blocked by TestFromAC interface conflict
- Lint: ruff clean
- Blocked: Conflict between task #136 AC (refresh_all must call list_enabled) and task #554 TestFromAC (refresh_all must call list_all, list_enabled MUST NOT be called)
- Non-conflicting deliverables committed: commit f315d26
- AC suggestion: Architect must retire or update task #554 TestFromAC_RefreshAll::test_calls_list_all_not_list_enabled to allow list_enabled
