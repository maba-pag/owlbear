---
id: 701
title: 'Research: Integrate always-on memory into OwlBear knowledge layer'
status: backlog
priority: important
created: 2026-03-08T18:40:17.618175+01:00
updated: 2026-03-10T02:44:00.0755788+01:00
started: 2026-03-09T23:04:21.6699698+01:00
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

[[2026-03-09]] Mon 23:12
## Research
doc: docs/research/always-on-memory-integration-research.md

### Key Findings
- Component mapping complete: 11 GCP components mapped to OwlBear equivalents
- 4 gaps identified: periodic consolidation, insight storage, importance scoring, consolidated flag
- Hybrid approach recommended (.80): keep existing RAG + add consolidation as enrichment layer
- Previous MemoryConsolidator (#485) was YAGNI for *session* summaries; this targets *knowledge* consolidation  different scope
- 8 sources studied, 2+ per claim

### Follow-up Tasks
```
kanban\kanban-md.exe create "Schema v8: add importance, consolidated, consolidations table" --priority needed --status backlog --tag "scope:core,memory,knowledge,schema"
kanban\kanban-md.exe create "Add importance scoring to EntityExtractor" --priority needed --status backlog --tag "scope:core,memory,knowledge"
kanban\kanban-md.exe create "Implement ConsolidationService (feature-flagged)" --priority nice-to-have --status backlog --tag "scope:core,memory,knowledge,consolidation"
```

[[2026-03-09]] Mon 23:12
## Research
doc: docs/research/always-on-memory-integration-research.md

### Key Findings
- Component mapping complete: 11 GCP components mapped to OwlBear equivalents
- 4 gaps identified: periodic consolidation, insight storage, importance scoring, consolidated flag
- Hybrid approach recommended (.80): keep existing RAG + add consolidation as enrichment layer
- Previous MemoryConsolidator (#485) was YAGNI for *session* summaries; this targets *knowledge* consolidation  different scope
- 8 sources studied, 2+ per claim

### Follow-up Tasks
```
kanban\kanban-md.exe create "Schema v8: add importance, consolidated, consolidations table" --priority needed --status backlog --tag "scope:core,memory,knowledge,schema"
kanban\kanban-md.exe create "Add importance scoring to EntityExtractor" --priority needed --status backlog --tag "scope:core,memory,knowledge"
kanban\kanban-md.exe create "Implement ConsolidationService (feature-flagged)" --priority nice-to-have --status backlog --tag "scope:core,memory,knowledge,consolidation"
```

[[2026-03-10]] Tue 02:43
## Architecture Review
VERDICT: REFINE

AC 1-6: PASS (research quality solid, 8 sources, codebase patterns verified)
AC 7: FAIL -- follow-up tasks NOT created (commands listed in body but never executed, verified via --tag filters)

Research architecture is sound: Entity model lacks importance (G3 confirmed), schema v7 has no consolidated flag (G4 confirmed), GraphEnricher is correct pattern for ConsolidationService, YAGNI guard with feature flag is appropriate.

Action needed: execute the 3 kanban-md create commands from research doc section 8.
