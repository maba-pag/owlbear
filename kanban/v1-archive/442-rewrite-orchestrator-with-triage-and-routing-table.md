---
id: 442
title: Rewrite orchestrator with triage and routing table
status: archived
priority: needed
created: 2026-03-03T17:26:03.8182373+01:00
updated: 2026-03-04T07:58:20.4497962+01:00
started: 2026-03-03T18:03:35.3853146+01:00
completed: 2026-03-04T07:58:20.4497962+01:00
tags:
    - agent-refactor
    - agent
    - phase-refactor
depends_on:
    - 436
    - 437
class: standard
---

Redesign orchestrator.agent.md: add triage table (trivial/standard/complex/research), agent capability matrix with per-agent routing, structured delegation template, one-task-per-dispatch in critical_rules. Add agents: frontmatter listing all dispatchable agents. Remove serial chain optimization. Target ~150 lines excluding examples. Add emotional motivation in persona. See docs/agent-quality-analysis.md sections 6.3-6.5.
