---
id: 284
title: Implement IntraDocGraphBuilder -- cross-chunk relationship inference
status: archived
priority: needed
created: 2026-02-28T22:57:43.4880746+01:00
updated: 2026-03-01T17:09:12.7317603+01:00
started: 2026-02-28T23:12:23.3498328+01:00
completed: 2026-03-01T17:09:12.7317603+01:00
tags:
    - phase-9
    - knowledge-graph
    - agent
depends_on:
    - 283
    - 285
class: standard
---

Core intra-document graph builder using PydanticAI.
AC:
- [ ] New module graph_builder.py with IntraDocGraphBuilder class
- [ ] PydanticAI agent with ExtractionResult output
- [ ] Single LLM call per document (batch by entity_type if >80 entities)
- [ ] Edges stored with weight=0.5 and metadata.source=intra_doc_inference
- [ ] Constrained to existing RelationType enum
- [ ] Returns GraphBuildResult with edges_added count
Depends on #283
See docs/research/intra-document-graph.md
