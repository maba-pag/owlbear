---
id: 407
title: Add knowledge_context_tokens config setting
status: archived
priority: important
created: 2026-03-01T20:18:51.0128879+01:00
updated: 2026-03-02T09:15:03.476885+01:00
started: 2026-03-01T20:23:54.348962+01:00
completed: 2026-03-02T09:15:03.476885+01:00
tags:
    - phase-13
    - config
    - knowledge-graph
depends_on:
    - 424
class: standard
---

From #305 context-aware-knowledge-injection.md. AC: - Add to OwlBearSettings in src/owlbear/config.py: knowledge_context_tokens: int = 2000 - Field validator: must be > 0 (raise ValueError with message 'knowledge_context_tokens must be greater than 0') - Environment variable: OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS - Place in Knowledge section (after embedding_model) - Depends on test task #424
