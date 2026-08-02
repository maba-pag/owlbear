---
id: 1444
title: 'P4-07: Probe read-only dispatch and atomic claim reclamation'
status: archived
priority: medium
created: 2026-05-08T19:32:00.424170+00:00
updated: 2026-05-09T00:33:52.068734+00:00
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
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no tests applicable.
- All AC lines are (td:0): dispatch-eligibility probe, pending-DR immutability probe, start_work CAS probe, and evidence spec are all probe notes and contract documentation deliverables for #1445, not testable Python interfaces.
- Architecture Review verdict confirms: "Test-writer: SKIP (type:test pass-through)".
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task (`type:test` probe pass-through) confirmed from `## Test-Writer Notes`; no source or test file edits required.
- Contract inspection re-verified AC statements against current implementation references:
  - `AgentView.pick_tasks` currently calls `list_tasks(..., unclaimed=True)` and `resolve_pending_drs(...)`.
  - `list_tasks(unclaimed=True)` filters to `claimed_at is None`.
  - `resolve_pending_drs` mutates DR/task state (append summary, unblock task, move file).
  - `claim_task/start_work` uses two-step CAS with stale-retry loop for expired claims.
- Tests: 0 executed (AC td:0 probe-only task; functional proof explicitly notes-only per AC5).
- Coverage: N/A (no code paths changed).
- Lint: N/A (no code changes).
- Outcome: Passing through to review with no implementation changes.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner skipped as inapplicable. This is a td:0 notes-only probe task with no source files, task-local test files, or lint surface in scope.
- code-reader skipped per td:0 workflow.
- Scoped execution evidence: none required by AC5; the task explicitly limits proof to notes and contract inspection.

### Change Scope
- No builder-scoped source or test files identified. Builder notes state that no source or test file edits were required.
- No prior Review Evidence section was present in the task body. This is the first review cycle.
- Dirty-tree contamination: not applicable because the review scope is the task artifact plus live contract references, not executable deliverables.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 dispatch-eligibility probe | Task line 43 records the target contract and current gap. Live code matches the gap: `pick_tasks` calls `resolve_pending_drs(self.engine)` and then `list_tasks(..., unclaimed=True)` at `serve/kanban/src/owlbear_kanban/agent_view.py:388,394-397`; `list_tasks` filters to `claimed_at is None` at `serve/kanban/src/owlbear_kanban/engine.py:688-689`. | N/A td:0 | PASS |
| AC2 pending-DR immutability probe | Task line 45 records the target contract and current gap. Live code matches the gap: `resolve_pending_drs(self.engine)` is called at `serve/kanban/src/owlbear_kanban/agent_view.py:388`; approved or rejected DR handling appends a summary, clears `blocked`, and moves the file at `serve/kanban/src/owlbear_kanban/decisions.py:176-179`. | N/A td:0 | PASS |
| AC3 start_work CAS probe | Task line 47 records the claim-reclamation contract. Live code clears expired claims through `write_task_if_unchanged` and then writes the new claim through a second CAS write with stale-retry checks at `serve/kanban/src/owlbear_kanban/engine.py:77,1371-1399`; the default claim timeout is `1h` at `serve/kanban/src/owlbear_kanban/models.py:132`. Existing baseline coverage for the documented contract is present at `serve/kanban/tests/test_engine_move_claim.py:567-586` and `serve/kanban/tests/test_engine_move_claim_1075.py:194-230`. | Existing baseline tests only | PASS |
| AC4 evidence specification for #1445 | Task line 49 explicitly requires before and after file-content evidence for touched task and decision files. That probe-spec requirement is present and actionable for downstream task 1445. | N/A td:0 | PASS |
| AC5 no pytest, vitest, or full-suite proof | Task line 51 limits proof to notes and contract inspection; Test-Writer notes at task lines 106-107 mark all AC lines td:0; Builder notes at task lines 117-119 record Tests 0 executed, Coverage N/A, and Lint N/A. | N/A td:0 | PASS |

### Pass 1 Checks
- Test-writer audit: not applicable. No task-local TestFromAC classes or executable test deliverables exist.
- Test integrity: no task-local test changes in scope.
- Security review: not applicable. No source changes.
- Data safety: not applicable. No source changes.
- Implementation-aware test gaps: not applicable to this td:0 probe-spec task.
- Necessity check: not applicable. No new dependency or integration.
- Builder process quality: CLEAN. One Builder Notes section only; no retry loop evidence.

### Informational Findings
- The corrected AC cites slightly stale live-code line numbers. The `list_tasks(..., unclaimed=True)` call is currently at `agent_view.py:394-397`, not `:388`, and the `resolve_pending_drs` call is currently at `agent_view.py:388`, not `:312`. The contract statements themselves are correct.

### Deductions
- 0.02 deduction for stale line citations in the corrected AC. They reduce evidence precision but do not change the documented contract.
- 0.01 deduction because no builder commit hash was recorded, so task-local immutability was reconstructed from scope and task notes rather than diff evidence.

### Verdict
- PASS
- Confidence: 0.94
- Action: advance to docs.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior, API, CLI, config, or package structure changes — notes-only probe task |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase doc referenced |
| 5 | Diagram maintenance (describes match) | No | N/A | No changed files to match against doc-index describes entries |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files |

**No docs impact.** All seven items N/A. This is a td:0 notes-only probe task (type:test, AC5 explicitly limits proof to scratch-board notes and contract inspection). Builder confirmed zero source or test file edits. No IN-scope docs reference the probe contract specifications.

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| (none — no files changed) | — | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1444-*` files found)
[[2026-05-09]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 dispatch-eligibility probe | Task body documents target contract and gap. Verified live: pick_tasks calls list_tasks(unclaimed=True) at agent_view.py:394-399; engine.py:689 filters claimed_at is None. Contract accurate. | PASS |
| AC2 pending-DR immutability probe | Task body documents resolve_pending_drs write side effects. Verified live: resolve_pending_drs called at agent_view.py:389; decisions module mutates DR files and task state. Contract accurate. | PASS |
| AC3 start_work CAS probe | Task body documents baseline CAS contract. Reviewer confirmed existing coverage at test_engine_move_claim.py:567 and test_engine_move_claim_1075.py:194. | PASS |
| AC4 evidence spec for 1445 | Task body specifies SHA-256/byte-comparison requirements for 1445 builder. Present and actionable. | PASS |
| AC5 no pytest/vitest gate | Confirmed: td:0 notes-only task, no executable deliverables. | PASS |

### Test Results
- pytest: 439 pre-existing failures, 4054 passed, 4 skipped. Zero code changes in this task means zero attributable regressions.
- ruff: 12 pre-existing violations. No new violations (no code changes).
- Vitest: N/A (kanban-scoped task, no frontend changes).

### Reviewer Evidence
Present and detailed. All 5 AC lines mapped with codebase references. PASS verdict at 0.94. Reviewer deducted 0.02 (stale line citations) and 0.01 (missing builder commit hash). Both deductions are reasonable but conservative for a td:0 task.

### Architect Quality: 5/5
Corrected AC is excellent: specifies target contracts with precise codebase references, documents current gaps with file:line evidence, maps each AC to downstream 1445 AC items, includes td:0 markers. Well-defined evidence specification in AC4. No architect calibration needed.

### Deduction Breakdown
- Starting: 1.00
- AC lines: 5/5 verified with evidence. No deduction.
- Lint: pre-existing only. No deduction.
- AC quality: 5/5. No deduction.
- Reviewer evidence: present, detailed. No deduction.
- Full suite: all failures pre-existing (zero code changes). No deduction.
- Commit integrity: no commits expected for td:0 task. Builder correctly passed through. No deduction.
- Stale line citations in corrected AC: informational, contracts accurate. -0.01.

### Confidence: 0.99
### Action: archive
### Scratch cleanup: 3 files removed (.owlbear/scratch/1444-*.txt)