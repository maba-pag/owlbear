---
id: 997
title: Add skill pre-flight to w-ideation M1
status: backlog
priority: nice-to-have
created: 2026-04-18T21:26:18.187211+00:00
updated: 2026-04-18T21:57:42.388859+00:00
tags:
- type:improvement
- scope:skills
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
M3 landscape (via Explore subagent) covers codebase + ecosystem scan, but happens AFTER M1 (Understanding) and M2 (Outcomes) are locked. If existing skills/conventions in OwlBear contradict assumptions made in M1/M2, they only surface at M3 when decisions are already locked — forcing loop-backs.

Concrete example from ideation #973: user and Mediator locked "every block requires a DR, no exemptions" in M1. Critic later surfaced that `r-pipeline-protocol` already distinguishes DR from AR and lists legitimate non-DR/AR blocks. A 30-second `grep` for "block" / "DR" / "Decision Request" in `share/skills/` would have caught this before locking M1.

## Fix
Add a "Skill pre-flight" sub-step to w-ideation Step 1:
- After restating the problem, identify 1-3 skill files most likely relevant (by name match to problem keywords).
- Skim those skills (read or grep) for existing conventions/protocols on the topic.
- Surface any apparent conflicts to the user as part of M1 probes, before tier confirmation.

## Acceptance Criteria
- w-ideation Step 1 includes a "Skill pre-flight" sub-step with explicit guidance on selecting and skimming relevant skills.
- Step lists examples: problem about kanban → grep `r-pipeline-protocol`, `h-mcp-kanban`; problem about agents → check `agent-common.instructions.md`; etc.
- Step makes clear this is fast (1-2 minutes), not a substitute for M3 Explore.

## Context
Surfaced during ideation session for #973.
[[2026-04-18]]
## Research
- Research doc: `.owlbear/research/997-skill-preflight-ideation-m1.md`
- Sources: 5 studied, 3 high-relevance (w-ideation SKILL.md, w-research Step 1.5, r-pipeline-protocol § Knowledge Pre-flight)
- Recommendation: Insert skill pre-flight as M1 sub-step between steps 5→6 (confidence: 0.88). Mediator greps `share/skills/` + `share/instructions/` for 2-3 problem keywords, skims matches, surfaces convention conflicts as M1 probes before tier confirmation.
- Follow-up tasks created: #1009 (backlog — implement the sub-step in w-ideation SKILL.md)
- Decision requests: none (T1 — autonomous skill-file improvement)