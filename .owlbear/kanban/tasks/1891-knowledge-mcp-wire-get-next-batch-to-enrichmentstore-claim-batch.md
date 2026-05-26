---
id: 1891
title: 'Knowledge: MCP wire get_next_batch to EnrichmentStore.claim_batch'
status: research
priority: needed
created: 2026-05-27T01:00:59.243665+02:00
updated: 2026-05-27T01:00:59.243665+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - get_next_batch calls 
    EnrichmentStore.claim_batch(EnrichmentParams(batch_size=limit))
  - Each claimed item hydrated with text + metadata from 
    ContentStore.get_chunk()
  - 'Response shape unchanged: list[EnrichmentChunk] with text, doc_title, section_path,
    source_name'
  - Old direct SQL claiming code removed
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace direct SQL claiming in `get_next_batch` with EnrichmentStore.claim_batch(EnrichmentParams). Hydrate response with chunk text via ContentStore.get_chunk(). Maintain same response shape (chunk_id, text, doc_title, section_path, source_name, scope, claim_token, claimed_at).

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`