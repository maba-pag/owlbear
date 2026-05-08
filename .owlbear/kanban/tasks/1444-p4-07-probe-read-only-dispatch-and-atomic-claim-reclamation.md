---
id: 1444
title: 'P4-07: Probe read-only dispatch and atomic claim reclamation'
status: todo
priority: needed
created: 2026-05-08T19:32:00.424170+00:00
updated: 2026-05-08T21:51:00.789448+00:00
tags:
- phase-4
- scope:kanban
- type:test
- verification-probe
- dispatch
- claims
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: scratch-board probes for pick_tasks read behavior and start_work claim reclamation.
Out of scope: resolve_drs tool design, Cockpit maintenance UI, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a scratch-board dispatch probe with an unblocked backlog task whose claimed_at is older than claim timeout; pick_tasks must treat the task as dispatch-eligible while leaving the task file content unchanged.
2. Test-writer records a pending-DR probe where a response-approved pending DR and its linked blocked task remain unchanged after pick_tasks.
3. Test-writer records a start_work probe where an expired claimed_at is cleared and replaced with the caller's new claimed_at through a compare-and-swap write.
4. Test-writer records before and after file mtime or content evidence for task and decision files touched by the probes.
5. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and contract inspection.
[[2026-05-08]]


## Corrected Acceptance Criteria (supersedes original AC)

1. **Dispatch-eligibility probe:** The expected post-#1445 contract is: given an unblocked backlog task whose `claimed_at` is older than the 1h claim timeout, `AgentView.pick_tasks` returns the task in a dispatch wave and leaves the task file unchanged on disk. Current gap: `pick_tasks` calls `engine.list_tasks(unclaimed=True)` (agent_view.py:388) which filters out all non-null `claimed_at` via the `unclaimed` filter in `engine.py:578+688` — expired-claim tasks are currently excluded from dispatch. (td:0)

2. **Pending-DR immutability probe:** The expected post-#1445 contract is: given a response-approved pending DR in `decisions/pending/` and its linked blocked task, `AgentView.pick_tasks` leaves the DR file in `decisions/pending/`, the task body unchanged, and the task `blocked` field unchanged. Current gap: `pick_tasks` calls `resolve_pending_drs()` (agent_view.py:312) which moves DR files from `pending/` to `resolved/`, appends a response summary to the task body, and sets `blocked=False` via `edit_task` — all write side effects in `decisions.py:143+`. (td:0)

3. **Start_work CAS probe:** The start_work claim reclamation contract (current and target): given a task with expired `claimed_at`, `start_work` clears the expired claim via `write_task_if_unchanged` and writes the caller's new `claimed_at` in a second CAS write, with up to 4 stale retries (`engine.py:1354–1390`). The on-disk task file must reflect the new `claimed_at` and `updated` fields. Current state: this behavior already exists and is the baseline contract that #1445 preserves. (td:0)

4. **Evidence specification for #1445:** The #1445 builder must capture before/after file content evidence (SHA-256 hash or byte comparison) for task files and decision files touched by dispatch (AC 1, AC 2) and claim operations (AC 3), proving read-only behavior where required and correct mutation where expected. (td:0)

5. No pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and contract inspection. (td:0)
[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: define probe specifications for dispatch eligibility, DR immutability, and claim reclamation contracts |
| Interface clarity | PASS (after refinement) | Corrected AC specifies target contracts with codebase-referenced current gaps; maps cleanly to #1445 AC2-AC4 |
| Dependency correctness | PASS | No dependencies — correct as root probe. #1445 depends on this task for probe artifacts |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as contract specification for #1445 RED/GREEN |
| KISS/YAGNI | PASS | Minimal scope — notes-only deliverable |
| Premise challenge | PASS | Probes define the dispatch/claim contract before #1445 implementation; existing tests cover start_work CAS mechanics but not the deployment-readiness specification |
| Pattern consistency | PASS | Follows probe-before-implementation pattern from siblings #1438, #1440, #1442 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | kanban domain only (scope:kanban) |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### Corrected AC Summary
- AC1 (dispatch eligibility): Documents target contract (expired claims in dispatch waves, files unchanged) and current gap (unclaimed=True filter excludes all non-null claimed_at). Maps to #1445 AC2.
- AC2 (pending-DR immutability): Documents target contract (DRs and blocked tasks unchanged after pick_tasks) and current gap (resolve_pending_drs writes to both DR files and task files). Maps to #1445 AC3.
- AC3 (start_work CAS): Documents existing baseline contract (two-step CAS with 4 stale retries). Maps to #1445 AC4. Already covered by existing tests but documented here as deployment-readiness specification.
- AC4 (evidence spec): Defines SHA-256/byte-comparison evidence requirements for #1445 builder.
- AC5: No pytest/vitest gate — consistent with all Phase 4 probes.

### Codebase Context
- pick_tasks: `serve/kanban/src/owlbear_kanban/agent_view.py:299` — calls list_tasks(unclaimed=True), resolve_pending_drs()
- list_tasks unclaimed filter: `engine.py:578+688` — filters claimed_at != None
- resolve_pending_drs: `decisions.py:143+` — moves DR files pending→resolved, appends to task body, clears blocked
- start_work/claim_task: `engine.py:1327+` — two-step CAS via write_task_if_unchanged (storage.py:453)
- Claim timeout: `models.py:132` — default "1h"
- CAS retries: `engine.py:76` — _MAX_CLAIM_STALE_RETRIES = 4
- Existing CAS coverage: `serve/kanban/tests/test_engine_move_claim.py:567`, `test_engine_move_claim_1075.py:194`

### Dependency Analysis
- No inbound dependencies (root probe). Correct.
- Outbound: #1445 depends on #1444 for probe artifacts (AC5: "using the probe artifacts from #1444").
- #1456 consolidation test expects dispatch walkthrough evidence — #1444 AC1+AC2 provide the specification.

### Challenge Results
- Challenger: SKIPPED — all AC lines are td:0 (Step 2.1 gating rule)

### Test Depth
- All AC lines: td:0 (probe notes, no test code)
- Max depth: td:0
- Test-writer: SKIP (type:test pass-through)

### Verdict: APPROVE
### Action Taken: Corrected AC to document both target contracts and current gaps with codebase evidence. Kept type:test tag and notes-based probe format consistent with sibling probes #1438, #1440, #1442. Advanced to todo.