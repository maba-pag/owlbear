---
id: 370
title: 'Update #136 AC: bookmark tools target server.py not tools.py'
status: archived
priority: medium
created: 2026-03-30 20:46:21.911180+02:00
updated: 2026-04-04 07:09:56.296915+02:00
started: 2026-04-04 07:09:30.646974+02:00
completed: 2026-04-04 07:09:30.646974+02:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
- chore
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Task #136 AC line 4 references `packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py` for bookmark_source and list_bookmarks registration. This file is being deleted by #223. Update the AC to register bookmark tools as `@mcp.tool()` decorators in `server.py`, following the v2 pattern established by #152.

## Acceptance Criteria
- [ ] Task #136 AC line "bookmark_source and list_bookmarks registered as MCP tools in packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py" updated to reference server.py
- [ ] AppContext extension AC updated to match server.py pattern (lifespan_context, not standalone AppContext)

## Context
See docs/research/dead-code-mcp-knowledge-tools.md §3.3. tools.py was the v1 approach (#72); server.py is the v2 pattern (#152). Task #223 deletes tools.py.

[[2026-04-03]] Fri 00:25
## Architecture Review
**Verdict:** BLOCK (duplicate of #520)
**DR Verification:** N/A

### AC Assessment
AC1 (Update #136 tools.py ref to server.py): Identical to #520 AC1 -- Duplicate
AC2 (AppContext extension AC update): Identical to #520 AC2 -- Duplicate

### Architecture Notes
Task #370 is a duplicate of #520. Task #520 was created during the architect review of #223, and #370 was explicitly merged into #520 (see #520 body). The merge noted Deleted #370 but the deletion did not execute, leaving #370 as a zombie duplicate.

#520 is already at todo with a full Architecture Review (APPROVED, confidence .92), refined AC covering all of #370 scope plus an additional dependency guard (AC4: add depends_on 223 to #136).

Action: Block #370 to ideation. The planner should archive or delete this duplicate. All work proceeds through #520.
