---
id: 1659
title: Cockpit Memory Tab — browse, filter, and manage agent memory entries
status: backlog
priority: important
created: 2026-05-18T17:40:16.810102+02:00
updated: 2026-05-18T17:44:43.651306+02:00
tags:
  - cockpit
  - memory
  - feature
parent:
depends_on:
  - 1673
ac:
  - serve/memory/ package exists with MemoryEngine exposing approve(), edit(), 
    delete() methods enforcing state machine transitions
  - serve/mcp-memory/ rewired to import from owlbear-memory; all existing MCP 
    tool tests pass
  - GET /api/memories returns all entries with parse_errors count; entries match
    MemoryEntry schema
  - POST approve/edit/delete mutations enforce OCC via expected_updated_at and 
    return correct HTTP status codes (404/409/422)
  - Frontend Memory tab renders list with state/category/agent filters and text 
    search (client-side)
  - Inline accordion detail shows full content (sanitized markdown) and metadata
    with state-dependent action buttons
  - Delete confirmation dialog for both hard-delete (pending) and soft-delete 
    (curated/approved)
  - Edit of approved entry shows inline warning and downgrades state to curated 
    on save
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Add a Memory tab to the cockpit providing full visibility and control over agent institutional memory. Includes engine extraction to a shared package, cockpit backend API, and React frontend component.

## Brief

See `.owlbear/briefs/draft-cockpit-memory-tab/brief.md` for the complete specification.

## Architecture Summary

1. Extract `serve/memory/` as shared engine package (MemoryEngine with mutation methods, models, state machine enforcement)
2. Rewire `serve/mcp-memory/` to depend on the new package (tools.py becomes thin adapter)
3. Add cockpit backend routes (`/api/memories`, approve/edit/delete mutations with OCC)
4. Add React frontend component (list + inline accordion detail + actions) — blocks on #1638

## Key Decisions

- D7: Extract engine first (prerequisite)
- D8: Split scope — backend now, frontend after #1638
- D9: No SSE in V1
- D10: Deleted entries excluded from default filter
- D11: No auto-commit
- D12: Lenient read, strict write

## Scope Split

- **Backend (independent):** Engine extraction + API routes
- **Frontend (blocks on #1638):** React component, filtering, accordion detail, actions

[[2026-05-18T17:44:43+02:00]]
## Planning
### Decomposition: Cockpit Memory Tab
- Tasks created: 7 (6 implementation + 1 consolidation)
- Dependency layers: 4
- Phases: P1 (engine extraction, 2 tasks) + P2 (rewire + API, 2 tasks) + P3 (frontend, 2 tasks) + consolidation

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1667 | P1-01: Memory engine package — models, errors, and storage primitives | critical | — | phase-1, scope:memory, backend |
| #1668 | P1-02: Memory engine — MemoryEngine with state machine, OCC, and caching | critical | #1667 | phase-1, scope:memory, backend |
| #1669 | P2-01: Rewire mcp-memory to import from owlbear-memory engine package | needed | #1668 | phase-2, scope:mcp-memory, backend |
| #1670 | P2-02: Cockpit backend API — memory routes with OCC | needed | #1668 | phase-2, scope:cockpit, backend |
| #1671 | P3-01: Memory list view with state/category/agent filters and text search | needed | #1670, #1639 | phase-3, scope:cockpit-web, frontend |
| #1672 | P3-02: Memory accordion detail and state-dependent actions | important | #1671 | phase-3, scope:cockpit-web, frontend |
| #1673 | Consolidation test: Cockpit Memory Tab | needed | #1667–#1672 | consolidation-test, scope:memory, scope:cockpit |

### Dependency Graph
```mermaid
graph TD
    P1_01["#1667 P1-01: Models + storage"]
    P1_02["#1668 P1-02: MemoryEngine"]
    P2_01["#1669 P2-01: Rewire mcp-memory"]
    P2_02["#1670 P2-02: Cockpit API routes"]
    P3_01["#1671 P3-01: Memory list view"]
    P3_02["#1672 P3-02: Accordion + actions"]
    CONSOL["#1673 Consolidation test"]
    EXT["#1639 Tab routing infra (external)"]

    P1_01 --> P1_02
    P1_02 --> P2_01
    P1_02 --> P2_02
    P2_02 --> P3_01
    EXT --> P3_01
    P3_01 --> P3_02

    P1_01 --> CONSOL
    P1_02 --> CONSOL
    P2_01 --> CONSOL
    P2_02 --> CONSOL
    P3_01 --> CONSOL
    P3_02 --> CONSOL
```

### Key Sequencing Decisions
- P1 (engine extraction) ships first — prerequisite for all downstream work
- P2-01 (mcp-memory rewire) and P2-02 (cockpit API) are independent siblings, both depend only on P1-02
- P3 frontend tasks depend on both the cockpit API (#1670) and the external tab infrastructure (#1639 from #1638)
- Parent #1659 depends on consolidation #1673 as completion gate
