---
id: 129
title: Agent registry — load, instantiate, and manage agents
status: archived
priority: needed
created: 2026-02-27T14:56:13.5544646+01:00
updated: 2026-02-28T23:52:52.4761284+01:00
started: 2026-02-27T18:53:27.2232751+01:00
completed: 2026-02-28T23:52:52.4761284+01:00
tags:
    - phase-8
    - agent
depends_on:
    - 128
class: standard
---

Central registry: scan agent definitions, instantiate PydanticAI Agents with configured tools/skills, lookup by name.
Research: docs/research/agent-framework.md section 3.2
Depends on: #128 (AgentDefinition + parse_agent_definition)

## AC
- [ ] File: src/owlbear/core/agent_registry.py
- [ ] AgentRegistry class:
      - __init__(agents_dir: Path, tool_resolver: Callable[[str], AbstractToolset], skill_registry: SkillRegistry | None = None, default_model: str = 'gpt-4o')
      - scan() -> None: parse all .md files in agents_dir via parse_agent_definition, store AgentDefinition metadata
      - get(name: str) -> Agent[OwlBearDeps, str]: lazily instantiate PydanticAI Agent on first call, cache thereafter
      - list_agents() -> list[AgentDefinition]: return all scanned definitions
      - definitions property: dict[str, AgentDefinition] (read-only view)
- [ ] get() builds Agent with:
      - model from AgentDefinition.model or default_model
      - instructions from AgentDefinition.system_prompt
      - toolsets resolved via tool_resolver(tool_name) for each tool in definition
      - role policy applied via apply_role_policy() if role != 'builder'
- [ ] KeyError raised when get() called with unknown agent name (message includes available names)
- [ ] scan() logs warnings for unparseable files (never raises)
- [ ] Tests (TDD — write first):
      - scan() finds 2+ valid definitions in temp dir
      - get(name) returns Agent, second call returns same cached instance
      - get('missing') raises KeyError with available names in message
      - list_agents() returns all scanned definitions
      - scan() with empty dir produces empty registry
      - scan() with invalid .md file logs warning, skips file
      - tool_resolver called for each tool name in definition
- [ ] ruff clean

## Architecture
- Follows SkillRegistry pattern: scan dir -> store metadata -> lazy load on demand
- AgentRegistry is NOT a toolset (unlike SkillRegistry) — plain registry class
- tool_resolver callback decouples registry from concrete toolset knowledge
- get() returns PydanticAI Agent (not OwlBearAgent) — inner agents don't need session persistence
- Will be injected into OwlBearDeps for delegation (#130)
