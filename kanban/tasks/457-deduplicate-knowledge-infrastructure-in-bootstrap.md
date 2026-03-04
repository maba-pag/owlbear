---
id: 457
title: Deduplicate knowledge infrastructure in bootstrap
status: ideation
priority: critical
created: 2026-03-04T07:37:37.7196664+01:00
updated: 2026-03-04T07:37:37.7196664+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-01/DRY-01/F-01/C-2/INT-02: _build_knowledge_toolset and _build_bookmark_toolset each create independent SQLite connections, BgeM3EmbeddingProvider (~3GB each), QdrantVectorStore, GraphStore, EntityExtractor, TextChunker, IngestPipeline. Extract shared KnowledgeInfrastructure dataclass built once. AC: single SQLite conn, single BgeM3 instance, single QdrantVectorStore shared. See docs/architecture-audit.md, docs/software-design-audit.md, docs/resilience-audit.md.
