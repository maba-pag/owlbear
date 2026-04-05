---
id: 575
title: 'P2-04: Update pipeline agent files with MCP tool references alongside CLI'
status: ideation
priority: needed
created: 2026-04-03T11:15:13.4411362+02:00
updated: 2026-04-05T07:30:10.8668696+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:build'
parent: 483
depends_on:
    - 572
    - 574
claimed_by: fork-solar
claimed_at: 2026-04-05T07:30:10.8641816+02:00
class: standard
---

## Acceptance Criteria\n\n- [ ] All 11 pipeline agent files updated with MCP tool alternatives alongside CLI examples\n- [ ] Agents: architect, auditor, builder, curator, kanban-planner, planner, researcher, reviewer, scribe, test-writer, writer\n- [ ] Each agent's inline CLI command examples show MCP equivalent (e.g., start_work/end_work for claim+show/advance+release)\n- [ ] Compound tools (start_work, end_work) documented as preferred pattern for task lifecycle\n- [ ] No existing CLI references removed (fallback preserved)\n- [ ] Must pass agent file checks in #572\n\n## Files\n\nagents/architect.agent.md, agents/auditor.agent.md, agents/builder.agent.md, agents/curator.agent.md, agents/kanban-planner.agent.md, agents/planner.agent.md, agents/researcher.agent.md, agents/reviewer.agent.md, agents/scribe.agent.md, agents/test-writer.agent.md, agents/writer.agent.md\n\n## Dependencies\n\nDepends on #574 (instructions update) so agents reference consistent MCP patterns from agent-common.

[[2026-04-05]] Sat 09:42
## Research
- Research doc: .owlbear/research/575-agent-mcp-lifecycle-audit.md
- Sources: 7 studied, 5 high-relevance (all codebase/kanban)
- Recommendation: Close as resolved-by-architecture (confidence: .78). v2 correctly factors MCP lifecycle: generic pattern in h-mcp-kanban skill (single source), agent-specific outcomes inline in kanban protocol. Original AC premise (CLI to MCP annotation) no longer applies.
- AC issues: lists 11 agents (10 exist, 9 should get blocks), names kanban-planner (absent) and writer (= doc-writer), includes scribe (never claims tasks)
- Follow-up tasks created: #625 at ideation (restore #574 pipeline protocol MCP callouts). #596 already at todo (planner skill language fix).
- Decision requests: none (all findings T1)

## Challenge Results
- Challenger: reconsider (confidence in original: .55, lowered from .82)
- Key challenges: C1 (DRY violation), C3 (2-variant oversimplifies), C4 (#574 is audit failure), C5 (no empirical gap)
- Researcher response: accepted C1/C3/C4/C5. Revised from full lifecycle blocks to close-as-resolved-by-architecture.
