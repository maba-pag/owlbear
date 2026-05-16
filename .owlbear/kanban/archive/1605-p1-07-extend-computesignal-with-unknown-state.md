---
id: 1605
title: 'P1-07: Extend computeSignal with unknown state'
status: archived
priority: important
created: 2026-05-16T03:36:07.039801+00:00
updated: 2026-05-16T07:51:20.823482+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1599
ac:
  - computeSignal(null) and computeSignal({}) return an object with state 
    'unknown'
  - Existing 5-state behavior unchanged for valid inputs 
    (green/yellow/red/gray/stale)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: duplicate
archival_refs:
  - 1599
---
Brief: see parent #1590.

Add 'unknown' state for malformed/missing inputs.

Scope: computeSignal extension only.
Out of scope: Formatting utilities, token migration, layout.

[[2026-05-16T09:10:47+02:00]]
## Research
- Research doc: .owlbear/research/compute-signal-unknown-state-impl.md
- Sources: 4 studied, 4 high-relevance
- Finding: Implementation already complete — done in #1599's builder phase (commit a6e26299). CardSignal type extended, guard clause added, 23/23 tests pass.
- Both ACs have stale wording (\"object\" should be \"string\"; color names should be state names) — same corrections applied in #1599's research.
- Recommendation: archive as superseded by #1599 (confidence: 0.95)
- Challenge: skipped (factual finding, not a recommendation)
- No follow-up tasks — no remaining implementation work
- Commit: ea19b261

[[2026-05-16T09:24:53+02:00]]
## Architecture Review
### Verdict: ARCHIVE (superseded by #1599)

Implementation was completed during #1599's builder phase (commit a6e26299). Codebase verification confirms:

| AC Line | Status | Evidence |
|---------|--------|----------|
| AC-1: computeSignal(null) and computeSignal({}) return unknown | SATISFIED | Guard clause at computeSignal.ts:11-12 returns 'unknown' for null/undefined/missing-id. 6 dedicated tests pass. |
| AC-2: Existing 5-state behavior unchanged | SATISFIED | Original 17 tests pass; 23/23 total. Precedence logic untouched. |

### Notes
- Both ACs have stale wording (\"object\" should be \"string\"; color names should be state names) — moot since work is complete.
- Researcher recommendation to archive as superseded (confidence 0.95) confirmed by direct code inspection.
- No challenger dispatch needed — factual verification, not a design decision.
- Routing: skip pipeline stages (todo/in-progress/review/docs) — no remaining work. Direct to done for auditor archival as duplicate of #1599.

[[2026-05-16T09:51:12+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4627 passed, 237 failed (all pre-existing: cockpit_view, engine_accessor_migration, server, ideation_diagram), 14 skipped, lint clean
- regression verdict: PASS (no task-caused regressions)

### Intent Verification
- scope alignment: PASS (research doc in correct cockpit frontend domain)
- purpose match: PASS (researcher and architect independently verified implementation already completed in #1599 commit a6e26299)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer (N/A, superseded task)

### Architect Quality: 2/5
ACs factually incorrect: AC-1 says \"return an object\" (function returns string), AC-2 says \"green/yellow/red/gray/stale\" (actual states are dr-pending/blocked/claimed/deps-unmet/ready). Architect correctly identified task as superseded but original ACs would have misled an implementer. Follow-up #1631 created for planner AC accuracy calibration.

### Commit Integrity
- upstream commit presence: PASS (ea19b261 research doc for #1605; a6e26299 implementation attributed to #1599)
- kanban commit packaging: pending (this archival)

### Deduction Breakdown
- AC quality score 2 (lte 3): -.03

### Confidence: .97
### Action: ARCHIVE (superseded by #1599)
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | planner | Review AC accuracy for PDS decomposition batch | #1590 child tasks | AC-1 wrong return type, AC-2 wrong state names |
