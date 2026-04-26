# Cockpit Mutation OCC Parity

> **Owning task:** #1130 — Implement cockpit mutation OCC parity (move/edit/release)
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

The Cockpit HTTP routes (`mutation.py`) bypass the OCC-aware `CockpitView` facade and call raw `KanbanEngine` methods directly. This creates TOCTOU (time-of-check-to-time-of-use) windows where a concurrent writer can modify a task between the route's `show_task` read and its subsequent mutation call. The engine already supports per-task CAS via `expected_updated` + `write_task_if_unchanged`, and `CockpitView` wraps it with required OCC signatures — but the routes don't use either.

**Question:** What is the minimal change to close these TOCTOU windows?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` (L82–227) | 1.0 — current route implementations |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` `CockpitView` (L3049–3250) | 1.0 — OCC-correct facade already exists |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py` `move_task` (L1068–1140) | 0.9 — engine `expected_updated` param |
| 4 | `serve/kanban/src/owlbear_kanban/engine.py` `release_task` (L1266–1320) | 0.9 — no OCC param, last-writer-wins |
| 5 | `serve/kanban/src/owlbear_kanban/storage.py` `write_task_if_unchanged` | 0.9 — CAS primitive with fcntl locks |
| 6 | `serve/kanban/src/owlbear_kanban/errors.py` `ConcurrencyError` | 0.8 — `ERR_STALE` error type for 409 mapping |
| 7 | `tests/test_cockpit_mutation_api.py` | 0.8 — existing mutation test coverage |
| 8 | `tests/test_engine_cockpit_view_1078.py` | 0.8 — CockpitView OCC tests (engine layer) |

## 3. Analysis

### Current State per Endpoint

| Endpoint | OCC token required? | CAS write? | TOCTOU window? |
|----------|---------------------|------------|-----------------|
| `POST /move` | No — `MoveRequest` has no `updated` field | No — calls `engine.move_task()` without `expected_updated` | **Yes** — show → move gap |
| `POST /edit` | Yes — `EditRequest.updated` is required | **Route-level only** — checks `req.updated != task.updated`, then calls `engine.edit_task()` without `expected_updated` | **Yes** — check-vs-write gap |
| `POST /release` | No | No — calls `engine.release_task()` (LWW) | **Yes** — show → release gap; fresh claim can be cleared by stale UI |

### Engine Capabilities Already Available

| Method | `expected_updated` param | `ConcurrencyError` on mismatch |
|--------|--------------------------|-------------------------------|
| `engine.edit_task()` | Optional | Yes, via `write_task_if_unchanged` |
| `engine.move_task()` | Optional | Yes, via `write_task_if_unchanged` |
| `engine.release_task()` | **Not supported** | N/A — always LWW |
| `CockpitView.edit_task()` | **Required** | Yes |
| `CockpitView.move_task()` | **Required** | Yes |
| `CockpitView.release_task()` | Not supported | N/A |

### Option Comparison

| Option | Description | Pros | Cons | Complexity |
|--------|-------------|------|------|------------|
| **A: Route through CockpitView** | Inject `CockpitView` instead of `KanbanEngine` in routes; map CockpitView exceptions to HTTP | Cleanest separation; CockpitView already tested; single DI change | Requires new DI provider; release still LWW; CockpitView returns `SingleTaskResponse` not `Task` — adapter needs adjustment | Medium |
| **B: Pass expected_updated directly** | Keep raw engine calls; add `expected_updated` to move/edit routes; catch `ConcurrencyError` → 409 | Minimal diff; no DI change; routes already handle 409 for edit | Duplicates OCC wiring that CockpitView already provides; still no release CAS | Low |
| **C: Add expected_updated to engine.release_task** | Extend engine `release_task` with OCC param + route changes | Full CAS coverage including release | Engine API change; may over-engineer release (claim owner identity check may suffice) | Medium-High |

### Risk Assessment

- **Release CAS (AC3):** The AC says "compare-and-release semantics to avoid clearing a fresh claim from a stale UI snapshot." Engine `release_task` doesn't accept `expected_updated`. Two sub-options:
  - **C1:** Add `expected_updated` to `engine.release_task` (new engine API surface)
  - **C2:** Route-level precheck with `expected_updated` in the request body (weaker but simpler — same TOCTOU pattern being fixed for move/edit, but the release race window is very narrow in practice for a single-user cockpit)
  - **C3:** Route through `CockpitView.release_task` which already does a `claimed_at` guard (still no CAS, but scopes the check)

## 4. Recommendation

**Option A (Route through CockpitView) + C1 (engine release CAS)** — confidence: 0.82

Rationale: `CockpitView` already exists, is tested (#1078), enforces OCC on edit/move, and provides source tagging. The routes should use it instead of bypassing it. For release, add `expected_updated` to `engine.release_task` to satisfy AC3's compare-and-release requirement.

The route layer changes become:
1. Replace `get_engine` DI with `get_cockpit_view` (returns `CockpitView(engine)`)
2. Add `updated` field to `MoveRequest`
3. Add `updated` field to a new `ReleaseRequest` body model
4. Catch `ConcurrencyError` → 409, `NotFoundError` → 404, `ValidationError` → 422
5. Add `expected_updated` param to `engine.release_task`

Challenge: proceed — confidence in original: 0.82. The CockpitView facade exists specifically for this purpose and is already tested; not using it is the architectural gap.

## 5. Follow-up Tasks

See kanban tasks created at `research` status.
