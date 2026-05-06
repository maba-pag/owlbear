---
description: "Run knowledge enrichment workers (Phase 1 extraction, Phase 2 consolidation)"
agent: knowledge-enricher
---

Enrich: ${input:scope_or_goal:Optional scope or goal (for example: process all pending work)}

## Parallel worker option (D7)

Open 1 to 6 chat sessions with this same prompt to run parallel workers. Each worker
pulls from the same coordinated queue, so sessions can process work concurrently
without manual sharding.

## Worker phases

1. Phase 1: pull chunk batches and store entity/relation extraction results.
2. Phase 2: pull consolidation candidates and store cross-source outcomes.
