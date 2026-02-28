---
id: 128
title: Agent definition format — system prompt, tools, skills per agent
status: archived
priority: needed
created: 2026-02-27T14:56:01.2353624+01:00
updated: 2026-02-28T23:52:51.667013+01:00
started: 2026-02-27T18:53:26.7300977+01:00
completed: 2026-02-28T23:52:51.667013+01:00
tags:
    - phase-8
    - agent
depends_on:
    - 127
class: standard
---

Define how an agent's 'soul' is configured. Each agent needs: identity, system prompt, tool access list, skill access list, role policy.
Research: docs/agent-framework-research.md section 3.1

## AC
- [ ] File: src/owlbear/core/agent_def.py
- [ ] AgentDefinition Pydantic BaseModel with fields:
      - name: str (required)
      - description: str (required)
      - role: str (default 'builder', should match AgentRole values)
      - tools: list[str] (default [])
      - skills: list[str] (default [])
      - model: str | None (default None — inherits from caller)
      - max_delegation_depth: int (default 3)
      - system_prompt: str (populated from markdown body, not frontmatter)
- [ ] parse_agent_definition(path: Path) -> AgentDefinition
      - Reads YAML frontmatter + markdown body
      - Follows _parse_frontmatter / _safe_parse_yaml pattern from SkillRegistry
      - Body (after second ---) = system_prompt field
      - Raises ValueError on missing required fields (name, description)
- [ ] Tests (TDD — write first):
      - Parse valid definition with all fields populated
      - Parse definition with defaults (role='builder', tools=[], model=None, max_delegation_depth=3)
      - Missing name raises ValueError
      - Missing description raises ValueError
      - Empty body sets system_prompt to empty string
      - Invalid YAML raises ValueError
- [ ] ruff clean

## Architecture
- Mirrors SkillMeta/SkillRegistry frontmatter pattern but uses Pydantic BaseModel for richer validation
- role field maps to AgentRole in roles.py — validate value is a known role
- system_prompt populated from markdown body — NOT a frontmatter field
- Parser: ~30-50 LOC, standalone function (not a class method)
