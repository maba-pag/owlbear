---
id: 1878
title: 'Knowledge: IngestCoordinator — delete cascade'
status: research
priority: needed
created: 2026-05-25T19:04:37.443482+02:00
updated: 2026-05-25T19:04:37.443482+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1870
  - 1872
  - 1874
  - 1876
ac:
  - 'delete_source(source_id) executes cascade: Sources.delete → Content.purge → Enrichment.discard
    → Enrichment.purge → Graph.invalidate_evidence_by_chunks'
  - PurgeResult.status = COMPLETE when all steps succeed; PARTIAL when a step 
    fails
  - PurgeResult.completed_steps lists step names that succeeded (in order)
  - PurgeResult.failed_step names the step that failed; error carries the 
    message
  - Steps after a failure are not attempted (fail-fast)
  - Each step is idempotent — re-running delete_source after partial failure 
    resumes safely
  - Docstring includes idempotency guarantee (D63)
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Orchestrate source deletion with 5-step cascade across all modules. Track progress and handle partial failure gracefully.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py`
- Design decisions: CP13 (Ingest coordinates cascades), D63 (idempotency + PurgeResult)
- Depends on: SourceStore (#1870), ContentStore purge (#1872), EnrichmentStore purge (#1876), GraphStore evidence (#1874)
- Target file: `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` (extends same module)

## Implementation Notes

- 5-step cascade in order: Sources.delete → Content.purge_source → Enrichment.discard_chunks (from purge result) → Enrichment.purge_source → Graph.invalidate_evidence_by_chunks
- Each step is idempotent — safe to re-run after partial failure
- PurgeResult tracks completed_steps as tuple[str,...]; on failure records failed_step + error
- PurgeStatus.COMPLETE vs PARTIAL based on whether all 5 steps succeeded
- Content.purge_source returns chunk_ids that were deleted — these feed into Enrichment.discard and Graph.invalidate