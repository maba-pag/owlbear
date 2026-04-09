---
id: 733
title: 'Decompose #712: Native kanban engine into atomic subtasks (Phase 1-3)'
status: backlog
priority: needed
created: 2026-04-09T03:49:14.6128637+02:00
updated: 2026-04-09T07:04:47.0619099+02:00
tags:
    - phase-3
    - infrastructure
    - kanban
depends_on:
    - 712
class: standard
---

## Objective

Break #712 (native kanban engine) into atomic TDD-paired subtasks across three phases.

Needs decomposition: The parent task spans engine design, YAML I/O, 8 board operations, compound ops, MCP server migration, and cleanup across 40+ seam locations.

## Input
- Brief: `.owlbear/briefs/draft-kanban-native/brief.md`
- Research: `.owlbear/research/native-kanban-engine.md`
- Seam inventory in research doc (Section 3b)
- Key decisions D1-D7 in task #712 body

## AC
- [ ] Phase 1 subtasks: config loader, task YAML I/O (ruamel.yaml round-trip), each of 8 operations, compound ops — each with TDD test file
- [ ] Phase 2 subtasks: MCP server migration (atomic switchover), test migration
- [ ] Phase 3 subtasks: remove binary, remove setup scripts, update docs/guides/skills (checklist from seam inventory)
- [ ] Dependency graph between subtasks reflects build order
- [ ] All subtasks are children of #712
- [ ] CRITICAL CONSTRAINT preserved: existing subprocess server must work throughout Phase 1

[[2026-04-09]] Thu 07:04
## Research

**Finding: Task is redundant — decomposition already complete.**

The architect review on #712 explicitly flagged: "Redundant task #733 — decomposition was already completed (#713-#732 exist). #733 should be closed as redundant."

### AC Validation

All 6 AC lines satisfied by existing subtask structure:
- **Phase 1** (16 tasks): #713-728 cover models, config, I/O, listing, CRUD, claiming, compound ops, activity logging — each as RED/GREEN TDD pair
- **Phase 2** (2 tasks): #729-730 cover MCP server migration RED/GREEN
- **Phase 3** (2 tasks): #731 (700-file round-trip test), #732 (cleanup sweep per seam inventory)
- **Dependency graph**: verified — models→config→I/O→(listing∥CRUD)→claiming→compound+activity→MCP→(integration∥cleanup)
- **All subtasks parent: #712**: confirmed
- **CRITICAL CONSTRAINT**: Phase 2 atomic switchover correctly preserves subprocess server during Phase 1

### Status
- #713: archived (complete), #714: todo, #715-#732: backlog
- Existing research doc: `.owlbear/research/native-kanban-engine.md`
- No new follow-up tasks needed — #713-#732 already exist
- No new research doc — existing doc covers the domain
- Tier: T1 (redundant task, no decisions needed)
- Recommendation: Archive this task as redundant (confidence: .95)
