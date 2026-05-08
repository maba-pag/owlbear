---
id: 1408
title: 'B2: Loop-breaker protocol update — 2-batch-cycle threshold'
status: research
priority: important
created: 2026-05-07T23:16:25.227004+00:00
updated: 2026-05-07T23:18:14.512476+00:00
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