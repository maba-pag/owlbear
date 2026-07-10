---
description: "Run knowledge enrichment workers (Phase 1 extraction, Phase 2 consolidation)"
agent: knowledge-enricher
---

Enrich: ${input:scope_or_goal:Optional scope or goal (for example: process all pending work)}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting worker-scope choices, errors, findings, or continuation decisions, present exactly one decision item at a time before calling `askQuestions`.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## Parallel worker option (D7)

Open 1 to 6 chat sessions with this same prompt to run parallel workers. Each worker
pulls from the same coordinated queue, so sessions can process work concurrently
without manual sharding. Each Phase 1 worker must pass the exact `claim_token`
returned by `claim_enrichment_batch` when calling `store_enrichment`.

## Worker phases

1. Phase 1: pull chunk batches and store entity/relation extraction results.
2. If chunks fail, inspect `knowledge_stats`, correct the extraction/payload issue, then use `retry_enrichment` to requeue them.
3. Phase 2: pull consolidation candidates and store cross-source outcomes.
