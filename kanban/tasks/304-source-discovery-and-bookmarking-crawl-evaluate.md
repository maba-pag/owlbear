---
id: 304
title: Source discovery and bookmarking — crawl, evaluate, ingest pipeline
status: ideation
priority: needed
created: 2026-03-01T02:54:08.8905141+01:00
updated: 2026-03-01T02:54:54.3532222+01:00
tags:
    - phase-13
    - knowledge-graph
    - browser
depends_on:
    - 291
    - 292
class: standard
---

## Context
When researching for a project, OwlBear finds useful sources (repos, docs, articles). It needs to evaluate whether content is worth keeping, ingest it into the knowledge base, and maintain a source registry for future reference.

## Acceptance Criteria
- [ ] SourceEvaluator: score content relevance to current project (LLM-based)
- [ ] Bookmark pipeline: discover URL -> extract content -> evaluate relevance -> ingest if worthy
- [ ] Source registry (knowledge graph): track all discovered sources with metadata
- [ ] Agent tool: bookmark_source(url, reason) -> evaluates and optionally ingests
- [ ] Agent tool: list_bookmarks(project, tag) -> show known sources
- [ ] Auto-discover: when agent reads a page, offer to bookmark useful ones
- [ ] Dedup: don't re-ingest content already in knowledge base (content hash check)
- [ ] Unit tests with mocked content extraction and evaluation
