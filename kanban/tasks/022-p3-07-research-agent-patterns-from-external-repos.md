---
id: 22
title: 'P3-07: Research agent patterns from external repos'
status: done
priority: high
created: 2026-02-24T15:13:05.1441733+01:00
updated: 2026-02-26T15:58:30.1150482+01:00
started: 2026-02-24T15:17:04.9604469+01:00
completed: 2026-02-26T15:58:30.1150482+01:00
tags:
    - phase-3
    - research
    - agent
class: standard
---

AC: Deep-dive research into agent patterns and architecture from external repos.

Scope:
1. Clone openclaw (https://github.com/AiAutomatrix/openclaw) to docs/research/openclaw. Analyze: interactive gateway, heartbeat, backend connectivity, plugin architecture, build pipeline (ideation/dev/test/publish), human-in-the-loop patterns, communication channel abstractions.
2. Clone nanobot (https://github.com/HKUDS/nanobot) to docs/research/nanobot. Analyze: agent loop, skills system, subagent spawning, provider abstraction, session management, Typer CLI, WhatsApp integration (if present). This subsumes task #29.
3. Study coleam00 repos and disler/hooks-mastery for agent structures, personas, skill definitions, boundary patterns.

Deliverables:
- docs/agent-patterns-research.md with: architecture comparisons, recommended patterns for OwlBear agent loop, build pipeline design, communication gateway abstraction, quality gate patterns (Ralph Wiggum prevention), voice input pipeline notes.
- Architecture doc template/structure recommendations (gleaned from how these projects document their own architecture).
- Follow-up kanban tasks per research-docs guardrails.
- Log all repos in docs/sources.md.
- Delete docs/research/* clones after analysis.
