---
id: 424
title: Test knowledge_context_tokens config setting
status: archived
priority: important
created: 2026-03-01T22:19:18.3356433+01:00
updated: 2026-03-02T09:15:18.1384467+01:00
started: 2026-03-01T22:19:23.0882844+01:00
completed: 2026-03-02T09:15:18.1384467+01:00
tags:
    - phase-13
    - config
    - test
class: standard
---

TDD test task for #407. File: tests/test_config.py (extend existing). AC: - OwlBearSettings.knowledge_context_tokens defaults to 2000 - Env var OWLBEAR_KNOWLEDGE_CONTEXT_TOKENS overrides default - Setting value <= 0 raises ValidationError - Setting value of 500 is accepted (positive int)
