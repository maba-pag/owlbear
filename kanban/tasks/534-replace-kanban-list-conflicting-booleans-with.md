---
id: 534
title: Replace kanban_list conflicting booleans with block_filter enum
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:39.627003+01:00
updated: 2026-03-07T00:31:11.903033+01:00
started: 2026-03-07T00:29:36.3343606+01:00
tags:
    - audit
    - code-quality
    - tools
class: standard
---

F-24: kanban_list has blocked/not_blocked/unblocked as 3 mutually exclusive booleans. LLM may set conflicting flags. Replace with single block_filter: Literal['blocked','not_blocked','unblocked'] | None. AC: single filter param, no conflicts. See docs/code-quality-audit.md.

## Research (trivial)

N/A - trivial parameter consolidation.

- **Current:** 3 bool params (blocked, not_blocked, unblocked) each map to a CLI flag (--blocked, --not-blocked, --unblocked).
- **Problem:** LLM can set multiple=True simultaneously; flags are mutually exclusive in kanban-md CLI.
- **Fix:** Replace with block_filter: Literal['blocked','not_blocked','unblocked'] | None = None. Map value to --{value} CLI flag.
- **Files:** src/owlbear/tools/kanban.py (tool def), tests/test_kanban_tools.py (3 filter tests + no-filter test).
- **Scope:** ~15 lines changed in tool, ~10 lines changed in tests.
