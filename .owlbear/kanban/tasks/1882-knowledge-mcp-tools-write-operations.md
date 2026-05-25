---
id: 1882
title: 'Knowledge: MCP tools — write operations'
status: research
priority: needed
created: 2026-05-25T19:05:34.718298+02:00
updated: 2026-05-25T19:05:34.718298+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1870
  - 1875
  - 1876
  - 1877
  - 1878
ac:
  - knowledge_ingest tool calls IngestCoordinator.ingest; batch documents 
    accepted
  - knowledge_delete_source tool calls IngestCoordinator.delete_source; 
    PurgeResult surfaced in response
  - knowledge_register_source tool calls SourceStore.register_source; typed 
    config validated
  - knowledge_enrich / knowledge_submit_extractions tools call EnrichmentStore 
    methods
  - All write tools propagate errors correctly; mutations are atomic
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Wire MCP server write tools (ingest, delete_source, register_source, enrichment operations) to the new protocol-conformant implementations.

## Context

- MCP server: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- Depends on: IngestCoordinator (#1877, #1878), SourceStore (#1870), EnrichmentStore (#1875, #1876)

## Implementation Notes

- knowledge_ingest: accepts batch documents via IngestRequest; delegates to IngestCoordinator.ingest
- knowledge_delete_source: calls IngestCoordinator.delete_source; returns PurgeResult summary
- knowledge_register_source: validates typed SourceConfig discriminated union; calls SourceStore.register_source
- Enrichment tools: claim_batch, submit_extractions, release_claim map directly to EnrichmentStore methods
- Error handling: Pydantic validation errors → MCP error with details; runtime errors → MCP error with message