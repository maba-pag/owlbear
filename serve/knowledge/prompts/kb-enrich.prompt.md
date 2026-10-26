---
description: "Run knowledge enrichment workers for entity and relation extraction"
agent: knowledge-enricher
---

Enrich: ${input:scope_or_goal:Optional scope or goal (for example: process all pending work)}

## Execution Contract

Use the user's language unless they ask otherwise. This worker is queue-driven and autonomous; it has no user-decision tool and should not manufacture choices during extraction.

Continue until `claim_enrichment_batch` returns no work. An empty queue is successful completion.
If a payload or store failure cannot be corrected from the returned error and documented contract,
report the failed chunk and stop rather than blindly resetting it.

## Worker loop

1. Pull chunk batches and store entity/relation extraction results.
2. If chunks fail, inspect `knowledge_stats`, correct the extraction/payload issue, then use `retry_enrichment` to requeue them.
3. Continue until no chunks are claimable or failed.
