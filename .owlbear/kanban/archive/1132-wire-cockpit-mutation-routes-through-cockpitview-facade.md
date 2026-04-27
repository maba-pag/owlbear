---
id: 1132
title: Wire cockpit mutation routes through CockpitView facade
status: research
priority: important
created: 2026-04-26T15:52:11.982906+00:00
updated: 2026-04-26T17:13:47.605759+00:00
tags:
- cockpit
parent: 1130
depends_on:
- 1130
- 1133
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Replace raw engine calls in mutation.py with CockpitView calls to close TOCTOU windows on edit and release endpoints, and unify all three mutation routes through the CockpitView facade for pattern consistency.

**Errata (from reviewer cycle 1):** The original AC assumed POST /move had no OCC. Live code already has full OCC: `MoveRequest.updated` (L28-34), stale-snapshot precheck (L94), `expected_updated` pass-through (L108-109), and `ConcurrencyError` → 409 (L110-113). Move routing through CockpitView is a pattern-consistency change, not an OCC fix.

Acceptance Criteria:
- [ ] All three mutation routes (move, edit, release) delegate to CockpitView instead of raw KanbanEngine. DI provides CockpitView (or routes construct it from engine).
- [ ] POST /edit passes req.updated as expected_updated to CockpitView.edit_task() instead of route-level precheck + raw engine call.
- [ ] POST /release accepts `updated` in a new ReleaseRequest body model and passes it as expected_updated to CockpitView.release_task().
- [ ] POST /move routes through CockpitView.move_task() — functionally equivalent to current engine-level OCC (no behavior change; pattern consistency + source tagging).
- [ ] ConcurrencyError(ERR_STALE) from CockpitView maps to HTTP 409 on edit and release endpoints (move already maps it).
- [ ] NotFoundError maps to HTTP 404; ValidationError maps to HTTP 422.
- [ ] Route-level show_task prechecks removed for edit and release (CockpitView handles internally).
- [ ] New tests cover HTTP 409 on stale edit and stale release.
- [ ] Existing release tests updated to send request body with `updated` field.
- [ ] Activity events include source=cockpit (CockpitView sets this automatically).
- [ ] adapter.valid_transitions precheck in move route either removed (engine validates internally via ValueError) or retained with engine access alongside CockpitView.

Scope boundary: Route layer only (mutation.py, deps.py, models.py, cockpit tests). Engine changes are #1133.

Likely files:
- serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- serve/cockpit/src/owlbear_cockpit/deps.py (or inline CockpitView construction)
- serve/cockpit/src/owlbear_cockpit/models.py (if request models change)
- tests/test_cockpit_mutation_api.py

Research: .owlbear/research/cockpit-mutation-occ-parity.md (move endpoint parity reflected; this task keeps move routing for facade consistency)
