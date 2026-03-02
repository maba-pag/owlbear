---
id: 254
title: 'Research: Source registry and crawl scheduling'
status: archived
priority: important
created: 2026-02-28T12:40:19.7164183+01:00
updated: 2026-03-02T09:14:12.1540848+01:00
started: 2026-03-01T19:02:49.3150506+01:00
completed: 2026-03-02T09:14:12.1540848+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
class: standard
---

## Context
Need a way to manage knowledge sources: 'refresh all pages from Confluence space X', 'monitor PydanticAI docs for changes'. Currently ingestion is manual one-shot.

## Research Checklist
- [x] Theoretical validity: What metadata defines a source? URL pattern, crawl config, schedule, scope?
- [x] Prior art: How do LlamaIndex connectors, Haystack pipeline registries, Airflow DAGs handle this?
- [x] Technical feasibility: Source definitions as config (TOML/YAML) vs database records?
- [x] Architecture fit: Integration with existing CrawlConfig, WebCrawler, IngestPipeline
- [x] Implementation approach: Cron-style scheduling (APScheduler?) vs manual refresh commands

## Questions to Answer
- Source types: URL list, sitemap, RSS feed, file glob, Confluence API, Git repo?
- Schedule granularity: daily, hourly, on-demand?
- Priority: which sources to refresh first when resources are limited?
- Conflict: what if a refresh runs while user is querying?
- CLI: bearclaw knowledge sources add/list/refresh/schedule?

## Acceptance Criteria
- [x] Research doc in docs/ -- docs/source-registry-research.md (179 lines)
- [x] Follow-up implementation tasks created -- #382-387 (all done)
- [x] Source registry data model proposed -- SourceType enum + KnowledgeSource model
- [x] Scheduling approach recommended -- manual refresh via RefreshOrchestrator, defer cron to phase-14
