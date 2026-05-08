---
id: 1377
title: 'P2-02: Implement Cockpit task detail context model'
status: backlog
priority: critical
created: 2026-05-06T01:04:31.145299+00:00
updated: 2026-05-08T14:12:47.440034+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- model
parent: 1363
depends_on:
- 1376
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the Cockpit task detail frontend model needed for safe detail-view decisions.

## Problem Evidence
- DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by.
- Dependency and parent context is not available enough for action gating and edit decisions.
- Missing context can be confused with a user clearing a value.

## Acceptance Criteria
- The task detail frontend model matches backend task detail fields needed for Cockpit decisions, including claim state.
- Dependency and parent context from the backend is preserved for UI decisions wherever the backend exposes it.
- Optional or unavailable context has an explicit state and is not converted into a clearing edit.
- Existing valid task fetch, edit, and move flows continue to work with the expanded model.
- The implementation satisfies #1376 without adding action-gating or validation behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail model, parsing, and state propagation.
- Out of scope: edit validation, dirty-state UX, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1376.

[[2026-05-08]]
## Architecture Review

### Verdict: REJECT

### Findings

1. **Dependency #1376 (test task) does not exist.** The task declares `depends_on: [1376]` and references "Test task: #1376" but no task with that ID exists on the board. The TDD pipeline cannot function without its RED-phase counterpart.

2. **Problem Evidence is stale.** The frontend `TaskDetail` interface (DetailTab.tsx L16-31) already includes:
   - `claimed: boolean`
   - `claimed_at: string | null`
   - `dep_status: string | null`
   - `parent: number | null`
   - `depends_on: number[]`
   
   The task claims "DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by" — this is factually incorrect for `claimed` and `claimed_at`.

3. **`claimed_by` is deliberately omitted by the backend.** The kanban engine's `TaskSummary._coerce_claimed` validator (models.py L497-505) explicitly `data.pop("claimed_by", None)`. The field is never exposed in the API response. The frontend cannot model a field the backend deliberately drops.

4. **AC may already be satisfied.** Given that the frontend model already has claim state, dependency context, and parent context — all typed as `T | null` (explicit absent state, not `undefined`) — the AC lines appear to describe current behavior.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused on model expansion |
| Interface clarity | FAIL | AC references fields ("needed for Cockpit decisions") without specifying which are actually missing |
| Dependency correctness | FAIL | #1376 does not exist |
| TDD compliance | FAIL | Test task missing from board |
| Premise challenge | FAIL | Frontend model already has the claimed/dependency fields cited as missing |

### Required Research
- Identify what fields are genuinely missing from the frontend model vs the backend response (candidates: `archival_reason`, `archival_refs`, `guidance`, `missing_sections`)
- Determine whether any of those are needed for "safe detail-view decisions"
- Create the test task or redefine the dependency chain
- Rewrite Problem Evidence to reflect the current codebase state
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1377-task-detail-context-model.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Close as no-op (confidence: 0.95)

### Key findings
1. Task #1376 (the TDD test counterpart) was completed and archived — including the GREEN implementation (commit 216061a8) that added claim/dep_status fields to DetailTab.tsx.
2. All 15 tests in TaskDetailModel_1376.test.tsx pass against the current codebase.
3. Frontend TaskDetail already has every field the AC describes as "missing": claimed, claimed_at, dep_status, parent, depends_on.
4. Backend-only extras (archival_reason, archival_refs, guidance, missing_sections) are not needed for detail-view decisions.
5. #1377 is a no-op — its work was done during #1376's pipeline traversal.

### Follow-up
- Remove #1377 from #1378's depends_on to unblock Phase 2 downstream chain.
- Archive #1377 — no implementation changes needed.