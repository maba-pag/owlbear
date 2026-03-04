---
id: 546
title: Lazy-import QdrantVectorStore in knowledge __init__.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:49.8564762+01:00
updated: 2026-03-04T07:38:49.8564762+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-11: knowledge/__init__.py imports QdrantVectorStore at module level. Loads qdrant module even for graph/schema/chunker only usage. Move to lazy import. AC: import owlbear.memory.knowledge doesnt load qdrant. See docs/config-dependency-audit.md.
