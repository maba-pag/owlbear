---
id: 531
title: Add TypedDict for tool_stats return type
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:36.8877228+01:00
updated: 2026-03-07T00:27:11.9185391+01:00
started: 2026-03-07T00:26:11.7431131+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

## Research
N/A - trivial TypedDict definition.

### Inner dict keys (from `EventStore.tool_stats()` in `observability.py:119-148`)
- `call_count: int` - incremented per post_tool_use event
- `error_count: int` - incremented when `not e.success`
- `avg_duration_ms: float` - computed average, defaults to 0.0

### Implementation
Define `ToolStats(TypedDict)` in `observability.py`, change return annotation to `dict[str, ToolStats]`.
No logic changes needed - dict literals already match the shape.

### AC
- [ ] `ToolStats` TypedDict defined with 3 keys
- [ ] `tool_stats()` return type is `dict[str, ToolStats]`
- [ ] Existing tests still pass
- [ ] ruff clean
