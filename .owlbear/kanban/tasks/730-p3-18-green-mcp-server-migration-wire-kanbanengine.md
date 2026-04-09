---
id: 730
title: 'P3-18: GREEN — MCP server migration (wire KanbanEngine into server.py)'
status: backlog
priority: critical
created: 2026-04-09T03:28:46.4629227+02:00
updated: 2026-04-09T03:28:46.4629227+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 729
class: standard
---

## Objective
Replace _run_kanban() subprocess calls in server.py with KanbanEngine method calls. Update AppContext and lifespan. This is the atomic switchover — the existing server must work until this task completes.

Brief: see parent #712 — Phase 2

## AC
- [ ] AppContext holds KanbanEngine instance instead of kanban_bin Path
- [ ] Lifespan creates KanbanEngine(kanban_dir), no binary existence check
- [ ] `_run_kanban()` function removed
- [ ] Each MCP tool delegates to equivalent KanbanEngine method
- [ ] Lean list transform preserved (strip body/created/updated/class, synthesize claimed bool)
- [ ] pick_tasks gate logic preserved (reads body for AC pattern and TDD gate)
- [ ] Tool exclusion (KANBAN_TOOLS_EXCLUDE) still works
- [ ] outputSchema patches preserved
- [ ] All #729 tests pass
- [ ] All existing MCP kanban tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (major edit)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/__init__.py` (edit if needed)
