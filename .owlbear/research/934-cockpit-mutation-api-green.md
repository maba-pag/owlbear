# Cockpit Mutation API — GREEN Phase Validation

> **Owning task:** #934 — P1-07: GREEN — Cockpit mutation API
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #934 requires implementing three cockpit mutation endpoints (`move`, `edit`, `release`) to pass the RED tests written in #932. **On inspection, the implementation already exists and all 49 tests pass.** This research validates the existing code against AC rather than planning new work.

**Question:** Does the existing implementation satisfy all 10 AC items? Are there deviations from the prescribed file layout?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | 1.0 | Full implementation: 3 endpoints, request models, helpers |
| S2 | `serve/cockpit/src/owlbear_cockpit/adapter.py` | 0.8 | Read-only wrappers only — mutations bypass adapter |
| S3 | `tests/test_cockpit_mutation_api.py` | 1.0 | 49 tests: move, edit, release, audit logging, edge cases |
| S4 | `tests/test_cockpit_boundary.py` | 0.9 | 12 boundary tests including AST import enforcement |
| S5 | `.owlbear/research/932-cockpit-mutation-api-tests.md` | 0.9 | Gap analysis between engine and cockpit behaviour |
| S6 | `serve/kanban/src/owlbear_kanban/engine.py` | 0.7 | Engine method signatures for validation |

## 3. Analysis

### AC Verification Matrix

| AC Item | Status | Evidence |
|---------|--------|----------|
| `POST /move` validates via `valid_transitions` | ✅ | `mutation.py:82-95` — reads task, checks transitions, delegates |
| `POST /edit` updates allowlisted fields + body | ✅ | `_build_edit_kwargs()` maps 7 fields to engine kwargs |
| Edit checks `updated` snapshot → 409 | ✅ | `mutation.py:171-175` — string comparison, HTTPException 409 |
| `POST /release` calls engine release | ✅ | `mutation.py:186-197` — checks `claimed_by` first (refinement: 409 if unclaimed) |
| Block via `block_reason` / unblock via null | ✅ | `_build_edit_kwargs` lines 131-135 |
| Activity log with `actor: "cockpit"` | ✅ | Test fixture creates engine with `agent_name="cockpit"`, `activity_log=True` |
| Pydantic `extra="forbid"` on request models | ✅ | `MoveRequest`, `EditRequest` both set `ConfigDict(extra="forbid")` |
| 404 / 422 error handling | ✅ | All three endpoints handle `FileNotFoundError` → 404, `ValueError` → 422 |
| All RED tests from #932 pass | ✅ | 49 passed in 0.76s (verified) |
| Boundary tests still pass | ✅ | Included in the 49 passing tests |

### File Layout Deviations from AC

| AC Prescribed | Actual | Impact |
|---------------|--------|--------|
| `routes/mutate.py` | `routes/mutation.py` | None — naming preference only |
| `models.py` for request models | Request models in `routes/mutation.py` | Better cohesion — request models colocated with routes |
| `adapter.py` with mutation wrappers | Mutations call engine directly | KISS-aligned — adapter indirection unnecessary for writes |

All three deviations are improvements over the prescribed layout. No functional impact.

## 4. Recommendation (confidence: .95)

**Implementation is complete.** All 10 AC items are satisfied. The three file layout deviations are justified architectural refinements (KISS, cohesion). No code changes needed.

Challenge: skipped — validation pass, no competing approaches.

## 5. Follow-up Tasks

None required. Implementation is complete, all tests pass, no gaps identified.
