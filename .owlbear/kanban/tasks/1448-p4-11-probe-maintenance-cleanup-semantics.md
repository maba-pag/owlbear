---
id: 1448
title: 'P4-11: Probe maintenance cleanup semantics'
status: todo
priority: needed
created: 2026-05-08T19:32:09.582469+00:00
updated: 2026-05-08T21:41:17.360518+00:00
tags:
- phase-4
- scope:maintenance
- type:test
- verification-probe
- cleanup
- cockpit
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
In scope: scratch-board probes for user-triggered maintenance cleanup semantics.
Out of scope: source changes, docs, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a scratch-board claim-release probe with one expired claimed task and one live claimed task; the expected maintenance result clears only the expired `claimed_at` value via compare-and-swap, leaves the live claim untouched, and reports the released task ID in `released_claim_ids`. (td:1)
2. Test-writer records an archive-move probe for the drift-remediation scenario: one task file remaining in the active tasks directory whose status field is already `archived` and whose `archival_reason` is valid (e.g. `completed`); the expected maintenance result moves that file from tasks/ to archive/ and reports the archived task ID in `archived_task_ids`. (td:1)
3. Test-writer records a safety probe where an archive destination collision (target file already exists in archive/) or malformed task file (unparseable frontmatter) is skipped; each `skipped_items` entry includes `path` (str) and `reason` (str) fields, and the source task file is not deleted. (td:1)
4. Test-writer records a single-call aggregation probe: one cleanup invocation against a board containing an expired claim, a drift-archived file, and a malformed file returns `released_claim_ids`, `archived_task_ids`, and `skipped_items` in one response. (td:1)
5. Test-writer records a Cockpit contract probe for `POST /api/tasks/cleanup` returning `released_claim_ids` (list[int]), `archived_task_ids` (list[int]), and `skipped_items` (list[object with path and reason]) fields; Cockpit view/route layers pass `skipped_items` through without converting them to a generic error. (td:1)
6. Test-writer records a negative probe confirming that `pick_tasks`, `start_work`, engine initialization, Cockpit startup, board read endpoints, task list refresh, and SSE event streaming do not invoke the cleanup operation. (td:1)
7. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and contract inspection. (td:0)

[[2026-05-08]]
## Architecture Review

### Verdict: APPROVE (after refinement)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Probes only for cleanup/maintenance domain |
| Interface clarity | PASS | AC refined with CAS semantics, skipped_items shape, drift-remediation framing, negative probes |
| Dependency correctness | PASS | Root probe — no deps, correct |
| Module layering | N/A | No source changes — probe-only task |
| TDD compliance | PASS | This IS the test task (type:test, verification-probe) |
| KISS/YAGNI | PASS | Minimal probe scope, 7 focused AC lines |
| Premise challenge | PASS | Cleanup probes required by #1449 AC5 and #1457 AC5 as evidence source |
| Pattern consistency | PASS | Follows sibling root-probe pattern (1438, 1440, 1442, 1444, 1446, 1450, 1452, 1454) |
| Security surface | N/A | No new boundaries — probe notes only |
| Single domain | PASS | Maintenance/cleanup is one domain |

### Refinements Applied
Original 5 AC lines expanded to 7 to close gaps identified by challenger:
- AC1: added compare-and-swap semantics and `released_claim_ids` field reference
- AC2: reframed as drift-remediation scenario with example reason (`completed`)
- AC3: defined `skipped_items` entry shape (`path: str`, `reason: str`)
- AC4 (new): single-call aggregation probe — one invocation returns all three result categories
- AC5 (was AC4): typed response contract with Cockpit passthrough requirement
- AC6 (new): negative probe — cleanup not implicitly invoked by pick_tasks, start_work, init, Cockpit startup/read/refresh/SSE
- AC7 (was AC5): no-execution constraint unchanged

### Challenger
- Confidence in original: 0.57 → reconsider
- Key concerns: downstream proof mismatch (critical), skipped-items under-specified (moderate), remediation-state ambiguity (moderate), missing aggregation probe (moderate)
- Resolution: all critical and moderate concerns addressed via AC refinement; archive-reason coverage (minor) left as-is — one example reason is sufficient for a probe
- Post-refinement confidence: 0.90

### Codebase Evidence
- Existing `sweep()` at engine.py:1700 handles expired claim release with CAS
- `move_task(status="archived")` at engine.py:1200 handles archive moves with `validate_archival()`
- No `POST /api/tasks/cleanup` exists yet — probes define the contract for #1449 and #1457
- Archival reasons: [completed, deprecated, dropped, duplicate, wontfix] (currently config, hardcoded after #1439)
- RepairOutcome model at models.py:561 and scan serialization at mutation.py:110 show existing payload-shape conventions for maintenance results