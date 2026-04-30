---
id: 1215
title: Push validation from AgentView into KanbanEngine
status: backlog
priority: needed
created: '2026-04-30 15:29:15.255749+00:00'
updated: '2026-04-30 15:32:04.188300+00:00'
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1214
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Move validation logic from AgentView down into KanbanEngine.

## Files
- engine.py (AgentView → KanbanEngine)

## Change
Move body_size validation, archival matrix checking, status predicate evaluation, parent/dep existence checks from AgentView into KanbanEngine methods. AgentView becomes thin: error-code mapping + guidance only.

## AC
- [ ] KanbanEngine has validation methods for body_size, archival matrix, status predicates, parent/dep existence
- [ ] AgentView delegates to KanbanEngine for validation
- [ ] AgentView only handles error-code mapping and guidance text
- [ ] No behavior change from consumer perspective
- [ ] Tests pass

## Finding: 2.2
