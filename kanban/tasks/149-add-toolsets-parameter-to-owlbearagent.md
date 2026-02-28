---
id: 149
title: Add toolsets parameter to OwlBearAgent
status: archived
priority: critical
created: 2026-02-27T15:45:57.199224+01:00
updated: 2026-02-28T23:53:08.4542766+01:00
started: 2026-02-27T16:19:32.1409319+01:00
completed: 2026-02-28T23:53:08.4542766+01:00
tags:
    - phase-7
    - agent
    - config
class: standard
---

Prerequisite for #122 (bearclaw chat). OwlBearAgent.__init__ creates Agent(model, instructions=...) but does not forward toolsets. The chat REPL needs to pass FileToolset, TerminalToolset, and SkillRegistry to the inner Agent.

## AC

- [ ] OwlBearAgent.__init__ accepts optional toolsets: Sequence[AbstractToolset] | None = None
- [ ] Forward toolsets to inner Agent(model, instructions=..., toolsets=toolsets or [])
- [ ] When toolsets is None or empty, Agent created with no toolsets (current behavior preserved)
- [ ] Existing tests still pass (no behavioral change for callers that omit toolsets)
- [ ] New test: construct OwlBearAgent with a FunctionToolset, verify inner.toolsets is set
- [ ] New test: construct without toolsets, verify backward compatibility
- [ ] ruff clean

## Architecture Notes

- ~10 LOC diff in src/owlbear/core/agent.py
- Import AbstractToolset from pydantic_ai.toolsets.abstract (TYPE_CHECKING only)
- Follow existing pattern: optional param with None default
- TDD: write tests first, see them fail, then implement
