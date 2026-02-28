---
id: 161
title: Extend OwlBearDeps with agent_registry and delegation_depth
status: archived
priority: needed
created: 2026-02-27T19:20:55.4498498+01:00
updated: 2026-02-28T23:53:15.8126738+01:00
started: 2026-02-27T19:21:00.881157+01:00
completed: 2026-02-28T23:53:15.8126738+01:00
tags:
    - phase-8
    - agent
    - core
depends_on:
    - 129
class: standard
---

Extend OwlBearDeps dataclass to support agent delegation.
Prerequisite for #130 (delegation).

## AC
- [ ] Add to OwlBearDeps in src/owlbear/core/deps.py:
      - agent_registry: AgentRegistry | None = None (TYPE_CHECKING import)
      - _delegation_depth: int = 0 (underscore prefix: internal, not user-facing)
- [ ] Both fields have defaults (backwards-compatible — no existing code breaks)
- [ ] Update core/__init__.py if needed
- [ ] Tests:
      - OwlBearDeps() with no args still works (defaults)
      - OwlBearDeps(agent_registry=mock, _delegation_depth=2) constructs correctly
      - dataclasses.replace(deps, _delegation_depth=3) works
      - Existing OwlBearDeps tests still pass
- [ ] ruff clean

## Architecture
- Keep deps minimal: agent_registry is Optional because not all agents need delegation
- _delegation_depth is internal bookkeeping for recursion prevention
- Uses TYPE_CHECKING import for AgentRegistry to avoid circular imports
