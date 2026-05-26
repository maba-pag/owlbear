---
id: 1863
title: 'P2-06: Remove old Cockpit resolve flow and legacy endpoints'
status: todo
priority: important
created: 2026-05-24T21:00:04.160667+02:00
updated: 2026-05-26T05:54:21.231179+02:00
tags:
  - phase-2
  - scope:cockpit
  - cleanup
parent: 1850
depends_on:
  - 1856
  - 1858
  - 1859
  - 1860
ac:
  - Old resolve_decision endpoint (POST /api/decisions/{id}/resolve with 
    response=approved/needs-info/rejected payload) is removed from Cockpit 
    routes; requests to that path return HTTP 404.
  - Old list_pending_decisions endpoint (GET /api/decisions/pending returning 
    PendingDRResponse with body-text regex title extraction) is removed from 
    Cockpit routes; requests to that path return HTTP 404.
  - Frontend decisions.test.ts (testing old POST /api/decisions/{id}/resolve 
    contract) is removed; LegacyPendingDRResponse interface and dual-format 
    normalization in usePendingDRs.ts are removed; only new /api/requests/ API 
    types remain in frontend code.
  - Cockpit backend test suites in tests/test_cockpit_* and serve/cockpit/tests/
    pass green after removal (tests referencing deleted endpoints are updated or
    removed).
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Remove `resolve_decision` endpoint from `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- Remove `list_pending_decisions` endpoint and related models (`PendingDRItem`, `PendingDRResponse`, `ResolveRequest`)
- Remove the `decisions.py` route module entirely and its router registration in `main.py`
- Remove old frontend test file (`serve/cockpit/web/src/__tests__/decisions.test.ts`) that tests removed API contract
- Remove `LegacyPendingDRResponse` dual-format compatibility code from `serve/cockpit/web/src/hooks/usePendingDRs.ts`

**Out of scope:**
- `parse_dr` and `move_to_resolved` engine helpers (used by new code)
- `_append_response_section` and `_rewrite_response` in kanban engine (actively used by `resolve_decision` in new flow)
- New endpoints and UI (already shipped)
- `ResolveModal.tsx` (already uses new structured pattern)

## Downstream impact
- `tests/test_cockpit_decisions_api.py` — update or remove tests for old endpoints
- `tests/test_cockpit_decisions_pydantic_1640.py` — review for old model references
- `serve/cockpit/tests/test_decisions_integration.py` — references old `PendingDRResponse` model
- `tests/test_cockpit_error_envelope.py` — may reference old endpoint paths
- Frontend test files covering old resolve API contract

## Test scope
`tests/test_cockpit_*`, `serve/cockpit/tests/`, and `npm test` in `serve/cockpit/web/`

[[2026-05-26T05:54:21+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure removal of old Cockpit endpoints and dead frontend code |
| Interface clarity | PASS (after refine) | AC now specifies 404 outputs for both endpoints + concrete frontend targets |
| Dependency correctness | PASS | All 4 deps (1856, 1858, 1859, 1860) archived/completed |
| Module layering | PASS | Removes cockpit route module only; kanban engine helpers explicitly out of scope |
| TDD compliance | PASS | Test-writer will write 404 negative assertions; existing test cleanup enumerated |
| KISS/YAGNI | PASS | Straightforward removal, no new abstractions |
| Premise challenge | PASS | New endpoints live, old code is dead weight |
| Pattern consistency | PASS | Follows same removal pattern as sibling #1862 |
| Security surface | PASS | Removal only, no new boundaries |
| Single domain | PASS | Cockpit domain (Python routes + frontend tests/hooks) — corrected scope to exclude kanban engine helpers |

### Scope Correction
Planner scope listed `_append_response_section` and `_rewrite_response` as in-scope removals. These live in `serve/kanban/src/owlbear_kanban/decisions.py` and are actively called by the engine's `resolve_decision` (lines 157-158) which the NEW `requests.py` endpoint uses. Moved to explicit out-of-scope.

### Challenge Results
- Challenger: reconsider (confidence 0.46)
- Findings: domain-boundary (scope listed kanban helpers), AC-quality (AC2 missing 404, AC3 vague), verification-scope (incomplete test file listing)
- Architect response: accepted domain-boundary and AC-quality findings → refined scope and AC. Verification-scope addressed by expanding downstream impact section. Consolidation-backstop concern noted but acceptable — negative 404 assertions belong in this task's tests, not consolidation test.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Corrected scope (removed cross-domain kanban helpers from in-scope), tightened AC2 with 404 output, replaced vague AC3 with concrete file targets (decisions.test.ts, LegacyPendingDRResponse), added AC4 for test-suite health, expanded downstream impact list. Advanced backlog → todo.
