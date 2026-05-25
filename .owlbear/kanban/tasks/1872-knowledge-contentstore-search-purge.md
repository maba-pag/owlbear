---
id: 1872
title: 'Knowledge: ContentStore — search & purge'
status: research
priority: needed
created: 2026-05-25T19:03:11.262484+02:00
updated: 2026-05-25T19:03:11.262484+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1871
ac:
  - search(ContentSearchQuery) returns results with normalised scores (0.0-1.0);
    respects scope filter (scope = Content filter only, D53)
  - Search combines vector similarity (Qdrant) and keyword match; scores 
    normalised consistently
  - purge_source(source_id) removes all documents + chunks + Qdrant vectors for 
    that source; returns ContentPurgeResult with counts
  - stats() returns ContentStats with document_count, chunk_count, total_tokens
  - Purge is idempotent — purging unknown source returns zero counts, no error
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement hybrid search (vector + keyword) and source-scoped content purge. Completes the ContentStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/content.py`
- Design decisions: D53 (scope = Content filter only, graph is global), CP9 (embedding encapsulation)
- Depends on: ContentStore ingest (task #1871) for tables and core infrastructure
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/content.py` (extends same module)

## Implementation Notes

- Hybrid search: Qdrant vector similarity + SQLite keyword match (FTS5 or LIKE)
- Scores normalised to 0.0-1.0 regardless of underlying similarity metric
- Scope filters Content only — scope is not part of entity identity (D53)
- purge_source removes all documents and chunks for a source; also removes Qdrant vectors
- Purge is idempotent — purging unknown source returns ContentPurgeResult with zero counts