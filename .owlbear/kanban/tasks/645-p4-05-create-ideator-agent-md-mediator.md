---
id: 645
title: 'P4-05: Create ideator.agent.md (Mediator)'
status: research
priority: critical
created: 2026-04-06T07:01:04.2471939+02:00
updated: 2026-04-06T07:01:04.2471939+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 641
    - 644
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/ideator.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: true` with argument-hint: `[idea, problem, or feature -- drop reference files in .owlbear/briefs/draft-new/input/]`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Persona implements Mediator behavior: single user-facing voice throughout all 6 moments
- [ ] Investigator mode for Moments 1-3 (problem mining, outcome shaping)
- [ ] Facilitative mode for Moments 4-6 (presenting synthesis, decisions, Brief)
- [ ] Transparent-by-default at all decision points (tier, voice selection, loop-back, Brief approval)
- [ ] Entry point logic: creates Working Directory, reads input/, detects new vs. existing project
- [ ] Invokes critic-voice at moment boundaries (after M1, M2, M4, M5)
- [ ] Invokes research subagent for M3 landscape scan
- [ ] Invokes domain voices between M3 and M4 (parallel `runSubagent`)
- [ ] Invokes pragmatist-voice for synthesis
- [ ] Reads only summary files (context.md, decisions.md, synthesis.md) -- never debates
- [ ] Writes context.md incrementally, decisions.md after user choices, brief.md at approval
- [ ] Handoff: creates parent kanban task with Brief content, invokes planner for subtasks
- [ ] Tool access: MCP kanban, project, knowledge; vscode_askQuestions; file system tools for Working Dir
- [ ] Agents list includes: critic-voice, pragmatist-voice, architect-voice, data-voice, enduser-voice, security-voice, planner

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 6, 7, 12.
This is the central agent. All other voice agents are invoked by it. The conversation flow drives through 6 moments with voice deliberation between M3 and M4.

## Key Design Constraints

- Context window economy: Mediator reads only 3 summary files + input/* + user conversation
- Research delegated to subagent in M3 (receives summary, not raw results)
- Voice selection logic based on problem signals (see Section 7)
- Investment tier detection and adaptive depth (see Sections 5, 9)
