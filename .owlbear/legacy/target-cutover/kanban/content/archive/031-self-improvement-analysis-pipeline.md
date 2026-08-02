---
id: 31
title: Self-improvement analysis pipeline
status: archived
priority: medium
created: 2026-03-26 18:05:35.109813+01:00
updated: 2026-04-04 07:09:50.470155+02:00
started: 2026-04-04 07:09:24.389261+02:00
completed: 2026-04-04 07:09:24.389261+02:00
tags:
- phase-2
- scope:orchestrator
- type:build
depends_on:
- 21
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Build analysis on top of the audit log to generate improvement proposals for agents, skills, and workflows.

## Acceptance Criteria
- [ ] Read audit log data (dispatch history, outcomes, durations, errors)
- [ ] Detect patterns: high error rates per agent, slow tasks, repeated failures
- [ ] Generate improvement proposals (which agent, what to change, evidence)
- [ ] Output as structured data (JSON or markdown report)
- [ ] No autonomous mutation - proposals are review artifacts only
- [ ] Triggerable via CLI: owlbear analyze (not automatic)
- [ ] Unit tests for analysis logic

## Context
Depends on O3 (audit log). v1 had ImprovementProposals module that analyzed EventStore data. v2 simplifies to: read audit log, find patterns, suggest changes. Human reviews and applies.

[[2026-03-30]] Mon 15:53
## Architecture Review
**Verdict:** BLOCK (stale parent task, decomposed into #179 + #180)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Read audit log data | Covered by #179 AC (analyze() reads DispatchEvent + CompletionEvent) | Decomposed |
| Detect patterns: error rates, slow tasks, repeated failures | Covered by #179 AC (4 detectors with specific thresholds) | Decomposed |
| Generate improvement proposals | Covered by #179 AC (AnalysisProposal Pydantic model, 6 fields) | Decomposed |
| Output as structured data (JSON or markdown) | Covered by #179 AC (JSON default + markdown flag) | Decomposed |
| No autonomous mutation | Covered by #179 AC (no side effects, no file writes) | Decomposed |
| Triggerable via CLI: owlbear analyze | Covered by #180 AC (python -m owlbear_orchestrator.analyze) | Decomposed |
| Unit tests for analysis logic | Covered by #179 AC (synthetic JSONL fixtures) | Decomposed |

### Architecture Notes
Task #31 was the original research umbrella. The researcher completed research (docs/research/self-improvement-analysis-pipeline.md) and created two concrete follow-ups: #179 (analysis module, backlog) and #180 (CLI entrypoint, ideation). A second research pass (docs/research/analysis-module-implementation-readiness.md) confirmed implementation readiness for #179.

All seven AC lines map 1:1 to child task AC. No residual scope remains on #31. Same stale-parent pattern as #21.

Recommend direct archival by auditor or planner.

### Dependencies
- #21 (Build audit log): archived, satisfied
- #179 depends on #21 (correct)
- #180 depends on #179 (correct chain)

[[2026-04-04]] Sat 06:46
Archived: stale parent — all AC decomposed into #179 + #180.
