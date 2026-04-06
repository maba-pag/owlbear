---
id: 648
title: 'P4-08: Create data-voice.agent.md'
status: research
priority: needed
created: 2026-04-06T07:01:36.1434924+02:00
updated: 2026-04-06T07:01:36.1434924+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 644
    - 645
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/data-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Domain: data quality, validation, flows, schemas, ETL, analytics
- [ ] Reads: `context.md`, `decisions.md`, optionally `research-notes.md`
- [ ] Writes: `voices/data-person.md`, `voices/data-person-debate.md`
- [ ] Embedded Critic loop (same pattern as architect-voice)
- [ ] Agents list includes `critic-voice`

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Follows architect-voice pattern. Domain focus: data schemas, validation, ETL pipeline patterns, data integrity.
