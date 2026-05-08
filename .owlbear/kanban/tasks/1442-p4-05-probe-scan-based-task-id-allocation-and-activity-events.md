---
id: 1442
title: 'P4-05: Probe scan-based task ID allocation and activity events'
status: todo
priority: needed
created: 2026-05-08T19:31:56.603397+00:00
updated: 2026-05-08T21:36:17.131247+00:00
tags:
- phase-4
- scope:kanban
- type:test
- verification-probe
- id-allocation
- activity
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
In scope: scratch-board probes for create_task ID allocation and activity event emission.
Out of scope: source changes, MCP transport, Cockpit UI, and full-suite proof.

## Acceptance Criteria
1. Test-writer records a scratch-board ID probe with active task filename prefixes 1 and 3 plus archive filename prefixes 2 and 5, then states that the next create_task call must use ID 6 with no config.yml next_id read or write.
2. Test-writer records a concurrent-create probe that exercises the create lock and expects distinct task filename prefixes for competing create_task calls.
3. Test-writer records an activity probe where create_task emits one mutation event containing task_id, action, source, detail, and timestamp fields.
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-board probe notes and activity file inspection.
[[2026-05-08]]


## Architect Refinement

**AC3 expansion:** The event field list must include `task_status_at_start` alongside the five fields already listed, for a total of six fields matching the `ActivityEvent` model. Parent #1437 direction states "emit complete mutation events, including task creation" — the probe must specify the full field set. For a creation event, `task_status_at_start` is the entry status of the newly created task.

**Test depth:** All AC lines are td:0 (probe notes, no test code). Test-writer: SKIP (type:test pass-through). Probes serve as contract specification for #1443.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Both probes concern `create_task` behavior changes — scan-based allocation and activity emission are within the same feature area |
| Interface clarity | PASS (after refinement) | AC3 expanded to include `task_status_at_start` for full `ActivityEvent` coverage |
| Dependency correctness | PASS | No dependencies — correct as root probe |
| Module layering | N/A | No source changes |
| TDD compliance | PASS | type:test pass-through; probes serve as contract spec for #1443 RED/GREEN |
| KISS/YAGNI | PASS | Minimal scope — notes-only deliverable |
| Premise challenge | PASS | Probes define contract before #1443 implementation |
| Pattern consistency | PASS | Follows probe pattern established in #1438 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | kanban domain only |
| Failure Mode Map | N/A | No codepaths modified |
| Decision-request verification | N/A | No research doc referenced |
| User-action detection | SKIP | Counter-signal C3: type:test tag present |

### Codebase Context
- `allocate_next_id`: `serve/kanban/src/owlbear_kanban/storage.py` L571–581 — currently config-driven via `config.yml` `next_id` under `.next_id.lock`
- `create_task`: `serve/kanban/src/owlbear_kanban/engine.py` L941–1043 — no activity emission currently
- `_emit_event`: `serve/kanban/src/owlbear_kanban/engine.py` L1821–1845 — existing event helper, not called by `create_task`
- `ActivityEvent`: `serve/kanban/src/owlbear_kanban/models.py` L525–535 — 6-field model (timestamp, task_id, action, source, detail, task_status_at_start)
- `_naming.py` L33–35: `make_task_filename({id}, title)` → `{id}-{slug}.md`
- File locking: `_locking.py` L12–32 — `_exclusive_file_lock` via `fcntl.flock`

### Refinement Applied
- AC3: Added `task_status_at_start` to the expected event field list (6 fields total) to match `ActivityEvent` model and parent brief "complete mutation events" directive.

### Challenge Results
- Skipped: all AC lines are td:0 (per Step 2.1 gating rule).

### Test Depth
- All AC lines: td:0 (probe notes, no test code written in this task)
- Max depth: td:0
- Test-writer: SKIP (type:test pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC3 to include full ActivityEvent field set (6 fields). Kept type:test tag and notes-based probe format. Advanced to todo.
[[2026-05-08]]
Architecture review complete. Refined AC3 to include task_status_at_start (6-field ActivityEvent contract per parent brief "complete mutation events" directive). All AC lines td:0 — probe specifications only. Follows established probe pattern from #1438. Advanced to todo.