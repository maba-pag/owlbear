---
id: 42
title: Implement two-layer memory (context + session)
status: done
priority: medium
created: 2026-02-26T15:57:02.648065+01:00
updated: 2026-02-26T19:57:27.369324+01:00
started: 2026-02-26T19:42:20.0121496+01:00
completed: 2026-02-26T19:57:27.369324+01:00
tags:
    - phase-2
    - agent
    - memory
depends_on:
    - 41
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.2)

PydanticAI supports system prompt injection via: (1) static strings in system_prompt parameter, (2) dynamic functions via @agent.system_prompt decorator, (3) instructions parameter for agent-level instructions. These cover our context injection needs.

pydantic-deepagents injects context via: (1) MEMORY.md — persistent memory with read/write tools, (2) context files — auto-discover DEEP.md/AGENTS.md and inject into system prompt.

**Decision:** Build ContextManager that loads context.md from workspace root and injects it via PydanticAI instructions. Two layers: Layer 1 = static context file (always loaded), Layer 2 = session history (from #41). Knowledge graph (#50) becomes Layer 3 later.

## AC
Src: src/owlbear/memory/context.py with ContextManager. Loads context.md, injects into PydanticAI Agent instructions. Tests verify injection.
