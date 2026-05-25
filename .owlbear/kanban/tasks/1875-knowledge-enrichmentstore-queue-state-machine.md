---
id: 1875
title: 'Knowledge: EnrichmentStore — queue state machine'
status: backlog
priority: needed
created: 2026-05-25T19:03:53.062341+02:00
updated: 2026-05-25T19:41:14.394448+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on: []
ac:
  - enqueue_chunks(chunk_ids, source_id) transitions chunks to PENDING; returns 
    count enqueued; idempotent on re-enqueue
  - discard_chunks(chunk_ids) removes chunks from queue regardless of state; 
    returns EnrichmentDiscardResult with counts per prior state
  - claim_batch(EnrichmentParams) returns up to batch_size PENDING chunks 
    transitioned to CLAIMED; assigns batch_id + claim timestamp
  - release_claim(batch_id) transitions all CLAIMED chunks in batch back to 
    PENDING; idempotent on unknown batch_id
  - fail_chunk(batch_id, chunk_id, error) transitions chunk to FAILED with error
    message; error retrievable
  - stats() returns EnrichmentStats with counts per state (pending, claimed, 
    completed, failed)
  - 'Table DDL: enrich_queue, enrich_batches; ensure_tables idempotent'
blocked: true
block_reason: DR pending
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement the enrichment state machine: chunks flow through PENDING → CLAIMED → COMPLETED/FAILED. Supports batch claiming, release, expiry. Owns `enrich_*` tables.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py`
- Design decisions: CP10 (agent-external enrichment — state machine only, no LLM), D52 (submit_extractions idempotency)
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py`

## Implementation Notes

- State machine: PENDING → CLAIMED → COMPLETED/FAILED (EnrichmentState enum)
- claim_batch assigns a unique batch_id and claim timestamp; agent uses batch_id for submit/fail
- release_claim returns chunks to PENDING (for agent crash recovery)
- Claim expiry: implementation may check claim_timestamp and auto-release stale claims
- enqueue is idempotent — re-enqueueing an existing chunk is a no-op
- discard removes regardless of current state (used by cascade when chunks are deleted)

[[2026-05-25T19:41:14+02:00]]
## Research
- Research doc: .owlbear/research/1875-enrichmentstore-queue-state-machine.md
- Sources: 8 studied, 4 high-relevance
- Recommendation: Implement following protocol as-is; add release_claim as non-protocol extension; advisory DR created for AC/protocol naming discrepancies (confidence: 0.78)
- Key findings: Protocol is authoritative per ARCHITECTURE.md Spec Amendment Process. AC conflicts in 3 places (state naming IN_PROGRESS vs CLAIMED, mark_failed vs fail_chunk, release_claim absent from protocol). Table design: enrich_queue + enrich_batches with ensure_tables classmethod. Claim expiry is internal (CP22, 600s). Existing store patterns (GraphStore, KnowledgeSourceStore) provide implementation template.
- Challenge: reconsider (0.37 confidence in original) — revised from "amend protocol" to "protocol-first, DR for conflicts"
- Decision request: decisions/pending/1875-decision.md (advisory, AC/protocol resolution)
