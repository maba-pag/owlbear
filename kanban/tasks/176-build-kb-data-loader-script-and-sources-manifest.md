---
id: 176
title: Build KB data loader script and sources manifest
status: ideation
priority: needed
created: 2026-03-29T19:50:47.4770555+02:00
updated: 2026-03-29T19:50:47.4770555+02:00
tags:
    - phase-2
    - scope:knowledge
    - type:build
depends_on:
    - 32
class: standard
---

## Objective
Create data/knowledge/general/sources.yaml manifest and a loader script (packages/knowledge/src/owlbear_knowledge/loader.py) that reads the manifest and ingests documents via IngestPipeline.

## Acceptance Criteria
- [ ] sources.yaml manifest format: list of {name, type: file_glob/url_list, config: {glob/urls}, scope, enabled}
- [ ] Loader script reads manifest, resolves file globs relative to project root
- [ ] Registers each source via KnowledgeSourceStore.create()
- [ ] Checks content delta via StatusStore before re-ingesting
- [ ] Calls IngestPipeline.ingest_text() for new/changed documents
- [ ] CLI entry point: uv run python -m owlbear_knowledge.loader --manifest path
- [ ] Unit tests with mock EmbeddingProvider (no FlagEmbedding dep)
- [ ] Initial sources.yaml includes ~50 curated research docs + all skills + instructions

## Context
Split from #24. See docs/research/general-kb-initial-data-load.md.
