---
id: 430
title: Test RefreshOrchestrator -- dispatch by source type
status: archived
priority: needed
created: 2026-03-02T01:51:16.0712192+01:00
updated: 2026-03-02T09:15:31.5280841+01:00
started: 2026-03-02T01:51:21.6113236+01:00
completed: 2026-03-02T09:15:31.5280841+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD red-phase for #384. Tests for RefreshOrchestrator dispatching refresh by source type. Includes file_glob resolution (merged from #387).

## Acceptance Criteria
- RefreshOrchestrator accepts KnowledgeSourceStore + IngestPipeline + WebCrawler dependencies
- refresh(source) dispatches based on source.source_type
- url_list: calls pipeline.ingest(url) for each URL in config['urls']
- crawl: builds CrawlConfig from config dict, calls crawl_and_ingest(crawler, pipeline, config)
- file_glob: resolves config['pattern'] relative to config.get('base_dir', workspace_root) via pathlib.Path.glob(), calls pipeline.ingest(path) for each match
- file_glob: non-matching pattern returns empty results (not error)
- file_glob: workspace_root fallback when base_dir not specified
- Updates source.last_refreshed_at on success (via store.update)
- Sets source.last_error on failure (via store.update)
- Clears last_error on success
- Returns RefreshResult summary: source_id, refreshed count, skipped count, failed count, errors list
- Disabled source raises ValueError (or is skipped with warning)
- refresh_all() processes all enabled sources ordered by priority descending, returns list[RefreshResult]
- Individual URL/file failures don't abort the whole source refresh (collects errors)
- All tests use mocked IngestPipeline and WebCrawler (no real I/O)

Depends on #428 (test #382), #429 (test #383)
