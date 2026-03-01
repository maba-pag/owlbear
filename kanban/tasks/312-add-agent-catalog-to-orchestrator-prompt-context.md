---
id: 312
title: Add agent catalog to orchestrator prompt context
status: archived
priority: important
created: 2026-03-01T06:17:11.2661245+01:00
updated: 2026-03-01T17:09:36.6783335+01:00
started: 2026-03-01T06:17:16.4570083+01:00
completed: 2026-03-01T17:09:36.6783335+01:00
tags:
    - phase-12
    - agent
    - routing
depends_on:
    - 311
class: standard
---

Ensure orchestrator system prompt includes all available agent names and one-line descriptions:

- [ ] Static agent catalog in orchestrator.md listing: planner, coder, researcher, reviewer, writer (name + description + when to delegate)
- [ ] Verify the catalog matches AgentRegistry.definitions after scan (test in test_agent_definitions.py or test_intent_routing.py)
- [ ] If agent list grows, update orchestrator.md (acceptable manual maintenance for 6 agents)
- [ ] YAGNI: do NOT build dynamic injection — static list is simpler and the agent inventory changes rarely
- [ ] ruff clean

This is lower priority than #311 because the routing rules already name agents. This task ensures descriptions are also present for better LLM selection accuracy.
See docs/conversation-router-research.md S4
