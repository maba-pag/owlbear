---
id: 1411
title: 'C3: Role boundary documentation — in-scope/out-of-scope for each agent skill'
status: research
priority: important
created: 2026-05-07T23:16:25.269760+00:00
updated: 2026-05-07T23:18:14.524838+00:00
tags:
- pipeline
- ws-roles
- scope:agents
parent: 1403
depends_on:
- 1405
- 1406
- 1407
- 1409
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: Each pipeline agent skill file contains an explicit "In Scope / Out of Scope" section
P2: Agents covered: planner, architect/challenger, test-writer, builder, reviewer, auditor, doc-writer
P2: Boundaries are consistent across agents — no overlapping mandates, no uncovered gaps
P2: Boundaries reflect the post-rethink division of responsibilities (A2, A3, B1, C1 changes incorporated)
P3: Verification by artifact inspection of each agent's skill file; cross-reference check for consistency

## Scope

**In scope:** Adding boundary sections to all pipeline agent skills
**Out of scope:** Changing agent behavior (already done in A2, A3, B1, C1)