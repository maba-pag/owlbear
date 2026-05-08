---
id: 1406
title: 'A3: Architect/challenger skill update — AC validation via h-ac-quality, consolidation-test
  backstop'
status: research
priority: needed
created: 2026-05-07T23:16:25.200360+00:00
updated: 2026-05-07T23:18:14.496518+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
parent: 1403
depends_on:
- 1404
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `w-arch-review` skill updated — challenger validates AC quality using `h-ac-quality` rules during architecture review
P2: Challenger detects missing consolidation-test tasks: if task has ≥2 sibling implementation tasks under same parent AND no sibling consolidation-test task → flag for planner
P2: Architect acts on AC quality only when challenger flags issues (checker subagent pattern)
P2: `h-ac-quality` referenced in architect/challenger required reading or critical rules
P3: Verification by diff comparison of modified skill files

## Scope

**In scope:** `w-arch-review` skill update, challenger expansion for AC validation and consolidation-test detection
**Out of scope:** h-ac-quality content (A1), planner changes (A2), reviewer changes (B1)