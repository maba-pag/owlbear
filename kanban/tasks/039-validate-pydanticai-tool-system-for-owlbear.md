---
id: 39
title: Validate PydanticAI tool system for OwlBear
status: archived
priority: high
created: 2026-02-26T15:56:45.8638593+01:00
updated: 2026-02-27T10:00:12.506693+01:00
started: 2026-02-26T19:41:17.4910157+01:00
completed: 2026-02-27T10:00:12.506693+01:00
tags:
    - phase-2
    - agent
    - tooling
depends_on:
    - 37
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.1)

PydanticAI provides: Tool class, @tool decorator, ToolDefinition, RunContext for DI, FunctionToolset, AbstractToolset, and 9 toolset variants (FilteredToolset, PrefixedToolset, etc.). Building our own Tool ABC would duplicate all of this.

**Decision:** DO NOT build a custom Tool ABC or ToolRegistry. Use PydanticAI's @tool decorator and FunctionToolset.

**Remaining work:**
- Write smoke tests proving @tool decorator and FunctionToolset work for OwlBear use cases
- Document the PydanticAI tool patterns in copilot-instructions.md
- Create one example OwlBear tool to validate the pattern

## AC (revised)
Smoke tests proving PydanticAI's tool system works for OwlBear. Example tool implementation. Tool pattern documented.
