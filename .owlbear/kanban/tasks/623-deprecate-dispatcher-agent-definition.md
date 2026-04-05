---
id: 623
title: Deprecate dispatcher agent definition
status: ideation
priority: important
created: 2026-04-05T01:31:22.2282042+02:00
updated: 2026-04-05T01:58:35.0507883+02:00
tags:
    - scope:agents
    - phase-2
    - type:build
    - agent
parent: 619
depends_on:
    - 622
class: standard
---

## Acceptance Criteria

- Dispatcher agent file (share/agents/dispatcher.agent.md) is marked deprecated:
  - YAML frontmatter: `deprecated: true` (or equivalent marker)
  - Description prefixed with "(DEPRECATED)"
  - Body explains replacement by pick_tasks MCP tool
- Dispatcher removed from orchestrator agent's `agents:` list (if it was listed there)
- copilot-instructions.md pipeline description updated if it references dispatcher
- No remaining references to dispatcher as a live subagent in any active agent/skill file
- Dispatcher agent file NOT deleted (kept for reference), just deprecated
