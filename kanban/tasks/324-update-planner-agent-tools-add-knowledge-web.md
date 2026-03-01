---
id: 324
title: 'Update planner agent tools: add knowledge, web_search, project-definition skill'
status: archived
priority: needed
created: 2026-03-01T06:32:42.7417844+01:00
updated: 2026-03-01T17:09:49.193648+01:00
started: 2026-03-01T06:32:47.6993082+01:00
completed: 2026-03-01T17:09:49.193648+01:00
tags:
    - phase-11
    - planning
    - agent
    - config
depends_on:
    - 323
class: standard
---

## Acceptance Criteria
- [ ] Update src/owlbear/agents/planner.md tools list: add knowledge and web_search (after delegation)
- [ ] Update src/owlbear/agents/planner.md skills list: add project-definition (after kanban-based-development)
- [ ] Update tests/test_agent_definitions.py KNOWN_TOOLSETS: add 'knowledge' and 'web_search'
- [ ] Update tests/test_agent_definitions.py EXPECTED_AGENTS['planner']['tools']: add 'knowledge' and 'web_search'
- [ ] Update tests/test_agent_definitions.py EXPECTED_AGENTS['planner']['skills']: add 'project-definition'
- [ ] bootstrap.py tool_resolver already maps knowledge->KnowledgeToolset and web_search->WebSearchToolset (lines 376-377) — NO changes to bootstrap.py needed
- [ ] planner system_prompt line count stays within test_system_prompt_nonempty bounds (10-25 non-blank lines) — if it exceeds, update the bound
- [ ] All tests pass: uv run pytest tests/test_agent_definitions.py -v

Architecture note: bootstrap._aliases already has 'knowledge' and 'web_search' entries. Both toolsets are conditional (only built when deps are available). The planner must degrade gracefully when they are absent — this is handled by tool_resolver raising KeyError which AgentRegistry already catches.
See docs/project-definition-workflow-research.md sec3.5
