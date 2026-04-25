---
id: 1127
title: Fix release outcome to append notes per Brief B D52
status: research
priority: important
created: '2026-04-25 18:07:12.599139+00:00'
updated: '2026-04-25 18:07:12.599139+00:00'
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set."
Current implementation routes `release` through `release_task()` which does NOT append notes.
This is a D52 implementation bug separate from the `fail` outcome restoration (#1125).

Research doc: `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` (parent #1124, defect D2)

## Acceptance Criteria

- [ ] AC1: `AgentView.end_work(outcome="release", note="some note")` on a claimed task appends the timestamped note to the task body before releasing the claim
- [ ] AC2: `AgentView.end_work(outcome="release")` on an unclaimed task remains a pure no-op per D55 (no note appended, no `updated` advanced)
- [ ] AC3: The note-appending for `release` uses the same timestamped format as other outcomes (ISO 8601 prefix)
- [ ] AC4: Activity event for `release` remains `"released by agent"` (no change to session classification)

## Implementation Notes
- Option A: Add `release` to `KanbanEngine.end_work` valid_outcomes, remove `if outcome != "release"` guard on note logic, route AgentView `release` through `engine.end_work` instead of `engine.release_task`
- Option B: Modify `release_task()` to accept an optional `note` parameter
- Option A is preferred (atomic single-write, consistent with other outcomes)
- Affected files: `engine.py` (AgentView routing + raw engine), tests

## Research
- Research doc: .owlbear/research/1127-release-note-appending.md
- Sources: 12 studied, 8 high-relevance
- Recommendation: Option C — extract `_append_timestamped_note` helper, call from both `end_work` and `release_task` (confidence: 0.75)
- Follow-up tasks created: none (this task moves to backlog)
- Decision requests: none (T1 — autonomous bug fix)

## Challenge Results
- Challenger: reconsider (confidence in original Option B: 0.55)
- Key challenges: DRY risk underpriced, helper extraction captures best of both, dead guard evidence
- Researcher response: revised from B to C — accepted DRY concern and helper proposal
