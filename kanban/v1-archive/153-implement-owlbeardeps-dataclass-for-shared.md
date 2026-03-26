---
id: 153
title: Implement OwlBearDeps dataclass for shared dependency injection
status: archived
priority: important
created: 2026-02-27T16:47:45.9830354+01:00
updated: 2026-02-28T23:53:10.9680138+01:00
started: 2026-02-27T16:48:17.6961643+01:00
completed: 2026-02-28T23:53:10.9680138+01:00
tags:
    - phase-8
    - agent
    - core
class: standard
---

Shared dependency type for all OwlBear agents, replacing manual __init__ params. Research: docs/research/pydantic-ai-multi-agent.md section 3.5.

## AC
- [ ] File: src/owlbear/core/deps.py
- [ ] @dataclass class OwlBearDeps with fields: hooks: HookRegistry, tracker: UsageTracker | None = None
- [ ] Keep deps minimal — only fields that multiple agents need via ctx.deps. Do NOT include workspace_root or session (those are per-agent, not shared across delegated agents)
- [ ] Refactor OwlBearAgent: change inner Agent from Agent[None, str] to Agent[OwlBearDeps, str]
- [ ] Add workspace_root: Path | None = None parameter to OwlBearAgent.__init__ — store on self, do NOT put in deps
- [ ] OwlBearAgent.__init__ constructs OwlBearDeps from hooks + tracker
- [ ] OwlBearAgent.turn() passes deps to inner.run() call via deps= kwarg
- [ ] All existing tests continue to pass (backwards-compatible — OwlBearAgent public API adds workspace_root but it defaults to None)
- [ ] Test: OwlBearDeps dataclass construction with all fields
- [ ] Test: OwlBearAgent creates and injects deps into inner Agent run
- [ ] ruff clean

## Architecture
- This enables PydanticAI native DI: tools access ctx.deps.hooks, ctx.deps.tracker, etc.
- Required foundation for agent delegation in P8 (inner_agent.run(deps=ctx.deps, usage=ctx.usage))
- Keep deps minimal — hooks + tracker only. session is per-agent, workspace_root is per-agent
- OwlBearAgent public API stays the same for existing callers (new param defaults to None)
- WrapperToolset is NOT a dataclass inheritance concern here — separate task #155
