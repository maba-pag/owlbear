---
id: 356
title: Fix QdrantVectorStore bootstrap param mismatch
status: archived
priority: critical
created: 2026-03-01T18:12:34.3541802+01:00
updated: 2026-03-02T09:14:26.9763846+01:00
started: 2026-03-01T18:13:00.9647324+01:00
completed: 2026-03-02T09:14:26.9763846+01:00
tags:
    - phase-12
    - bugfix
    - knowledge-graph
class: standard
---

## Context
bootstrap._build_knowledge_toolset() passes storage_path= to QdrantVectorStore.__init__() which expects location=. This causes KnowledgeToolset to silently fail on every daemon boot.

## Acceptance Criteria
- [ ] bootstrap.py uses location= instead of storage_path= for QdrantVectorStore
- [ ] Existing tests still pass
- [ ] Integration smoke test: _build_knowledge_toolset returns a valid toolset

## Root Cause
Line 275 of bootstrap.py: QdrantVectorStore(storage_path=...) should be QdrantVectorStore(location=...)
