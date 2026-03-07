---
id: 546
title: Lazy-import QdrantVectorStore in knowledge __init__.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:49.8564762+01:00
updated: 2026-03-07T00:52:54.2733335+01:00
started: 2026-03-07T00:49:53.4894756+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-11: knowledge/__init__.py imports QdrantVectorStore at module level. Loads qdrant module even for graph/schema/chunker only usage. Move to lazy import. AC: import owlbear.memory.knowledge doesnt load qdrant. See docs/config-dependency-audit.md.

## Research (trivial)

N/A - trivial lazy import, following existing patterns.

**Findings:**
- Line 33: `from owlbear.memory.knowledge.qdrant import QdrantVectorStore` is eagerly imported
- Zero consumers use the re-export; all 8 call sites import directly from `owlbear.memory.knowledge.qdrant`  
- Existing pattern (bootstrap.py, benchmarks): function-body deferred import with `# noqa: PLC0415`  
- Codebase does NOT use PEP 562 `__getattr__` lazy imports anywhere

**Approach:**
1. Remove the eager import on line 33
2. Remove `QdrantVectorStore` from `__all__`  
3. No `__getattr__` needed - zero callers depend on the re-export
4. Verify: `import owlbear.memory.knowledge` should not load qdrant_client
