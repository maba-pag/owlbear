# Cockpit Mutation Race Tests — Stale-Precheck Interleavings

> **Owning task:** #1131 — Add cockpit mutation race tests for stale-precheck interleavings
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

The cockpit mutation API has three routes: edit (with OCC precheck), move (no OCC), and release (no OCC). Task #1131 requires tests that prove race outcomes and stale-token handling. **Question:** What race scenarios exist, what do the tests need to prove, and what test patterns work?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | 1.0 | All three route handlers, request models, precheck logic |
| S2 | `tests/test_cockpit_mutation_api.py` | 1.0 | Existing stale-edit test, release unclaimed test, fixture pattern |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L939–1310 | 1.0 | `edit_task`/`move_task`/`release_task` OCC signatures |
| S4 | `serve/kanban/src/owlbear_kanban/engine.py` L3049–3215 | 0.9 | `CockpitView` — proper OCC wrappers not used by routes |
| S5 | `serve/cockpit/src/owlbear_cockpit/models.py` L21–50 | 0.8 | `TaskDetailOut` — 16-field schema baseline |
| S6 | `tests/test_engine_cockpit_view_1078.py` | 0.8 | Engine-level OCC tests for contrast |
| S7 | `.owlbear/research/932-cockpit-mutation-api-tests.md` | 0.7 | Prior gap analysis (engine vs cockpit behaviour) |

## 3. Analysis

### 3.1 OCC Architecture: Route vs Engine vs CockpitView

| Layer | Edit OCC | Move OCC | Release OCC |
|-------|----------|----------|-------------|
| HTTP route (`mutation.py`) | Precheck only — `req.updated != task.updated` → 409 | None — `MoveRequest` has no `updated` field | None — presence check only |
| Engine (`KanbanEngine`) | CAS via `expected_updated` param (default None=off) | CAS via `expected_updated` param (default None=off) | No `expected_updated` param |
| CockpitView wrapper | Passes `expected_updated` → engine CAS engaged | Passes `expected_updated` → engine CAS engaged | No OCC; idempotent no-op if unclaimed |

**Key finding:** HTTP routes call `KanbanEngine` directly, not `CockpitView`. Routes do not pass `expected_updated` to the engine. The engine CAS is never engaged through the HTTP API.

### 3.2 Three Gap Categories

| Gap | Type | Route | Evidence |
|-----|------|-------|----------|
| G1: Edit precheck-only TOCTOU | Timing | `/edit` | `_build_edit_kwargs` strips `updated` (L105); engine called without `expected_updated`; `ConcurrencyError` not caught → would be 500 if CAS were engaged |
| G2: Move missing OCC token | Request contract | `/move` | `MoveRequest` has only `status` (L31-32); route calls `engine.move_task()` without `expected_updated` (L99) |
| G3: Release actor-agnostic | Ownership isolation | `/release` | Route checks `claimed_by` presence (L221), not identity; clears any agent's claim; existing happy path already proves this (seed claims, cockpit releases) |

### 3.3 Test Pattern Matrix

| AC Item | Gap | Test Pattern | Assertion |
|---------|-----|-------------|-----------|
| AC1: Post-precheck edit | G1 | Patch `engine.edit_task` to capture kwargs; assert `expected_updated` absent | Proves engine CAS not engaged |
| AC1: Post-precheck move | G2 | Send move after engine mutation; verify no 409 | Proves no OCC on move |
| AC1: Post-precheck release | G3 | Claim with agent B between snapshot and release; release succeeds | Proves actor-agnostic release |
| AC2: 409 detail stability | G1 | Send edit with stale `updated`; assert exact detail string | `"Task was modified since your last load (stale snapshot)"` |
| AC2: 409 detail stability | G3 | Send release on unclaimed; assert exact detail string | `f"Task {id} is not currently claimed"` |
| AC3: Release fresh-claim | G3 | Create task claimed by A; release claim; B claims; send release → clears B's claim | Proves route cannot distinguish claim owners |
| AC4: Schema preservation | All | Assert all 16 `TaskDetailOut` fields present in race-path 200/409 responses | Field baseline from `models.py` |

### 3.4 Test Infrastructure

Tests should use the existing fixture pattern from `test_cockpit_mutation_api.py`: `board_dir` → `engine` → `client` via DI override. New tests in a dedicated file `tests/test_cockpit_mutation_race_1131.py` to avoid bloating the existing 49-test suite.

For G1 (edit TOCTOU), use `unittest.mock.patch.object` on the engine to inspect whether `expected_updated` is passed. This is a structural proof (the route doesn't send the CAS token) rather than a timing proof (which would require threading).

For G2 (move), the test simply verifies that `MoveRequest` has no `updated` field and that a concurrent status change between client load and move request is invisible to the route.

For G3 (release), sequential interleaving: load task → claim via engine with different agent → send release → assert success (proving the gap).

### 3.5 Unhandled `ConcurrencyError` Risk

If the route were ever changed to pass `expected_updated` to the engine, `ConcurrencyError` would propagate as an unhandled 500 — the cockpit layer has zero `ConcurrencyError` imports or handlers. A test should document this: patching the route to pass `expected_updated`, then verifying the error path.

## 4. Recommendation (confidence: 0.78)

Write the race tests in a new file `tests/test_cockpit_mutation_race_1131.py`. Tests document current behavior (structural proofs for G1/G2, sequential interleaving for G3). Create separate follow-up tasks for route-level OCC fixes.

Challenge: `reconsider` — confidence in original: 0.64. Key challenges accepted: (1) 409 detail stability needs exact-string assertions, (2) release is actor-isolation not just timing, (3) move test must prove contract gap not just "two moves succeed", (4) schema preservation needs explicit field baseline. All four incorporated into revised test patterns (§3.3).

## 5. Follow-up Tasks

- **#1134**: Fix edit route to pass `expected_updated` to engine + add `ConcurrencyError` → 409 handler (G1)
- **#1135**: Add OCC token to move route (`MoveRequest.updated` + precheck or engine CAS) (G2)
- **#1136**: Add ownership check to release route (G3 — requires design decision on enforcement model)
