---
id: 130
title: Agent delegation — orchestrator dispatches subtasks to inner agents
status: archived
priority: needed
created: 2026-02-27T14:56:24.3870888+01:00
updated: 2026-02-28T23:52:53.4355652+01:00
started: 2026-02-27T18:53:27.702778+01:00
completed: 2026-02-28T23:52:53.4355652+01:00
tags:
    - phase-8
    - agent
depends_on:
    - 128
    - 129
    - 161
class: standard
---

The outer agent (orchestrator) can delegate work to specialized inner agents via a tool function.
Research: docs/agent-framework-research.md section 3.3
Depends on: #128 (AgentDefinition), #129 (AgentRegistry), #161 (OwlBearDeps extension)

## AC

- [ ] File: src/owlbear/core/delegation.py
- [ ] DelegationToolset (FunctionToolset subclass) with delegate_to_agent tool:
      - Parameters: agent_name: str, task: str
      - Accesses ctx.deps.agent_registry to look up agent
      - Accesses ctx.deps._delegation_depth to check depth limit
      - Creates new OwlBearDeps via dataclasses.replace() with incremented depth
      - Calls inner_agent.run(task, deps=inner_deps, usage=ctx.usage)
      - Returns result.output (str) on success
      - Returns error string (not exception) on:
        - Agent not found (KeyError)
        - Max depth exceeded
        - Inner agent failure (any exception)
- [ ] MAX_DELEGATION_DEPTH module constant (default 5)
- [ ] Tests (TDD — write first):
      - Successful delegation: mock agent returns result, tool returns output string
      - Agent not found: returns error string with agent name
      - Max depth exceeded: returns error string, inner agent NOT called
      - Inner agent exception: caught, returns error string, does not raise
      - Usage object passed through to inner agent via usage= kwarg
      - Depth incremented correctly in inner deps (depth+1)
      - ctx.deps.agent_registry is None: returns error string
- [ ] ruff clean

## Architecture

- PydanticAI native delegation: tool function calls inner.run(task, deps=..., usage=...)
- ~25 LOC for the tool function, ~15 LOC for the toolset class
- Inner failures caught and returned as error strings — never propagated to outer agent
- Context isolation: each inner agent gets fresh message history
- Usage aggregates via PydanticAI native usage= parameter
- MVP returns str; structured TaskResult output is YAGNI for now
