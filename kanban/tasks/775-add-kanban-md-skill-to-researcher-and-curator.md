---
id: 775
title: Add kanban-md skill to researcher and curator agent definitions
status: backlog
priority: nice-to-have
created: 2026-03-13T10:41:58.2552099+01:00
updated: 2026-03-13T14:25:36.023231+01:00
started: 2026-03-13T14:25:36.023231+01:00
tags:
    - config
    - scope:core
claimed_by: researcher
claimed_at: 2026-03-13T14:25:36.023231+01:00
class: standard
---

Add kanban-md to skills list in src/owlbear/agents/researcher.md and src/owlbear/agents/curator.md so they can load kanban format guidance. See docs/research/cheat-sheet-tool.md S4.

[[2026-03-13]] Fri 14:24
## Research
N/A -- trivial config change. Fully analyzed in docs/research/cheat-sheet-tool.md (S3.3 gap analysis, S4 recommendation).

### Checklist
1. **Theoretical validity** -- Sound. Agents that interact with kanban ops should load format guidance. Parent research validated this.
2. **Prior art** -- 7/9 agents already follow this pattern (builder, reviewer, auditor, etc. have skills: [kanban-md, ...]).
3. **Technical feasibility** -- YAML edit in 2 .md files. AgentRegistry checks defn.skills truthiness to add SkillRegistry toolset (agent_registry.py L188-189).
4. **Architecture fit** -- Seamless. No new code. SkillRegistry already handles progressive loading.
5. **Implementation approach** -- Change skills: [] to skills: [kanban-md] in researcher.md and curator.md. Update EXPECTED_AGENTS in test_agent_definitions.py.

### Files to change
- src/owlbear/agents/researcher.md L11: skills: [] -> skills: [kanban-md]
- src/owlbear/agents/curator.md L9: skills: [] -> skills: [kanban-md]
- 	ests/test_agent_definitions.py L63,L96: update EXPECTED_AGENTS.researcher.skills and .curator.skills from [] to [kanban-md]

### Note
Researcher agent also lacks kanban and 	erminal tools -- it can read skill docs but not execute kanban commands via PydanticAI toolset. This is a separate scope concern (not blocking this task).
