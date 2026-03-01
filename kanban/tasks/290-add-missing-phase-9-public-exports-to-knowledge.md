---
id: 290
title: Add missing phase-9 public exports to knowledge/__init__.py
status: archived
priority: important
created: 2026-03-01T02:00:06.0388696+01:00
updated: 2026-03-01T17:08:13.2216152+01:00
started: 2026-03-01T03:13:57.1865443+01:00
completed: 2026-03-01T17:08:13.2216152+01:00
tags:
    - phase-9
    - knowledge-graph
    - code
depends_on:
    - 289
class: standard
---

## Context
The phase-9 docs audit (task #289) identified that knowledge/__init__.py is missing exports for 11 public symbols added during phase-9.

## Acceptance Criteria

- [ ] Add imports and __all__ entries for: IngestPipeline, IngestResult, DocumentStatus, compute_content_hash (from ingest.py)
- [ ] Add imports and __all__ entries for: IntraDocGraphBuilder, GraphBuildResult (from graph_builder.py)
- [ ] Add imports and __all__ entries for: BgeM3EmbeddingProvider, EmbeddingProvider (from embeddings.py)
- [ ] Add imports and __all__ entries for: init_db (from schema.py)
- [ ] Add imports and __all__ entries for: TextChunker, Chunk (from chunker.py)
- [ ] Import groups follow existing pattern: one `from ... import (...)` block per source module, alphabetical within each block
- [ ] __all__ remains a single alphabetically-sorted list (append new symbols, re-sort)
- [ ] Existing imports and __all__ entries unchanged (no reordering, no removals of current 14 symbols)
- [ ] Add test function in tests/ asserting all 11 new symbols are accessible via `from owlbear.memory.knowledge import <symbol>`
- [ ] ruff clean, all existing tests pass

## Architecture notes

- Follow existing __init__.py pattern: one `from .module import (...)` block per source module, alphabetical __all__
- Include EmbeddingProvider protocol alongside BgeM3EmbeddingProvider -- consumers need the protocol for type annotations
- Do NOT add exports for dedup.py, intake.py, or reranker.py internals (YAGNI)
- Safe import chain: ingest.py pulls in intake.py (httpx/anyio -- already core deps), embeddings.py defers FlagEmbedding to method call, no heavy surprises
- 11 new symbols (alphabetical): BgeM3EmbeddingProvider, Chunk, compute_content_hash, DocumentStatus, EmbeddingProvider, GraphBuildResult, IngestPipeline, IngestResult, IntraDocGraphBuilder, TextChunker, init_db

## Out of scope

- reranker.py exports (separate concern)
- intake.py exports (internal pipeline detail)
- dedup.py exports (internal pipeline detail)
