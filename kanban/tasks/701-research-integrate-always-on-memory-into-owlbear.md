---
id: 701
title: 'Research: Integrate always-on memory into OwlBear knowledge layer'
status: archived
priority: important
created: 2026-03-08T18:40:17.618175+01:00
updated: 2026-03-10T22:36:05.1710136+01:00
started: 2026-03-09T23:04:21.6699698+01:00
completed: 2026-03-10T22:36:05.1710136+01:00
tags:
    - research
    - phase-research
    - scope:core
    - memory
    - knowledge
    - rag
depends_on:
    - 700
claimed_by: auditor
claimed_at: 2026-03-10T22:35:51.2843986+01:00
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
- [ ] Research doc at docs/research/always-on-memory-integration.md
- [ ] Follow-up kanban tasks for implementation if recommended

[[2026-03-09]] Mon 23:12
## Research
doc: docs/research/always-on-memory-integration.md

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
doc: docs/research/always-on-memory-integration.md

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

[[2026-03-10]] Tue 17:12
## Architecture Review (2nd cycle)
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Component mapping: GCP -> OwlBear | PASS -- 11-row table in Â§3, codebase-verified (Entity lacks importance, schema v7 lacks consolidated) | None |
| 2. Gap analysis | PASS -- 4 gaps in Â§4 with value/effort estimates, all codebase-confirmed | None |
| 3. Integration design sketch | PASS -- Â§5 module layout, ConsolidationService follows GraphEnricher pattern (enrichment.py:26) | None |
| 4. Impact assessment on RAG pipeline | PASS -- Â§5d, 4-row impact table with risk levels | None |
| 5. Decision: with-RAG vs without-RAG vs hybrid | PASS -- Â§6, hybrid recommended at .80 confidence with sound YAGNI guard | None |
| 6. Research doc at docs/research/always-on-memory-integration.md | PASS -- exists at docs/research/always-on-memory-integration.md | None |
| 7. Follow-up kanban tasks for implementation | **FAIL (2nd cycle)** -- 3 kanban-md create commands in Â§8 still not executed. Zero tasks with tags schema/consolidation on the board. | Researcher MUST execute the 3 commands from Â§8 |

### Architecture Notes
Research quality is strong and architecturally sound. All codebase claims verified:
- Entity model (models.py:77) correctly identified as lacking importance
- Schema at v7 (schema.py:21) correctly identified as lacking consolidated flag
- GraphEnricher (enrichment.py:26) is the right pattern model for ConsolidationService
- Hybrid approach (.80) is the correct call -- preserves existing RAG, adds consolidation as enrichment
- YAGNI guard (feature-flag ConsolidationService, nice-to-have priority) is appropriate given #485 history

The only remaining blocker is executing the follow-up task creation commands. This is the second cycle with the same finding.

### Changes Made
- No kanban edits -- same refinement as prior review cycle.

### Dependencies
- #700 (GCP always-on-memory-agent research): backlog, no blocking dependency
- Follow-up tasks (once created): Schema v8 is a prereq for importance scoring and ConsolidationService

[[2026-03-10]] Tue 17:12
## Architecture Review (2nd cycle)
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Component mapping: GCP -> OwlBear | PASS -- 11-row table in Â§3, codebase-verified (Entity lacks importance, schema v7 lacks consolidated) | None |
| 2. Gap analysis | PASS -- 4 gaps in Â§4 with value/effort estimates, all codebase-confirmed | None |
| 3. Integration design sketch | PASS -- Â§5 module layout, ConsolidationService follows GraphEnricher pattern (enrichment.py:26) | None |
| 4. Impact assessment on RAG pipeline | PASS -- Â§5d, 4-row impact table with risk levels | None |
| 5. Decision: with-RAG vs without-RAG vs hybrid | PASS -- Â§6, hybrid recommended at .80 confidence with sound YAGNI guard | None |
| 6. Research doc at docs/research/always-on-memory-integration.md | PASS -- exists at docs/research/always-on-memory-integration.md | None |
| 7. Follow-up kanban tasks for implementation | **FAIL (2nd cycle)** -- 3 kanban-md create commands in Â§8 still not executed. Zero tasks with tags schema/consolidation on the board. | Researcher MUST execute the 3 commands from Â§8 |

### Architecture Notes
Research quality is strong and architecturally sound. All codebase claims verified:
- Entity model (models.py:77) correctly identified as lacking importance
- Schema at v7 (schema.py:21) correctly identified as lacking consolidated flag
- GraphEnricher (enrichment.py:26) is the right pattern model for ConsolidationService
- Hybrid approach (.80) is the correct call -- preserves existing RAG, adds consolidation as enrichment
- YAGNI guard (feature-flag ConsolidationService, nice-to-have priority) is appropriate given #485 history

The only remaining blocker is executing the follow-up task creation commands. This is the second cycle with the same finding.

### Changes Made
- No kanban edits -- same refinement as prior review cycle.

### Dependencies
- #700 (GCP always-on-memory-agent research): backlog, no blocking dependency
- Follow-up tasks (once created): Schema v8 is a prereq for importance scoring and ConsolidationService

[[2026-03-10]] Tue 18:31
## Architecture Review (3rd cycle)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Component mapping: GCP -> OwlBear | PASS -- 11-row table in sec.3, codebase-verified | None |
| 2. Gap analysis | PASS -- 4 gaps in sec.4 with value/effort estimates | None |
| 3. Integration design sketch | PASS -- sec.5 module layout, follows GraphEnricher pattern | None |
| 4. Impact assessment on RAG pipeline | PASS -- sec.5d, 4-row impact table | None |
| 5. Decision: with-RAG vs without-RAG vs hybrid | PASS -- sec.6, hybrid at .80 confidence | None |
| 6. Research doc | PASS -- exists at docs/research/always-on-memory-integration.md | None |
| 7. Follow-up kanban tasks | PASS -- #721 (Schema v8), #722 (importance scoring), #723 (ConsolidationService) now exist on board | None |

### Architecture Notes
All 7 ACs now satisfied. Research quality confirmed solid in prior reviews (8 sources, codebase claims verified). Follow-up tasks created since 2nd cycle resolved the only remaining blocker.

### Changes Made
- Moved #701 backlog -> todo

### Dependencies
- #700 (GCP always-on-memory-agent research): docs status, not blocking
- Follow-up tasks #721, #722, #723 in backlog awaiting their own arch review

[[2026-03-10]] Tue 18:31
## Architecture Review (3rd cycle)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Component mapping: GCP -> OwlBear | PASS -- 11-row table in sec.3, codebase-verified | None |
| 2. Gap analysis | PASS -- 4 gaps in sec.4 with value/effort estimates | None |
| 3. Integration design sketch | PASS -- sec.5 module layout, follows GraphEnricher pattern | None |
| 4. Impact assessment on RAG pipeline | PASS -- sec.5d, 4-row impact table | None |
| 5. Decision: with-RAG vs without-RAG vs hybrid | PASS -- sec.6, hybrid at .80 confidence | None |
| 6. Research doc | PASS -- exists at docs/research/always-on-memory-integration.md | None |
| 7. Follow-up kanban tasks | PASS -- #721 (Schema v8), #722 (importance scoring), #723 (ConsolidationService) now exist on board | None |

### Architecture Notes
All 7 ACs now satisfied. Research quality confirmed solid in prior reviews (8 sources, codebase claims verified). Follow-up tasks created since 2nd cycle resolved the only remaining blocker.

### Changes Made
- Moved #701 backlog -> todo

### Dependencies
- #700 (GCP always-on-memory-agent research): docs status, not blocking
- Follow-up tasks #721, #722, #723 in backlog awaiting their own arch review

[[2026-03-10]] Tue 19:55
## Test-Writer Notes
Non-implementation task (tagged research) -- no tests applicable. Passing through to builder.

[[2026-03-10]] Tue 20:42
## Builder Notes
- Non-implementation research task, no code changes
- Verified: research doc exists, follow-up tasks #721 #722 #723 on board
- All 7 ACs PASS per 3rd architecture review

[[2026-03-10]] Tue 22:35
## Audit

[[2026-03-10]] Tue 22:35
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| 1. Component mapping | doc sec.3: 11-row table, GCP->OwlBear | PASS |
| 2. Gap analysis | doc sec.4: 5 covered + 4 gaps (G1-G4) | PASS |
| 3. Design sketch | doc sec.5a-5c: module layout, ConsolidationService, schema v8 | PASS |
| 4. RAG impact | doc sec.5d: 4-row impact table with risk levels | PASS |
| 5. Decision | doc sec.6: hybrid at .80, 3-option comparison | PASS |
| 6. Research doc | docs/research/always-on-memory-integration.md exists | PASS |
| 7. Follow-up tasks | #721 #722 #723 in backlog (committed 95ee70e) | PASS |

### Test Results
- pytest: 820 passed, 63 pre-existing failures (bootstrap/browser modules)
- ruff: 2 pre-existing I001 in test_bootstrap_structure.py

### Confidence: .97
### Action: archive

-t
