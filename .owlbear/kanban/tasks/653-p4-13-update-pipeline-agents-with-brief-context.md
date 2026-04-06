---
id: 653
title: 'P4-13: Update pipeline agents with Brief context'
status: research
priority: nice-to-have
created: 2026-04-06T07:03:44.1448783+02:00
updated: 2026-04-06T07:03:44.1448783+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:integrate'
depends_on:
    - 651
    - 652
class: standard
---

## Acceptance Criteria

- [ ] Pipeline agents (planner, orchestrator, etc.) can read Brief from parent task body
- [ ] Agents reference Brief context when available, gracefully skip when absent
- [ ] w-orchestration skill updated to mention Brief as optional context source
- [ ] w-task-decomposition skill updated to accept Brief-derived scope
- [ ] No breaking changes to existing pipeline flow (Brief is additive)

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 8, 11.
Integration task: ensures the Brief artifact produced by ideation flows into existing pipeline agents. The Brief lives in the parent kanban task body — agents just need to know to look for it.
