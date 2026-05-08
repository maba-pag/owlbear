---
id: 1409
title: 'C1: Auditor skill update — regression + intent focus, remove reviewer overlap'
status: research
priority: needed
created: 2026-05-07T23:16:25.240390+00:00
updated: 2026-05-07T23:18:14.519704+00:00
tags:
- pipeline
- ws-roles
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

P1: `w-task-verification` skill updated to focus on regression detection and intent verification
P2: Overlap with reviewer removed — auditor no longer re-checks completeness (reviewer's job post-B1)
P2: Architect-quality scoring retained in auditor skill
P2: Auditor positioned as pipeline-end integrity gate (runs full test suite to catch fabricated evidence)
P3: Verification by diff comparison of modified skill file; confirm no overlap with B1's reviewer scope

## Scope

**In scope:** Auditor skill update, remove reviewer-overlapping checks
**Out of scope:** Reviewer rewrite (B1), role boundary docs (C3)