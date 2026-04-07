---
id: 673
title: 'P4-14: Add Brief-from-parent convention to pipeline skill files'
status: backlog
priority: nice-to-have
created: 2026-04-07T05:38:11.8618391+02:00
updated: 2026-04-07T06:03:51.355692+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:integrate'
depends_on:
    - 653
class: standard
---

## Acceptance Criteria

- [ ] w-task-decomposition Step 1 updated: detect Brief sections in parent task body; include `Brief: see parent #{id}` reference in each child task body
- [ ] w-orchestration Context Budget section updated: note that Brief context is available to pipeline agents via parent task lookup (orchestrator does not use it directly)
- [ ] r-pipeline-protocol Reading Rules updated: add Brief context (via parent task) to architect/builder reading sources
- [ ] w-arch-review Step 1 updated: parent task Brief lookup when `parent` field is set; Brief sections inform AC evaluation and builder guidance
- [ ] All updates use graceful-skip patterns ("when present", "if available") — no breaking changes
- [ ] No source code changes — markdown skill files only

## Context

Research: `.owlbear/research/pipeline-brief-context-integration.md`
Parent task: #653. This task implements the actual skill file edits identified in the research.

The Brief artifact (problem, outcomes, approach, scope, investment tier) is embedded in a parent kanban task body by the ideator at M6. Child tasks created by the planner carry task-specific AC but lose this originating context. These skill updates tell pipeline agents where to find Brief context and how to use it — all additive, all optional.

[[2026-04-07]] Tue 06:03
## Research
- Research doc: .owlbear/research/pipeline-brief-context-integration.md (produced by parent #653)
- Sources: 8 studied, 5 high-relevance (≥0.90) — all internal workspace files
- Recommendation: Hybrid parent-lookup approach — agents call `show_task(parent_id)` when `parent` is set; planner includes `Brief: see parent #{id}` in child tasks. Update 4 skill files: w-task-decomposition, w-orchestration, r-pipeline-protocol, w-arch-review. All additive, graceful-skip when absent. (confidence: .82)
- Follow-up tasks created: none — this task IS the implementation follow-up from #653
- Decision requests: none (T1 — autonomous, documentation-only)

## Validation Pass
Existing research doc confirmed current against codebase state (2026-04-07). All 4 target skill files verified — none have been updated yet. Dependency #653 done. No codebase drift detected.

## Challenge Results
- Challenger: FALLBACK — validation pass on existing T1 research; no new recommendation to challenge
- Confidence in original: .82
- Key challenges: none
- Researcher response: N/A

## Notes
- Task should carry `docs` pass-through tag — no testable Python code; markdown skill file edits only
- Research doc §3D item 5 mentions optional w-research update (parent Brief lookup for scope focus) — not in AC, could be a minor enhancement later
