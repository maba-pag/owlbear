---
id: 305
title: Context-aware research — use knowledge base to improve agent work
status: archived
priority: important
created: 2026-03-01T02:54:19.689127+01:00
updated: 2026-03-03T15:33:21.401839+01:00
started: 2026-03-01T19:55:13.6887087+01:00
completed: 2026-03-03T15:33:21.401839+01:00
tags:
    - phase-13
    - knowledge-graph
    - agent
depends_on:
    - 291
class: standard
---

## Context
Agents currently work with only session history and static context.md. The knowledge base has accumulated information but agents don't query it automatically to inform their decisions.

## Status: FAST-TRACK — Already Implemented
All work completed via archived sub-tasks #406-#409 (impl) and #423-#427 (tests).
Builder/reviewer should verify existing code and tests, then advance to done.

## Acceptance Criteria (refined to match implementation)
- [x] KnowledgeQueryService created at src/owlbear/memory/knowledge/query_service.py
- [x] Per-turn injection: OwlBearAgent.turn() calls query_for_context(prompt) every turn
- [x] PydanticAI instructions= parameter used for injection (superior to hook enhancement)
- [x] Relevance query embeds user prompt + project scopes (global + project:{id})
- [x] Top-K relevant knowledge chunks formatted within token budget
- [x] Token budget: knowledge_context_tokens config setting (default: 2000)
- [x] Header format: 'Relevant knowledge:' followed by scored document snippets
- [x] GraphAugmentedRetriever integration when knowledge_graph_expansion enabled
- [x] Graceful degradation: exceptions caught, logged WARNING, agent continues without context
- [x] Bootstrap wiring: _build_knowledge_toolset returns (toolset, service) tuple
- [x] Unit tests: test_knowledge_query_service.py, TestOwlBearAgentKnowledgeInjection in test_agent.py, TestBuildKnowledgeToolsetReturnsService in test_bootstrap.py

## Implementation sub-tasks (all archived)
- #406 Implement KnowledgeQueryService
- #407 Add knowledge_context_tokens config setting
- #408 Integrate KnowledgeQueryService into OwlBearAgent.turn()
- #409 Wire KnowledgeQueryService in bootstrap
- #423 Test KnowledgeQueryService
- #424 Test knowledge_context_tokens config
- #425 Test KnowledgeQueryService integration in turn()
- #426 Test KnowledgeQueryService bootstrap wiring
- #427 Unit tests for KnowledgeQueryService graph expansion

## Research doc
See docs/research/context-aware-knowledge-injection.md for details.
