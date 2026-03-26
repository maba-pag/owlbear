---
id: 127
title: 'Research: PydanticAI multi-agent patterns and tool architecture'
status: archived
priority: needed
created: 2026-02-27T14:55:50.0841633+01:00
updated: 2026-02-28T23:52:50.9905929+01:00
started: 2026-02-27T16:39:05.5968684+01:00
completed: 2026-02-28T23:52:50.9905929+01:00
tags:
    - phase-8
    - research
    - agent
class: standard
---

Before building the agent framework, understand what PydanticAI offers natively. This research gates all P8 implementation.

## Research Checklist
- [ ] How does PydanticAI handle agent-to-agent delegation? (Agent.run inside a tool?)
- [ ] What toolset types exist? FunctionToolset, MCPServerStdio, others?
- [ ] How to share tools across agents vs restrict by role?
- [ ] PydanticAI structured output patterns for agent communication
- [ ] How does PydanticAI's dependency injection work with agent hierarchy?
- [ ] What does the PydanticAI Agent Playground / Logfire offer?
- [ ] Clone pydantic/pydantic-ai into docs/research/ for analysis
- [ ] Document findings in docs/research/agent-framework.md
- [ ] Create follow-up implementation tasks on kanban board
