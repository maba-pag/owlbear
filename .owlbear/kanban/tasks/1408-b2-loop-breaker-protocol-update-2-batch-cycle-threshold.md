---
id: 1408
title: 'B2: Loop-breaker protocol update — 2-batch-cycle threshold'
status: todo
priority: important
created: 2026-05-07T23:16:25.227004+00:00
updated: 2026-05-09T03:32:00.924610+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
parent: 1403
depends_on:
- 1407
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `r-pipeline-protocol` loop-breaker section updated from 3-FAIL threshold to 2-batch-cycle threshold
P2: Before state: loop-breaker triggers after 3 consecutive FAILs. After state: loop-breaker triggers after 2 batch review cycles
P3: Verification by diff comparison of modified protocol file

## Scope

**In scope:** Loop-breaker threshold change in `r-pipeline-protocol`
**Out of scope:** Reviewer rewrite (B1), other protocol sections
[[2026-05-09]]
## Planning

Created 1 follow-up task:

| ID | Title | Status | Priority | Parent | Tags |
|----|-------|--------|----------|--------|------|
| #1462 | B2-impl: Update loop-breaker terminology to batch-review-cycle and add cycle-3 escalation | research | important | #1403 | pipeline, ws-reviewer, scope:agents, agent |

Single atomic task — terminology update across 4 .md agent/skill files + cycle-3 escalation row addition. No TDD pair needed (documentation-only change, td:0 throughout).
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/loop-breaker-batch-cycle-update.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Terminology update across 4 files (FAIL → batch review cycle) + cycle-3 architect escalation row (confidence: 0.90)

Key finding: Commit 96ed7280 (April 29) already changed the numeric threshold from 3→2. The remaining work is a terminology update to align wording with the post-B1 batch review model, plus adding the cycle-3 architect escalation from synthesis rec #7.

Follow-up: #1462 (B2-impl) at research — covers all 4 files.