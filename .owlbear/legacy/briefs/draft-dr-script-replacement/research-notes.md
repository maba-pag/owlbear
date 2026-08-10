# Research Notes

## Verified Findings

### Engine Integration Surface
- `pick_tasks` lives at `serve/kanban/src/owlbear_kanban/engine.py:2270` — called via `AgentView.pick_tasks()`
- MCP wrapper at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:668` — simple pass-through, easy to add pre/post logic
- Tool registration uses `@mcp.tool()` decorator pattern — adding `create_dr` follows identical pattern to `create_task`
- Guidance field already exists in `PickTasksResponse` — can surface DR status there

### Blocking & Guidance Mechanism
- `guidance.py` in mcp-kanban generates the "Create a Decision Request" message when task is blocked
- Message currently says "via the scribe agent" — this is the text that changes to "via create_dr tool"
- `block:user` tag suppresses guidance (Cockpit-initiated blocks don't need DRs)
- Guidance is advisory text in the MCP response — not an automated dispatch

### DR File Operations (what the engine would absorb)
- Create: write markdown+frontmatter to `.owlbear/decisions/pending/{task_id}-{slug}.md`
- Resolve: scan pending/, read YAML frontmatter, classify `response` field, write to task body, move to resolved/
- Both are pure filesystem + kanban operations — no judgment

### Cockpit Backend
- Routes split into `routes/read.py` and `routes/mutation.py`
- Engine accessed via DI (`get_engine`)
- Adding DR endpoints follows existing patterns (FastAPI routes calling engine)

### Auto-Resolve Evidence
- Zero `response: auto-approved` entries in entire history
- Feature was specified but never triggered — dead code, safe to remove

## Candidate Implications

- DR resolve logic in `pick_tasks` means every `pick_tasks` call does a directory scan — should be fast (glob + stat) but needs to not slow down the hot path
- The guidance message text change is trivial but touches agent behavior (agents currently react to "via scribe agent" text)
- Cockpit status bar indicator needs a new API endpoint (`GET /api/decisions/status` or folded into `/api/board`)
- Format simplification is a non-breaking migration: new engine writes simplified format, reading code handles both old and new

## Open Research Questions (for Phase 2 mediator)

- Exact `create_dr` tool parameter shape: how many params minimize agent context while ensuring file completeness?
- Should resolve write a `## Decision Resolved` section to the task body (current behavior) or is the file in resolved/ sufficient?
- Cockpit resolve UX: inline edit in status bar popover, or separate page?
- Migration strategy for existing 35 resolved DR files (leave as-is, or reformat?)
