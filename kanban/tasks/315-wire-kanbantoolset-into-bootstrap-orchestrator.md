---
id: 315
title: Wire KanbanToolset into bootstrap + orchestrator definition
status: archived
priority: critical
created: 2026-03-01T06:23:50.0831657+01:00
updated: 2026-03-01T17:09:40.554349+01:00
started: 2026-03-01T09:50:07.3610991+01:00
completed: 2026-03-01T17:09:40.554349+01:00
tags:
    - phase-12
    - agent
    - orchestrator
depends_on:
    - 314
class: standard
---

Wiring task for #301. Register KanbanToolset and update agent definitions.

## Acceptance Criteria

- [ ] `bootstrap.py`: import `KanbanToolset` from `owlbear.tools.kanban`
- [ ] `build_toolsets()`: add `KanbanToolset(kanban_dir=workspace / 'kanban', hooks=hooks)` to `raw` list (wrapped in `HookedToolset` like other toolsets)
- [ ] `orchestrator.md` YAML frontmatter: add `KanbanToolset` to `tools` list
- [ ] `test_bootstrap.py TestBuildToolsets`: assert `KanbanToolset` appears in toolset type names
- [ ] `test_agent_definitions.py EXPECTED_AGENTS['orchestrator']['tools']`: updated to include `KanbanToolset`
- [ ] Pre-existing tool name resolution: verify short name vs class name mapping works. If agent definitions use short names (`delegation`, `filesystem`) and resolver maps by class name, either fix the resolver to support aliases or use the class name `KanbanToolset` consistently. Document which convention is used.
- [ ] All existing tests pass (no regressions)
- [ ] ruff clean

## Architecture Notes

`build_toolsets()` pattern: append to `raw` list before the `HookedToolset` wrapping loop. `build_agent_registry()` maps by `type(inner).__name__`, so the orchestrator.md tools entry must match how the resolver indexes it. Currently there is a pre-existing mismatch (agent defs use short names like `delegation` but resolver maps by class name `DelegationToolset`). The builder must investigate and resolve for KanbanToolset specifically.
