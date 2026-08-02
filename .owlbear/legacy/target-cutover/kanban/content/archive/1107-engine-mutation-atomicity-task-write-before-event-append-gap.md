---
id: 1107
title: 'Engine mutation atomicity: task-write-before-event-append gap'
status: archived
priority: medium
created: 2026-04-22T22:41:43.892451+00:00
updated: 2026-04-23T09:25:37.544032+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-22]]
## Research

**Duplicate of #1104** — fully superseded.

### Validation pass (w-research Step 1.5)

Existing research doc `.owlbear/research/engine-write-before-log-atomicity-1104.md` covers this exact topic. Codebase validation confirms all findings still hold:

- All 6 engine mutators follow `write_task()` → `_emit_event()` with zero error handling (engine.py L820–1126)
- Archive paths have `_move_file` between write and emit (move_task L851–860, end_work L1065–1078)
- `_emit_event()` (L1174–1197) propagates exceptions uncaught
- No existing tests cover emit failure scenarios

### #1104 status
- Status: `in-progress` (builder phase)
- Design decision: Rollback (Option A) — locked by architect
- Tests: 11 tests written in `serve/kanban/tests/test_engine_atomicity_1104.py`
- Implementation: covers both RED tests and GREEN implementation as TDD unit

### Related superseded tasks
- #1105: deleted (test-writing stub, absorbed by #1104)
- #1106: `todo`, marked MERGE/superseded by #1104 architect review

### Disposition
This task (#1107) describes the identical concern as #1104. No independent deliverables exist. Recommend architect advance directly to `done` as duplicate.

- Follow-up tasks created: none (all work owned by #1104)
- Decision requests: none
- Tier: T1 — deduplication
- Sources: 0 new (existing research doc validated)
- Confidence in duplicate finding: .98
[[2026-04-22]]
## Architecture Review

### Verdict: MERGE (superseded)

This task is a verified duplicate of #1104 ("Engine write-before-log atomicity: append-failure resilience tests"), which is currently `in-progress` with:
- Approved architecture review (rollback design decision locked)
- 11 failing tests in `serve/kanban/tests/test_engine_atomicity_1104.py`
- Refined AC covering all 6 mutators, archive-path rollback, sweep per-task handling
- Builder phase active

### Verification
- #1104 status: `in-progress` (builder phase)
- #1104 scope: covers BOTH tests and implementation as TDD unit — identical to #1107's concern
- #1106 status: `in-progress` — already processed as superseded merge artifact via same path
- #1107 body references the same research doc, same engine.py lines, same 6 mutators
- Zero independent deliverables

### Evaluation
No full Step 2 criteria evaluation needed — task has no independent scope. All architectural analysis was performed during #1104's architecture review (2026-04-22).

### Challenge Results
- Challenge: SKIPPED — no independent verdict to challenge; merge already completed on #1104

### Action Taken
Advanced as superseded merge artifact. All deliverables owned by #1104. Downstream agents: no work required — pass through.
[[2026-04-23]]
## Test-Writer Notes
- Non-implementation pass-through: task is a verified duplicate of #1104, which already owns 11 failing tests in `serve/kanban/tests/test_engine_atomicity_1104.py`.
- Architect verdict (2026-04-22): MERGE/superseded — no independent deliverables. Explicit directive: "Downstream agents: no work required — pass through."
- No tests written. All AC coverage owned by #1104.
[[2026-04-23]]
## Archived
Confirmed duplicate of #1104. Research, architect, and test-writer all explicitly noted "no work needed, pass through." Zero independent deliverables. Archived during manual board triage.