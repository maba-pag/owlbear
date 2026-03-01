---
id: 305
title: Context-aware research — use knowledge base to improve agent work
status: ideation
priority: important
created: 2026-03-01T02:54:19.689127+01:00
updated: 2026-03-01T02:54:54.9129285+01:00
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

## Acceptance Criteria
- [ ] ContextInjectionHook enhanced: on SESSION_START, query knowledge base for relevant context
- [ ] Relevance query based on: user's current message, project name, active task
- [ ] Top-K relevant knowledge chunks injected into agent instructions (token-budgeted)
- [ ] Token budget: configurable max tokens for knowledge context (default: 2000)
- [ ] Agent prompt includes 'You have access to these relevant facts from past research: ...
- [ ] Refreshed per-turn (not just session start) for long conversations
- [ ] Unit tests verifying knowledge injection with mock query results
