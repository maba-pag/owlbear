---
id: 140
title: Extract bookmark pipeline + refresh orchestrator
status: archived
priority: medium
created: 2026-03-29 14:51:50.492045+02:00
updated: 2026-04-04 07:09:51.512909+02:00
started: 2026-04-04 07:09:25.595607+02:00
completed: 2026-04-04 07:09:25.595607+02:00
tags:
- phase-1
- ' scope:knowledge'
- ' type:build'
depends_on:
- 33
- 139
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Extract bookmark_pipeline.py and refresh.py from v1 into the knowledge package. These modules depend on IngestPipeline from #33 which is still in ideation.

## Acceptance Criteria
AC will be refined by the architect when #33 (ingest pipeline) interface is defined. Preliminary scope:

### bookmark_pipeline.py
- [ ] BookmarkPipeline class orchestrating: dedup check, content extraction, relevance evaluation, conditional ingest, bookmark storage
- [ ] BookmarkResult model (frozen Pydantic BaseModel)
- [ ] Dependencies accepted as constructor params: BookmarkStore, SourceEvaluator, IngestPipeline, web_read_fn (callable)
- [ ] CancelSignal defined as Protocol or extracted from v1 cancellation.py
- [ ] Zero PydanticAI imports

### refresh.py
- [ ] RefreshOrchestrator dispatching by SourceType (url_list, crawl, file_glob)
- [ ] RefreshResult model (frozen Pydantic BaseModel)
- [ ] Dependencies accepted as constructor params: IngestPipeline, KnowledgeSourceStore, CrawlHandler (callable)
- [ ] workspace_root accepted as Path parameter (replaces v1 sandbox_path import)
- [ ] CancelSignal shared with bookmark_pipeline
- [ ] Zero PydanticAI imports

### Verification
- [ ] TDD-paired test task created before implementation
- [ ] Unit tests for both modules
- [ ] ruff check passes

## Exclusions
- bookmark_toolset.py is EXCLUDED: MCP tool registration is a separate domain (tools/agent-config) and requires a design decision (FunctionToolset vs MCP tool). Create a separate task when needed.
- web_extract is an external dependency; bookmark_pipeline accepts a callable, not an import.
- cancellation.py is purely a CancelSignal protocol; define inline or as a shared protocol.

## Context
Part of #130 split. Blocked on #33 (ingest pipeline, currently in ideation). Also depends on #139 (evaluator stub). v1 sources: bookmark_pipeline.py (264 LOC), refresh.py (331 LOC). See docs/research/extract-knowledge-engine-v1.md.

[[2026-04-03]] Fri 00:39
## Architecture Review
**Verdict:** BLOCK (duplicate)
**DR Verification:** N/A -- not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| BookmarkPipeline class | Fully covered by #136 AC (identical scope) | Redundant |
| BookmarkResult model | Fully covered by #136 AC | Redundant |
| Constructor DI params | Fully covered by #136 AC (identical signature) | Redundant |
| CancelSignal Protocol | Already exists in cancellation.py (from #135) | Redundant |
| Zero PydanticAI imports | Same constraint in #136 AC | Redundant |
| RefreshOrchestrator | Fully covered by #136 AC + #554/#555 (TDD pair) | Redundant |
| RefreshResult model | Fully covered by #136 AC | Redundant |
| workspace_root Path param | Already implemented in refresh.py | Redundant |
| TDD-paired test task | Already exists as #554 (review) | Redundant |

### Architecture Notes
This task is a **full duplicate** of #136 (Extract bookmark pipeline, refresh orchestrator, and bookmark MCP tools). Both originate from the #130 split.

Evidence:
- bookmark_pipeline.py already exists: committed in f315d26 (#136 builder)
- refresh.py already exists: committed in f315d26 (#136) and 1e27919 (#554/555)
- cancellation.py with CancelSignal already exists from #135
- __init__.py already exports BookmarkPipeline, BookmarkResult, RefreshOrchestrator, RefreshResult
- #136 is a superset (also covers MCP tools and list_enabled)
- #554 (test) and #555 (impl) are the TDD pair for RefreshOrchestrator

#140 should be deleted. All scope is covered by #136 + #554/#555.

### Changes Made
- Blocked to ideation as duplicate of #136

### Dependencies
- #33 (archived): no longer a blocker
- #139 (archived): no longer a blocker
- Both modules already implemented by #136 pipeline
