---
id: 254
title: 'Research: Source registry and crawl scheduling'
status: ideation
priority: important
created: 2026-02-28T12:40:19.7164183+01:00
updated: 2026-02-28T14:54:39.1641618+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
class: standard
---

## Context
Need a way to manage knowledge sources: 'refresh all pages from Confluence space X', 'monitor PydanticAI docs for changes'. Currently ingestion is manual one-shot.

## Research Checklist
- [ ] Theoretical validity: What metadata defines a source? URL pattern, crawl config, schedule, scope?
- [ ] Prior art: How do LlamaIndex connectors, Haystack pipeline registries, Airflow DAGs handle this?
- [ ] Technical feasibility: Source definitions as config (TOML/YAML) vs database records?
- [ ] Architecture fit: Integration with existing CrawlConfig, WebCrawler, IngestPipeline
- [ ] Implementation approach: Cron-style scheduling (APScheduler?) vs manual refresh commands

## Questions to Answer
- Source types: URL list, sitemap, RSS feed, file glob, Confluence API, Git repo?
- Schedule granularity: daily, hourly, on-demand?
- Priority: which sources to refresh first when resources are limited?
- Conflict: what if a refresh runs while user is querying?
- CLI: bearclaw knowledge sources add/list/refresh/schedule?

## Acceptance Criteria
- [ ] Research doc in docs/
- [ ] Follow-up implementation tasks created
- [ ] Source registry data model proposed
- [ ] Scheduling approach recommended
