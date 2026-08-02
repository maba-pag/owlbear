---
id: 120
title: Add __main__.py entry points to mcp-knowledge and mcp-project
status: archived
priority: medium
created: 2026-03-29 06:32:41.471337+02:00
updated: 2026-03-29 11:10:02.362458+02:00
started: 2026-03-29 11:10:02.362458+02:00
completed: 2026-03-29 11:10:02.362458+02:00
tags:
- phase-1
- scope:mcp
- type:build
depends_on:
- 119
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add __main__.py files to owlbear_mcp_knowledge and owlbear_mcp_project packages so they can be started via python -m.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/src/owlbear_mcp_knowledge/__main__.py exists with FastMCP entry point
- [ ] packages/mcp-project/src/owlbear_mcp_project/__main__.py exists with FastMCP entry point
- [ ] uv run -m owlbear_mcp_knowledge starts without import error
- [ ] uv run -m owlbear_mcp_project starts without import error
- [ ] Both packages list mcp[cli] as a dependency (like mcp-kanban)

## Context
See docs/research/mcp-server-registry.md section 3.2. Only mcp-kanban currently has __main__.py. The other two are stubs but need at least a minimal MCP server instance to avoid startup errors.

[[2026-03-29]] Sun 10:28
## Research
doc: docs/research/mcp-entry-points-overlap.md

Key findings:
- #120 AC overlaps with #54 (mcp-knowledge server+main) and #17 (mcp-project server+main)
- Only non-overlapping gap: mcp[cli] dependency in pyproject.toml
- Stub server.py approach rejected: conflicts with existing RED tests from #104
- Recommendation (.80): merge #120 into #54 and #17, close as subsumed
- Follow-up created: #133 (add mcp[cli] dep to both pyproject.toml files)

Architect action needed: add mcp[cli]>=1.26 to AC of #54 and #17, then close #120 as subsumed.

[[2026-03-29]] Sun 11:09
## Architecture Review
**Verdict:** MERGE (delete as subsumed)

### AC Assessment
| # | AC Line | Covered By | Evidence |
|---|---------|------------|----------|
| 1 | mcp-knowledge __main__.py | #54 AC7 | __main__.py exists and calls mcp.run() |
| 2 | mcp-project __main__.py | #17 AC7 | Server communicates via stdio transport |
| 3 | uv run -m starts (knowledge) | #54 AC8-9 | Tests pass GREEN implies runnable |
| 4 | uv run -m starts (project) | #17 full build | Working server implies runnable |
| 5 | mcp[cli] dependency | #133 | Standalone task at ideation |

### Architecture Notes
All five AC lines in #120 are covered by existing tasks. Research doc confirms overlap at .80 confidence. Verified codebase: mcp-knowledge has only tools.py, mcp-project has only models.py. Both gaps addressed by #54 and #17. Reference pattern: mcp-kanban __main__.py is 8 lines calling mcp.run(). Note for future #17 review: add explicit __main__.py AC line.

### Changes Made
- Deleted #120 as fully subsumed by #54, #17, #133

### Dependencies
- #54 (mcp-knowledge server): covers AC1, AC3
- #17 (mcp-project server): covers AC2, AC4
- #133 (mcp[cli] dep): covers AC5
