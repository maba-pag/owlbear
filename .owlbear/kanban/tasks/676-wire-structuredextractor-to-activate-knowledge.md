---
id: 676
title: Wire StructuredExtractor to activate knowledge graph layer
status: research
priority: important
created: 2026-04-08T18:26:20.7985508+02:00
updated: 2026-04-08T18:26:20.7985508+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:analysis'
class: standard
---

## Context

Analysis confirmed that the knowledge graph layer is a no-op in production. The MCP knowledge server creates `EntityExtractor(model)` with a model name, but `EntityExtractor` requires an injected `StructuredExtractor` via the `extractor=` keyword argument to actually produce entities and edges. Without it:

- `EntityExtractor.extract()` returns empty `ExtractionResult`
- Zero entities/edges are ever stored in the graph
- Graph-augmented retrieval degrades to pure vector search
- ColBERT vectors are computed by BGE-M3 but never stored in Qdrant

The `StructuredExtractor` protocol (`serve/knowledge/src/owlbear_knowledge/protocol.py`) requires an async callable that produces structured JSON from prompts. The `OWLBEAR_MODEL` env var is already read and passed to `EntityExtractor` — it just needs to be used to construct a real extractor.

## Acceptance Criteria

- [ ] AC1: Implement a concrete `StructuredExtractor` that uses the model specified by `OWLBEAR_MODEL`
- [ ] AC2: Wire the extractor into `EntityExtractor(extractor=...)` in `app_lifespan()` of `mcp-knowledge/server.py`
- [ ] AC3: Ingest a test document and verify entities and edges appear in `get_stats` output
- [ ] AC4: Verify `search_knowledge` returns graph expansion context (not just vector chunks)
- [ ] AC5: Graceful degradation — if the LLM call fails, ingestion still succeeds (vector-only fallback)
- [ ] AC6: The `StructuredExtractor` implementation lives in the knowledge engine package, not the MCP server

Needs decomposition: This may need a sub-task for the `StructuredExtractor` implementation and a separate sub-task for wiring + integration testing.
