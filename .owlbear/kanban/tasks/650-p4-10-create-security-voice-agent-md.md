---
id: 650
title: 'P4-10: Create security-voice.agent.md'
status: research
priority: needed
created: 2026-04-06T07:03:14.8495037+02:00
updated: 2026-04-06T07:03:14.8495037+02:00
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

- [ ] `share/agents/security-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Domain: access control, data safety, trust boundaries, compliance
- [ ] Reads: `context.md`, `decisions.md`, optionally `research-notes.md`
- [ ] Writes: `voices/security.md`, `voices/security-debate.md`
- [ ] Embedded Critic loop (same pattern as architect-voice)
- [ ] Agents list includes `critic-voice`

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Follows architect-voice pattern. Domain focus: OWASP awareness, data boundaries, trust assumptions.
