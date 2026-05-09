---
id: 1462
title: 'B2-impl: Update loop-breaker terminology to batch-review-cycle and add cycle-3
  escalation'
status: research
priority: important
created: 2026-05-09T03:31:13.416517+00:00
updated: 2026-05-09T03:31:30.689453+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
- agent
parent: 1403
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)
Research: `.owlbear/research/loop-breaker-batch-cycle-update.md`

## Acceptance Criteria

P1: `r-pipeline-protocol/SKILL.md` Confidence Thresholds table uses "batch review cycle" instead of "FAIL" for reviewer loop-breaker rows (td:0)
P2: `r-pipeline-protocol/SKILL.md` has a new row for 3rd+ batch review cycle → architect escalation for AC refinement (td:0)
P3: `w-code-review/SKILL.md` FAIL routing section uses "batch review cycle" instead of "review FAIL" for loop-breaker line (td:0)
P4: `reviewer.agent.md` pipeline_position table uses "batch review cycle" for loop-breaker row (td:0)
P5: `agent-broad-audit.prompt.md` rejection-routing table uses "batch review cycle" for reviewer loop-breaker row (td:0)
P6: Diff of all 4 files shows only loop-breaker terminology changes and cycle-3 row addition (td:0)

## Scope

**In scope:** Terminology update in 4 files, cycle-3 escalation row addition
**Out of scope:** Reviewer rewrite (B1, done), other protocol sections

## Files to modify

1. `share/skills/r-pipeline-protocol/SKILL.md` — Confidence Thresholds table
2. `share/skills/w-code-review/SKILL.md` — FAIL routing section
3. `share/agents/reviewer.agent.md` — pipeline_position table
4. `share/prompts/agent-broad-audit.prompt.md` — rejection-routing table