---
id: 140
title: Extract bookmark pipeline + refresh orchestrator
status: ideation
priority: nice-to-have
created: 2026-03-29T14:51:50.4920453+02:00
updated: 2026-03-29T14:51:50.4920453+02:00
tags:
    - phase-1
    - ' scope:knowledge'
    - ' type:build'
depends_on:
    - 33
    - 139
class: standard
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
