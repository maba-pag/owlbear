---
id: 999
title: Thread CancelSignal from IngestPipeline to GraphEnricher schedule calls
status: archived
priority: nice-to-have
created: 2026-03-25T04:37:19.7207908+01:00
updated: 2026-03-26T11:38:42.5146662+01:00
started: 2026-03-26T11:38:42.5146662+01:00
completed: 2026-03-26T11:38:42.5146662+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 871
class: standard
---

[[2026-03-25]] Wed 04:37
Source: #871 research (docs/research/graphenricher-cancellation-draining.md). Depends on #997 (GraphEnricher CancelSignal support).

AC:

1. IngestPipeline._ingest_from_intake passes its cancel parameter to enricher.schedule_graph_enrichment and enricher.schedule_inter_doc_enrichment.
2. When cancel is set before enrichment scheduling, no new enrichment tasks are created.
3. Existing callers that omit cancel continue to work unchanged.

[[2026-03-26]] Thu 11:38

## Architecture Review

VERDICT: Merge (delete) -- superseded by #1005 which has refined AC and is already approved at todo.

# 1005 covers all three AC lines from #999 with more precise line references

# 1006 (TDD RED) is in-progress for #1005

No tasks depend on #999. Deleting as redundant.
