---
id: 4
title: .agent.md format validation
status: ideation
priority: needed
created: 2026-03-26T17:18:37.5800694+01:00
updated: 2026-03-26T17:18:37.5800694+01:00
tags:
    - research
    - phase-1
    - scope:agents
class: standard
---

## Objective
Research the .agent.md format and validate whether v1 agents can be ported. Map PydanticAI tool names to VS Code/CLI built-in tool names.

## Acceptance Criteria
- [ ] Read .agent.md specification (VS Code custom agents docs)
- [ ] Document all YAML frontmatter fields: tools, agents, model, handoffs, hooks
- [ ] Map v1 agent tool dependencies to VS Code built-in tools (file ops, terminal, git, search, etc.)
- [ ] Identify tools that have no built-in equivalent (these become MCP tool references)
- [ ] Test a custom agent in VS Code Copilot Chat
- [ ] Test agent-to-agent handoff via agents: field
- [ ] Test tool restrictions (allow/deny patterns)
- [ ] Document model selection and thinking effort configuration
- [ ] Write findings to docs/research/agent-md-format.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
OwlBear v1 has 9 agents already in .agent.md format in .github/agents/. They reference PydanticAI toolsets. V2 agents need to reference VS Code built-in tools + MCP server tools instead.
