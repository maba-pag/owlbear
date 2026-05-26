---
id: 1886
title: 'Knowledge: IngestCoordinator.refresh() — implement refresh with fetcher'
status: research
priority: needed
created: 2026-05-26T06:08:59.608970+02:00
updated: 2026-05-26T06:09:04.452937+02:00
tags:
  - knowledge
  - layer-2
parent: 1877
depends_on:
  - 1884
  - 1885
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement the IngestCoordinator.refresh() method using the ContentFetcher protocol and SourceStore refresh watermarks.

## Context

- Depends on: SourceStore last_refreshed_at write path, ContentFetcher protocol
- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py` (RefreshRequest/RefreshResult)
- Design: list active+refreshable sources, fetch content, call self.ingest(), update watermark
- Gap identified in: `.owlbear/research/1877-ingest-coordinator.md`