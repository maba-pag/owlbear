---
id: 1009
title: Implement skill pre-flight sub-step in w-ideation M1
status: backlog
priority: nice-to-have
created: 2026-04-18T21:57:35.239825+00:00
updated: 2026-04-18T21:57:35.239825+00:00
tags:
- type:improvement
- scope:skills
parent:
depends_on:
- 997
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
w-ideation M1 lacks a skill pre-flight check. Existing conventions in skill files may contradict assumptions made during problem narrowing, only surfacing at M3 when decisions are locked.

## Fix
Insert a "Skill Pre-Flight" sub-step in `share/skills/w-ideation/SKILL.md` Step 1 (M1), between current steps 5 and 6 (after narrowing, before writing Problem Statement).

## Acceptance Criteria
- [ ] w-ideation Step 1 includes a "Skill Pre-Flight" sub-step between "catch disguised solutions" (step 5) and "write Problem Statement" (step 6)
- [ ] Sub-step lists: extract 2-3 keywords → grep `share/skills/` and `share/instructions/` → skim matched sections → surface conflicts as M1 probes
- [ ] Sub-step includes 3+ keyword → skill examples (e.g., blocking → `r-pipeline-protocol`; kanban → `h-mcp-kanban`; agents → `agent-common.instructions.md`)
- [ ] Sub-step explicitly states: "1-2 minutes, not a substitute for M3 Explore"
- [ ] Verification Checklist updated to include skill pre-flight completion check
- [ ] No new tooling required — uses Mediator's existing `textSearch`/`fileSearch`

## Research
See `.owlbear/research/997-skill-preflight-ideation-m1.md`