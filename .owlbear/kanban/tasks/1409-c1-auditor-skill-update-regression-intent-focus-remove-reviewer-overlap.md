---
id: 1409
title: 'C1: Auditor skill update — regression + intent focus, remove reviewer overlap'
status: review
priority: needed
created: 2026-05-07T23:16:25.240390+00:00
updated: 2026-05-09T04:13:06.004814+00:00
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
[[2026-05-09]]
## Planning

Created follow-up task: #1461 — "C1-impl: Apply 4-pillar auditor model to w-task-verification and auditor.agent.md"
- Status: backlog
- Priority: needed
- Parent: #1403
- Depends on: #1409
- Tags: pipeline, ws-roles, scope:agents

Single-task shortcut — no TDD pairing required (skill/agent file updates, not feature implementation).
[[2026-05-09]]
## Research\n- Research doc: .owlbear/research/auditor-skill-update-1409.md\n- Sources: 5 studied, 5 high-relevance (all codebase — current auditor skill, post-B1 reviewer skill, pipeline protocol, agent def, brief)\n- Recommendation: 4-pillar auditor model (regression detection, intent verification, architect quality scoring, commit integrity). Remove AC spot-check, AC deviations, file-exists, per-AC evidence table — all now reviewer scope post-B1. Updated scoring rubric adds regression/intent deductions, removes AC-line deductions. Confidence: .85\n- Follow-up: #1461 (implementation at backlog)\n- Challenge: skipped (T1 autonomous, overlap analysis mechanical)
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (skill/agent file updates) — no tests applicable.
- All AC lines target `w-task-verification` skill content and auditor agent file (markdown files). No testable Python interfaces exist.
- Architect note in body confirms: "Single-task shortcut — no TDD pairing required (skill/agent file updates, not feature implementation)."
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Scope confirmed: AC targets skill/agent markdown updates only.
- Passing through to review per `w-tdd-green` Step 0a.