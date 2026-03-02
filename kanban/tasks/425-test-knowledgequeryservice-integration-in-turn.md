---
id: 425
title: Test KnowledgeQueryService integration in turn()
status: archived
priority: needed
created: 2026-03-01T22:19:32.253523+01:00
updated: 2026-03-02T09:15:20.40128+01:00
started: 2026-03-01T22:19:37.5767018+01:00
completed: 2026-03-02T09:15:20.40128+01:00
tags:
    - phase-13
    - agent
    - test
class: standard
---

TDD test task for #408. File: tests/test_agent.py (extend existing or new test_agent_knowledge.py). AC: - OwlBearAgent.__init__ accepts knowledge_service: KnowledgeQueryService | None = None - turn() calls knowledge_service.query_for_context(prompt) when service is not None - turn() passes result as instructions= to inner.run() - When knowledge_service is None: inner.run() called without instructions= (existing behavior preserved) - When service returns None: instructions=None passed to inner.run() - When service raises exception: warning logged, turn() continues without injection (never breaks)
