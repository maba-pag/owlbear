---
id: 426
title: Test KnowledgeQueryService bootstrap wiring
status: archived
priority: important
created: 2026-03-01T22:19:45.2689603+01:00
updated: 2026-03-02T09:15:22.6783971+01:00
started: 2026-03-01T22:19:50.0126484+01:00
completed: 2026-03-02T09:15:22.6783971+01:00
tags:
    - phase-13
    - daemon
    - test
class: standard
---

TDD test task for #409. File: tests/test_bootstrap.py (extend existing). AC: - _build_knowledge_toolset returns KnowledgeQueryService alongside toolset (tuple or dataclass) - bootstrap() passes knowledge_service to OwlBearAgent constructor - knowledge_context_tokens from settings used as default max_tokens for service - When knowledge subsystem unavailable: knowledge_service=None (graceful fallback) - Agent constructed with knowledge_service=None when knowledge components fail
