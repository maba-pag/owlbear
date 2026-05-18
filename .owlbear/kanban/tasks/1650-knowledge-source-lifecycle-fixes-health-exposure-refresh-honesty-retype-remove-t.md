---
id: 1650
title: Knowledge source lifecycle fixes — health exposure, refresh honesty, 
  retype, remove tool
status: backlog
priority: important
created: 2026-05-18T03:05:20.577820+02:00
updated: 2026-05-18T03:11:44.724517+02:00
tags:
  - knowledge
  - mcp-tools
  - parent
parent:
depends_on:
  - 1655
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief

See `.owlbear/briefs/draft-knowledge-source-lifecycle/brief.md`

## Summary

4 focused fixes to the knowledge source surface:

- **O1:** Expose source health in `list_sources` (5 new fields: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`)
- **O2:** Fix refresh honesty — two-field timestamp model (`last_checked_at` + `last_refreshed_at`) with conditional update logic
- **O3:** Retype direct-ingest HTTP sources from `AUTHENTICATED_WEB` to `URL_LIST` (gated on handler equivalence)
- **O4:** Add `remove_source` MCP tool with vectors-first abort-on-failure cascade

## Implementation Order

O2 → O1 → O4 → O3

## Key Constraints

- No `config` in `list_sources` (leak risk)
- Raw error strings (no sanitization)
- `remove_source` aborts if Qdrant cleanup fails
- O3 drops if handler equivalence fails

[[2026-05-18T03:11:44+02:00]]
## Planning
### Decomposition: Knowledge source lifecycle fixes
- Tasks created: 5
- Dependency layers: 3
- Phase: P1

### Task List
| ID | Title | Priority | Depends On | Tags | Proof |
|----|-------|----------|------------|------|-------|
| #1651 | P1-01: Refresh honesty — two-field timestamp model | critical | — | scope:knowledge, knowledge | behavioral |
| #1654 | P1-02: Expose source health in list_sources | needed | #1651 | scope:mcp-knowledge, mcp-tools | behavioral |
| #1652 | P1-03: Add remove_source MCP tool with vectors-first abort | needed | — | scope:mcp-knowledge, mcp-tools | behavioral |
| #1653 | P1-04: Verify handler equivalence for URL_LIST retype | important | — | scope:knowledge, research | skip |
| #1655 | Consolidation test: knowledge source lifecycle | needed | #1651, #1654, #1652 | scope:knowledge, scope:mcp-knowledge, consolidation-test | behavioral |

### Dependency Graph
```mermaid
graph TD
  1651[\"#1651 O2: Refresh honesty\"] --> 1654[\"#1654 O1: Health in list_sources\"]
  1651 --> 1655[\"#1655 Consolidation test\"]
  1654 --> 1655
  1652[\"#1652 O4: remove_source tool\"] --> 1655
  1653[\"#1653 O3: Handler equivalence research\"]
  1655 --> 1650[\"#1650 Parent\"]
```

### Notes
- O2 (#1651) is critical path — O1 depends on it for `last_checked_at` field
- O4 (#1652) can develop in parallel with O2/O1
- O3 research (#1653) is independent; creates conditional follow-up impl task if handler equivalence holds
- Consolidation test (#1655) moved to backlog and gates parent completion
