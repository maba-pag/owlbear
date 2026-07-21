---
id: 1972
title: Recover lint-clean Kanban integrity changes
status: collect
priority: high
created: 2026-07-21T16:05:51.989615+02:00
updated: 2026-07-21T16:11:16.920360+02:00
tags:
  - scope:kanban
  - integrity
  - maintenance
  - baseline-repair
parent:
depends_on: []
ac:
  - 'AC-1: Given readable persisted defects, an unreadable task, broken references,
    and an archived-state task in active storage, `KanbanEngine.task_health()` returns
    the named findings and leaves file paths, bytes, and mtimes unchanged.'
  - 'AC-2: Given duplicate and archive-reconciliation fixtures from the maintained
    corruption suite, repair preserves unresolved complete sets, uses no-overwrite
    archive movement, reports terminal outcomes, and converges on a repeated call.'
  - 'AC-3: Given the recovered corruption source and task-health regression file,
    Ruff lint and format validators accept both maintained artifacts.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The previously verified Kanban integrity work from archived tasks #1937 and #1940 has durable commit ownership without changing its public behavior.

## Scope
In scope: the existing dirty changes in `serve/kanban/src/owlbear_kanban/corruption.py` and `serve/kanban/tests/test_engine_task_health.py`; lint-safe repair decomposition; retained public task-health regression coverage.

Out of scope: new repair rules, Cockpit behavior, Memory behavior, task renumbering, and unrelated workspace cleanup.

## Contract Authorities
- Archived task-health contract: #1937.
- Archived deterministic-repair contract: #1940.
- Current `KanbanEngine.task_health()` and corruption repair public boundaries.

## Proof Guidance
Run focused Kanban task-health and corruption suites plus Ruff lint and format checks on the two owned files. Treat this as ownership recovery: reduce or reject any delta that changes the archived contracts.

[[2026-07-21T16:09:05+02:00]]
## Builder Notes

Verdict: DONE.

Change envelope: adopted only the existing dirty Kanban integrity changes in `serve/kanban/src/owlbear_kanban/corruption.py` and `serve/kanban/tests/test_engine_task_health.py`; no new repair rule or cross-domain file was introduced.

Behavior: retained #1937 read-only task-health evidence and #1940 complete-set/no-overwrite repair behavior while decomposing archive reconciliation enough for repository lint.

Proof: `uv run pytest serve/kanban/tests/test_corruption.py serve/kanban/tests/test_engine_task_health.py -q` passed 86 tests; Ruff check passed; Ruff format reported both files formatted.

Durable-test rent: the added public task-health cases protect persisted-file integrity, broken-reference evidence, and non-mutation, risks not cheaply observable after release.

Builder-challenger: decision pass; no blocker, scope drift, or auto-fix.

[[2026-07-21T16:11:16+02:00]]
## Verify Notes

Verdict: PASS.

Exact revision: `9949f9b1b86c5573bd62720a27137784a34e4333`, confirmed as HEAD in the clean prepared worktree after the switch command emitted the known empty exit-130 signal.

Authority: compared the recovered slice with archived #1937 task-health and #1940 deterministic-repair contracts; no public-contract or ownership deviation found.

Proof at the exact revision: focused corruption plus task-health suites passed 86 tests; Ruff check passed on both owned files; Ruff format reported both files formatted.

AC mapping: real-filesystem tests cover read-only persisted/reference/location evidence and complete-set/no-overwrite repair convergence; Ruff covers maintained-artifact quality.

Verifier-challenger: decision pass; no scope, rent, evidence, or unresolved-AC finding.
