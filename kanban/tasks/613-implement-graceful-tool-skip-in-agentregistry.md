---
id: 613
title: Implement graceful tool skip in AgentRegistry._build_agent
status: archived
priority: critical
created: 2026-03-07T05:19:07.963959+01:00
updated: 2026-03-07T18:08:20.9210357+01:00
started: 2026-03-07T05:33:09.2024205+01:00
completed: 2026-03-07T18:08:20.9210357+01:00
tags:
    - bugfix
    - config
    - phase-9
depends_on:
    - 612
class: standard
---

## TDD Green Phase for #611

Change the list comprehension in `_build_agent` to a loop with try/except KeyError.

## AC

- [ ] In `AgentRegistry._build_agent` (`src/owlbear/core/agent_registry.py` ~L172-174): replace list comprehension with for-loop that catches KeyError per tool
- [ ] Each caught KeyError logs: `logger.warning("Agent %r: skipping unavailable tool %r", defn.name, tool_name)`
- [ ] Agent instantiated with only the successfully resolved toolsets
- [ ] All tests from #612 pass (TDD green)
- [ ] All existing tests in `test_agent_registry.py` pass
- [ ] All existing tests in `test_pipeline_e2e.py` pass
- [ ] `uv run ruff check src/owlbear/core/agent_registry.py` clean

## Implementation (from research doc S4)

In `_build_agent`, replace:

```python
toolsets: list[AbstractToolset] = [
    self._resolve_tool(tool_name) for tool_name in defn.tools
]
```

With:

```python
toolsets: list[AbstractToolset] = []
for tool_name in defn.tools:
    try:
        toolsets.append(self._resolve_tool(tool_name))
    except KeyError:
        logger.warning(
            "Agent %r: skipping unavailable tool %r",
            defn.name, tool_name,
        )
```
