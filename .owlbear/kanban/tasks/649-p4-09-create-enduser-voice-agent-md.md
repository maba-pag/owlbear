---
id: 649
title: 'P4-09: Create enduser-voice.agent.md'
status: research
priority: needed
created: 2026-04-06T07:01:44.3789771+02:00
updated: 2026-04-06T07:01:44.3789771+02:00
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

- [ ] `share/agents/enduser-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Domain: human experience, usability, clarity, discoverability
- [ ] Reads: `context.md`, `decisions.md`, optionally `research-notes.md`
- [ ] Writes: `voices/enduser.md`, `voices/enduser-debate.md`
- [ ] Embedded Critic loop (same pattern as architect-voice)
- [ ] Agents list includes `critic-voice`

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Follows architect-voice pattern. Domain focus: user experience, interaction clarity, approachability.
