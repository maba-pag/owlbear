---
id: 1893
title: 'Knowledge: MCP wire ingest_document to IngestCoordinator.ingest'
status: research
priority: needed
created: 2026-05-27T01:00:59.346799+02:00
updated: 2026-05-27T01:00:59.346799+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - ingest_document tool calls IngestCoordinator.ingest(IngestRequest)
  - Source resolved or created via SqliteSourceStore (inline source for ad-hoc 
    docs)
  - IngestRequest constructed with source_id, documents=(IngestDocument(...),)
  - IngestResult fields surfaced in response string (documents_processed, 
    chunks_created, chunks_enqueued)
  - Old IngestPipeline.ingest_text() call removed
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace IngestPipeline.ingest_text() in `ingest_document` with IngestCoordinator.ingest(IngestRequest). Resolve or create a source record for the inline document. Build IngestRequest with source_id and single IngestDocument.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`