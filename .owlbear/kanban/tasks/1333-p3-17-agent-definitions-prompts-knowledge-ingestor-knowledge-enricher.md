---
id: 1333
title: 'P3-17: Agent definitions + prompts (knowledge-ingestor + knowledge-enricher)'
status: research
priority: important
created: 2026-05-04T05:48:50.177453+00:00
updated: 2026-05-04T05:51:41.356435+00:00
tags:
- phase-3
- scope:agents
- knowledge
- agent
parent: 1316
depends_on:
- 1328
- 1332
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.10)

## Acceptance Criteria

- [ ] knowledge-ingestor.agent.md created with tools: ingest_document, refresh_source, list_sources, get_stats, search_knowledge
- [ ] knowledge-enricher.agent.md created with tools: get_next_batch, get_consolidation_candidates, store_enrichment, get_stats, search_knowledge
- [ ] Enricher agent specifies model: gpt-5.4 mini (0.33x cost) with fallback chain (D8)
- [ ] /kb-ingest.prompt.md created — triggers ingestor agent for source ingestion
- [ ] /kb-enrich.prompt.md created — triggers enricher agent with parallelism option (1-6 workers, D7)
- [ ] Enricher worker loop documented in agent body (Phase 1 + Phase 2 sequence)
- [ ] Agent files follow structural standards (h-agent-structure)

## Scope

- **In scope:** Agent .agent.md files, prompt .prompt.md files, enricher worker loop documentation
- **Out of scope:** Entity type schema extension (D13 — deferred to enricher prompt design), batch rebuild prompt (§6)