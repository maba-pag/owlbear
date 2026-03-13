---
id: 550
title: Trim knowledge __init__.py to 15 or fewer exports
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:53.2483718+01:00
updated: 2026-03-07T01:04:47.6777369+01:00
started: 2026-03-07T00:55:27.3565874+01:00
tags:
    - audit
    - architecture
    - knowledge
class: standard
---

INT-11: knowledge/__init__.py exports 35 symbols. Target <=15 public re-exports.

Research complete: see docs/research/knowledge-init-trim.md

**Recommended 14 exports:** Document, Edge, Entity, EntityType, RelationType, DocumentStatus, GraphStore, IngestPipeline, IngestResult, KnowledgeQueryService, BookmarkStore, EmbeddingProvider, VectorStoreProtocol, init_db

**Remove 21 symbols** (import from submodules instead): BgeM3EmbeddingProvider, Bookmark, BookmarkPipeline, BookmarkResult, BookmarkToolset, Chunk, Embedding, EntityExtractor, EvaluationResult, ExtractionResult, GraphAugmentedRetriever, GraphBuildResult, HybridEmbedding, InterDocGraphBuilder, IntraDocGraphBuilder, QdrantVectorStore, RetrievalResult, SourceEvaluator, SparseVector, TextChunker, compute_content_hash

**Only 1 production import changes:** bootstrap.py L291 TextChunker -> import from .chunker

AC: clean public API surface, <=15 re-exports in __all__.
