---
id: 1461
title: 'C1-impl: Apply 4-pillar auditor model to w-task-verification and auditor.agent.md'
status: backlog
priority: needed
created: 2026-05-09T03:30:08.726831+00:00
updated: 2026-05-09T03:30:26.246653+00:00
tags:
- pipeline
- ws-roles
- scope:agents
parent: 1403
depends_on:
- 1409
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)
Research: `.owlbear/research/auditor-skill-update-1409.md`

## Acceptance Criteria

P1: `w-task-verification` skill updated to 4-pillar model (regression detection, intent verification, architect quality scoring, commit integrity)
P1: Overlapping checks removed from auditor skill — no AC spot-check, AC deviations, file-exists checks, or per-AC evidence table (reviewer's domain post-B1)
P2: Scoring rubric updated — AC-line deductions removed, regression/intent deductions added
P2: `auditor.agent.md` persona and boundaries updated to reflect pipeline-end integrity gate role
P3: Diff comparison against B1's `w-code-review` scope confirms no overlap between auditor and reviewer

## Scope

**In scope:** Update `share/skills/w-task-verification/SKILL.md` (4-pillar model, remove overlapping checks, update scoring rubric); update `share/agents/auditor.agent.md` (persona, boundaries)
**Out of scope:** Reviewer rewrite (B1), role boundary docs (C3), any changes to `w-code-review`