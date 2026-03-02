---
id: 384
title: Refresh orchestrator — dispatch by source type
status: archived
priority: needed
created: 2026-03-01T20:15:11.4618093+01:00
updated: 2026-03-02T09:14:48.7181095+01:00
started: 2026-03-01T20:23:02.6913605+01:00
completed: 2026-03-02T09:14:48.7181095+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 430
class: standard
---

From #254 source-registry-research.md. Orchestrator that reads source configs and dispatches refresh by type. Absorbs #387 (file_glob source type) since file_glob is just one handler method within the orchestrator.

## Location
- src/owlbear/memory/knowledge/refresh.py (new file)

## Acceptance Criteria
- RefreshOrchestrator class with constructor accepting: store (KnowledgeSourceStore), pipeline (IngestPipeline), crawler (WebCrawler | None), workspace_root (Path)
- async refresh(source: KnowledgeSource) -> RefreshResult: dispatches by source.source_type
- url_list handler: iterates config['urls'], calls pipeline.ingest(url) per URL, collects results
- crawl handler: builds CrawlConfig from config dict (maps seed_urls, max_depth, max_pages, etc.), calls crawl_and_ingest(crawler, pipeline, crawl_config), raises ValueError if crawler is None
- file_glob handler: resolves config['pattern'] relative to config.get('base_dir', workspace_root) via pathlib.Path.glob(), calls pipeline.ingest(path) per matched file
- file_glob: non-matching pattern yields 0 results (not an error)
- file_glob: paths resolved relative to workspace_root when base_dir absent
- Individual item failures (single URL, single file) don't abort source refresh -- errors collected in RefreshResult.errors
- On success: updates source record via store.update() with last_refreshed_at = now, last_error = None
- On failure (all items failed): updates source record with last_error = summary message
- RefreshResult(BaseModel, frozen=True): source_id (str), refreshed (int), skipped (int), failed (int), errors (list[str])
- async refresh_all(scope: str | None = None) -> list[RefreshResult]: loads all enabled sources via store.list_enabled(scope), processes each, returns results
- refresh_all: ordered by source.priority descending (highest priority first)
- Disabled source passed to refresh() raises ValueError
- Delta detection is handled by existing IngestPipeline.check_content_changed -- no duplicate logic

Depends on test task #430, #382, #383.
