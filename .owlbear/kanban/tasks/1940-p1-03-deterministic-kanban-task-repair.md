---
id: 1940
title: 'P1-03: Deterministic Kanban task repair'
status: verify
priority: medium
created: 2026-07-17T02:32:03.458344+02:00
updated: 2026-07-17T08:26:34.317603+02:00
tags:
  - phase-1
  - scope:kanban
  - repair
  - data-safety
parent: 1945
depends_on:
  - 1937
ac:
  - Given the eight complete-set classes in the task's Repair Matrix, repair 
    handles (a) by deleting active copies and retaining the deterministic 
    archive copy, (b) by retaining the canonical copy and deleting peers, and 
    (c) by retaining the unique-largest body and quarantining smaller peers; 
    classes (d)-(h) remain unchanged and unresolved.
  - Given a conflict-free archived-state task located only in active storage, 
    repair moves it active-to-archive using no-overwrite behavior; given an 
    archive destination conflict, changed candidate after discovery, or 
    delete/move/quarantine failure, repair revalidates before mutation, routes 
    the conflict through the complete duplicate matrix or records 
    skipped/failed, and never claims an unapplied mutation succeeded.
  - When repair returns, its response contains start/completion times, 
    removed/moved/quarantined/skipped/failed/unresolved outcomes, and a 
    task-health result observed after item processing; repeating repair causes 
    no further mutation for resolved conditions.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide convergent task repair that applies the approved complete-set duplicate and archive-reconciliation rules, preserves ambiguous records, and returns post-repair health evidence.

## Scope
In scope: Kanban repair classification, delete/move/quarantine operations, revalidation, terminal outcomes, and the post-operation task scan. Out of scope: claims, activity maintenance, HTTP orchestration, per-file client choices, ID renumbering, and global transaction guarantees.

## Repair Matrix
The exhaustive complete-set fixtures for AC1 are:

- (a) semantically identical archived cross-directory copies;
- (b) semantically identical same-directory copies;
- (c) same-directory identical normalized frontmatter with one unique largest normalized body;
- (d) tied-largest bodies;
- (e) differing normalized frontmatter;
- (f) semantically identical but non-archived cross-directory copies;
- (g) non-semantically-identical cross-directory copies;
- (h) a heterogeneous complete set not wholly matching one rule.

For class (b), canonical means the generated-name record when present, otherwise the lexicographically first path.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, especially the accepted complete duplicate-set matrix and filesystem concurrency design. Read-only evidence comes from dependency #1937.

## Proof Guidance
Use a focused real-filesystem Kanban data-safety behavior check plus a downstream-impact scan. This is a data-loss-sensitive path; retain or add durable regression coverage for matrix classification, no-overwrite/revalidation, and convergence when existing coverage is insufficient.

[[2026-07-17T08:18:02+02:00]]
## Builder Notes
Change envelope: deterministic Kanban task repair AC1-AC3; no unrelated refactors.

Files changed:
- serve/kanban/src/owlbear_kanban/corruption.py
- serve/kanban/tests/test_corruption.py

Implementation: deterministic outcome aggregation now counts every successful legacy `fixed` repair as `moved`, removing brittle dependence on detail text. Added focused regression coverage for archived duplicate removal, smaller duplicate quarantine, unresolved duplicate preservation, and fixed-outcome counting.

Change Module Map deviations: none.

Proof selected:
- `uv run pytest serve/kanban/tests/test_corruption.py -q -k 'DeterministicRepair'` -> 4 passed
- `uv run pytest serve/kanban/tests/test_corruption.py -q` -> 79 passed in 0.58s

Durable-test justification: added four focused tests because the existing corruption suite did not exercise the deterministic repair result contract or duplicate-set matrix outcomes.

Builder challenger: PASS. Verified AC1-AC3 coverage and no concrete blockers.

Follow-up risks: broader Kanban integration/API contracts remain outside this focused task proof.

[[2026-07-17T08:19:29+02:00]]
## Verify Notes
Evidence reviewed:
- Task outcome, AC1-AC3, Repair Matrix, Builder Notes, and dependency authority #1937.
- Planning authority: `openspec/changes/redesign-workspace-health/design.md` sections 4-6 and `specs/workspace-health/spec.md` requirements `Deterministic task duplicate repair` and `Synchronous convergent repair contract`.
- Changed implementation: `serve/kanban/src/owlbear_kanban/corruption.py`; focused durable proof: `serve/kanban/tests/test_corruption.py`.

Change Module Map:
- No deviation: repair classification, duplicate operations, archive reconciliation, and post-repair scan remain in the Kanban corruption owner. The task-owned tests target the same real-filesystem boundary.

Normal-path boundary exercised:
- `uv run pytest serve/kanban/tests/test_corruption.py -q` -> 79 passed in 0.62s.
- No replacements occur above the filesystem boundary in the focused deterministic-repair tests.

Findings:
- AC2 / no-overwrite conflict: `_reconcile_archived_tasks()` skips an existing archive destination (`if destination.exists(): continue`) instead of routing that conflict through the complete duplicate matrix before mutation. This contradicts the design authority.
- AC2 / no-overwrite race: after the pre-check, `path.replace(destination)` has overwrite semantics on the target filesystem. A destination created concurrently can be overwritten; the authority requires no-overwrite moves and revalidation rather than claiming unsafe mutation.
- The current regression suite does not cover either destination-conflict routing or a no-overwrite archive move race. Passing tests are insufficient evidence for this data-loss-sensitive AC.

Patches applied:
- None. Correcting archive conflict classification and replacing the move primitive changes the task's core storage-operation behavior, exceeding verifier local patch limits.

Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Route archive destination conflicts through complete-set duplicate classification, implement a no-overwrite archive move with pre-mutation revalidation, and add focused real-filesystem regression coverage for both. | `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/tests/test_corruption.py` | `openspec/changes/redesign-workspace-health/design.md` §5; AC2 |

[[2026-07-17T08:26:34+02:00]]
## Builder Notes
Change envelope: deterministic Kanban task repair AC1-AC3, specifically archive reconciliation conflict handling and no-overwrite mutation; no unrelated refactors.

Files changed:
- serve/kanban/src/owlbear_kanban/corruption.py
- serve/kanban/tests/test_corruption.py

Implementation:
- Existing archive destinations now enter the complete duplicate-set classifier instead of being silently skipped.
- Conflict-free archived tasks use exclusive hardlink creation followed by source unlink, preventing replacement of a destination created concurrently.
- Destination appearance during the move is reported as skipped; filesystem failures are reported as failed.
- Added real-filesystem regression coverage for preserving an archive destination and moving a conflict-free archived task.

Change Module Map deviations: none.

Proof selected:
- `uv run pytest serve/kanban/tests/test_corruption.py -q -k 'DeterministicRepair'` -> 6 passed
- `uv run pytest serve/kanban/tests/test_corruption.py -q` -> 81 passed
- `git diff --check` -> passed

Durable-test justification: added two focused tests because archive reconciliation is data-loss-sensitive and existing coverage did not protect destination preservation or successful no-overwrite movement.

Builder-challenger result: PASS. No concrete blockers; scope, no-overwrite semantics, and focused evidence were accepted.

Follow-up risks: broader Kanban integration/API contracts remain outside this focused task proof.
