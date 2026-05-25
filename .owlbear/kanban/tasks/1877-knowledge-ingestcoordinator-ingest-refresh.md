---
id: 1877
title: 'Knowledge: IngestCoordinator — ingest & refresh'
status: research
priority: needed
created: 2026-05-25T19:04:22.644852+02:00
updated: 2026-05-25T19:04:22.644852+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1870
  - 1871
  - 1875
ac:
  - ingest(IngestRequest) validates documents field (min_length=1); delegates 
    each document to Content.ingest
  - 'For CREATED results: enqueues new chunk_ids in Enrichment'
  - 'For REPLACED results: discards old chunk_ids in Enrichment, enqueues new chunk_ids'
  - refresh(RefreshRequest) identifies stale sources and re-ingests changed 
    documents
  - Returns IngestResult with per-document outcomes (created/replaced/unchanged 
    counts)
  - Content ingest + Enrichment enqueue are atomic per document
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Orchestrate document ingestion across Content and Enrichment. Batch ingest delegates to ContentStore, then enqueues new chunks for enrichment. Refresh re-ingests stale sources.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py`
- Design decisions: CP13 (Ingest as pure coordinator — owns no tables, orchestrates cross-module)
- Depends on: ContentStore ingest (#1871), EnrichmentStore queue (#1875), SourceStore (#1870)
- Target file: `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py`

## Implementation Notes

- IngestCoordinator receives all 4 leaf stores via constructor injection (testable in isolation)
- ingest delegates to Content.ingest per document; based on result state, enqueues or discards in Enrichment
- REPLACED cascade: discard old chunk_ids from Enrichment queue (they no longer exist), enqueue new ones
- refresh: reads source registry, checks last_ingested timestamps vs source config, re-ingests stale
- No direct table access — all operations through protocol methods on leaf stores