---
id: 45
title: Implement two-layer agent loop
status: archived
priority: high
created: 2026-02-26T15:57:21.3601536+01:00
updated: 2026-02-27T10:00:15.8633672+01:00
started: 2026-02-26T19:41:31.2854027+01:00
completed: 2026-02-27T10:00:15.8633672+01:00
tags:
    - phase-2
    - agent
depends_on:
    - 38
    - 39
    - 41
    - 43
    - 44
class: standard
---

See docs/agent-patterns-research.md para 2.1. This is the core of OwlBear.

## Research required (gate: ideation to backlog)

1. **Theoretical validity** - Is a two-layer loop (outer retry/session + inner turn) the right pattern? Or does PydanticAI's Agent.run() already provide this?
2. **Prior art** - Study PydanticAI Agent class (run, run_sync, run_stream), nanobot agent/loop.py, OpenClaw agent loop, AutoGPT loop patterns
3. **Technical feasibility** - PydanticAI already has a sophisticated agent loop with tool execution and retries. What would our own loop add? When do we need to break out of PydanticAI's loop?
4. **Architecture fit** - Central orchestrator. Connects to: Message model (#37), HookRegistry (#38), Tools (#39), Session (#41), Channel (#43), Provider (#44). This task depends on all of them being designed.
5. **Implementation approach** - Thin wrapper around PydanticAI Agent vs fully custom loop. What does the daemon process model require that PydanticAI doesn't provide?

## AC
Src: src/owlbear/core/agent.py with Agent class: outer_loop (retry, session management) + inner_turn (LLM call, tool execution, hook emission). Less than 100 LOC for core loop. Integration test with mocked provider.
