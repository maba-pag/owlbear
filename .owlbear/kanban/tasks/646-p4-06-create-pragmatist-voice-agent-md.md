---
id: 646
title: 'P4-06: Create pragmatist-voice.agent.md'
status: research
priority: needed
created: 2026-04-06T07:01:14.5070148+02:00
updated: 2026-04-06T07:01:14.5070148+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 645
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/pragmatist-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Reads: `context.md`, `decisions.md`, ALL `voices/*.md` results
- [ ] Writes: `synthesis.md`
- [ ] Identifies convergences, disagreements, and produces recommendation
- [ ] Flags disagreements with attribution (NOT resolved algorithmically -- resolution is user's job)
- [ ] Does NOT read debate logs, user conversation, raw research, or input files

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Pure synthesis subagent invoked after all domain voices have published. The Mediator reads synthesis.md and presents it to the user.
