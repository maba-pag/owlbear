---
id: 701
title: 'Research: Integrate always-on memory into OwlBear knowledge layer'
status: ideation
priority: important
created: 2026-03-08T18:40:17.618175+01:00
updated: 2026-03-08T18:40:17.618175+01:00
tags:
    - research
    - phase-research
    - scope:core
    - memory
    - knowledge
    - rag
depends_on:
    - 700
class: standard
---

## Goal
Assess integration paths for the always-on-memory-agent pattern into OwlBear's existing knowledge infrastructure (SQLite graph + Qdrant + BGE-M3 + RAG).

## Research Checklist

1. **Theoretical validity** - Does an always-on memory layer complement or conflict with our hybrid search (graph + vector)? Could it serve as a higher-level abstraction on top of our existing stores?
2. **Prior art** - How do other agent frameworks (LangGraph, CrewAI, AutoGen) implement persistent agent memory? Compare with the GCP approach.
3. **Technical feasibility** - What changes to KnowledgeService, GraphStore, or VectorStore would be needed? Can the memory layer sit alongside RAG without conflict?
4. **Architecture fit** - Map the GCP memory agent's components to OwlBear equivalents: what already exists, what's missing, what needs adaptation?
5. **Implementation approach** - Design sketch: where does the memory layer live in our architecture? How does it interact with existing knowledge injection (context-aware-knowledge-injection)?

## Acceptance Criteria
- [ ] Component mapping: GCP memory agent parts -> OwlBear equivalents
- [ ] Gap analysis: what's missing in OwlBear that the GCP pattern provides
- [ ] Integration design sketch (where it fits in src/owlbear/ module structure)
- [ ] Impact assessment on existing RAG pipeline and graph queries
- [ ] Decision: with-RAG vs without-RAG vs hybrid approach
- [ ] Research doc at docs/always-on-memory-integration-research.md
- [ ] Follow-up kanban tasks for implementation if recommended
