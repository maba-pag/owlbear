---
id: 296
title: Conversation router — intent detection and agent dispatch
status: archived
priority: critical
created: 2026-03-01T02:52:45.1118209+01:00
updated: 2026-03-22T18:59:18.9188783+01:00
started: 2026-03-01T05:59:56.1772238+01:00
completed: 2026-03-01T17:09:22.6179232+01:00
tags:
    - phase-12
    - agent
    - routing
depends_on:
    - 293
class: standard
---

SPLIT into atomic sub-tasks:

- #310 — Unit tests for intent routing (TDD first) [todo]
- #311 — Update orchestrator system prompt with routing rules [todo, depends-on #310]
- #312 — Add agent catalog to orchestrator prompt [todo, depends-on #311]

Architect decision: Approach A (prompt-based routing in orchestrator system prompt). No dedicated router agent, no IntentClassification model, no semantic-router dependency. See docs/research/conversation-router.md.

This parent task is now complete — all work tracked via children.
