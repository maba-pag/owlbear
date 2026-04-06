---
id: 647
title: 'P4-07: Create architect-voice.agent.md'
status: research
priority: needed
created: 2026-04-06T07:01:27.4188843+02:00
updated: 2026-04-06T07:01:27.4188843+02:00
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

- [ ] `share/agents/architect-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Domain: system design, structure, patterns, component integration
- [ ] Reads: `context.md`, `decisions.md`, optionally `research-notes.md`
- [ ] Writes: `voices/architect.md` (final position), `voices/architect-debate.md` (Critic dialogue log)
- [ ] Embedded Critic loop: invokes `critic-voice` with current position, up to 5 cycles
- [ ] Persona has strong opinions from architectural perspective, not neutral
- [ ] Agents list includes `critic-voice`

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Domain voice subagent. Follows the Voice Reasoning Cycle: read context, form opinion, Critic loop, publish hardened position.

## Pattern

This is the first domain voice. Its structure should serve as template for data-voice, enduser-voice, and security-voice. Core pattern:
1. Read context.md + decisions.md
2. Form initial opinion from architectural lens
3. Critic loop (invoke critic-voice, refine or stand firm, repeat)
4. Write final position + debate log
