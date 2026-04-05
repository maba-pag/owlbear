---
id: 623
title: Deprecate dispatcher agent definition
status: backlog
priority: important
created: 2026-04-05T01:31:22.2282042+02:00
updated: 2026-04-05T14:18:12.9675902+02:00
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

[[2026-04-05]] Sun 14:18
## Research
- Research doc: .owlbear/research/deprecate-dispatcher-agent.md
- Sources: 8 studied, 7 high-relevance (all codebase-internal, no external)
- Recommendation: Follow h-kanban-md deprecation pattern (description prefix + body callout); narrow scope to dispatcher.agent.md + orchestrator agents: list; copilot-instructions.md has no refs (N/A) (confidence: .88)
- Follow-up tasks created: none (gap noted in #629 body for w-task-decomposition L19)
- Decision requests: none — T1 autonomous, executing pre-approved migration plan

## Challenge Results
- Challenger: SKIP — T1 execution of pre-approved plan (#619 arch review approved all subtasks including deprecation)
- Tier: T1 (autonomous), no new capability or architecture change
- Key findings: (1) 38 dispatcher refs across 8 files; only 4 refs in #623 scope (agent file + orchestrator agents: list); (2) AC item 4 overlaps #629 — narrow to orchestrator agents: list verification; (3) w-task-decomposition L19 gap added to #629
- Researcher response: documented scope boundary; no new tasks needed (existing subtasks cover all work)
