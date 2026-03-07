---
id: 518
title: Extract shared _emit_hook into module-level utility in hooks.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:28.1302217+01:00
updated: 2026-03-07T00:01:32.9344452+01:00
started: 2026-03-06T23:58:22.7337926+01:00
tags:
    - audit
    - dry
    - refactor
    - tools
class: standard
---

DRY-02/F-10: _emit_hook identical 4-line method in git_local.py, kanban.py, github_api.py + inline variant in terminal.py.

Research checklist 1-3: N/A -- trivial DRY extraction of 4-line method, 4 copies.

## Findings

**Scope:** 4 toolsets store `_hooks: HookRegistry | None` and guard+emit PRE_TOOL_USE:

- git_local.py L87-93 (method)
- kanban.py L88-94 (method)
- github_api.py L119-125 (method)
- terminal.py L165-169 (inline in run_command)

All 3 method copies are character-identical. The terminal.py variant is the same logic inlined.

**Decision: module-level utility in hooks.py (not mixin)**

| Criterion | Module-level fn (.90) | HookMixin (.55) |
|---|---|---|
| Simplicity | 4-line free fn, no class | New class in MRO |
| MRO risk | None | Diamond with FunctionToolset |
| Import cost | Already import hooks.py | New module or hooks.py change |
| Call-site change | `emit_pre_tool_use(self._hooks, ...)` | `self._emit_hook(...)` unchanged |
| KISS/YAGNI | High | Medium |

Add `async def emit_pre_tool_use(hooks, tool_name, args)` to `hooks.py`. All 4 toolsets call it and delete their local copy/inline.

## AC

- [ ] Single `emit_pre_tool_use()` in `hooks.py`; no `_emit_hook` methods remain
- [ ] terminal.py uses the same utility (not inlined)
- [ ] All existing hook tests pass
- [ ] Ruff clean

See docs/software-design-audit.md DRY-02, docs/code-quality-audit.md F-10.
