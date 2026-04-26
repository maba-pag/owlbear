# end_work CAS gap: facade precheck vs raw-engine write race

> **Owning task:** #1129 — Research: end_work CAS gap — facade precheck vs raw engine write race
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

`AgentView` methods in `serve/kanban/src/owlbear_kanban/engine.py` perform read-time validation (`show_task`) and then call raw engine mutation methods that execute a separate read-mutate-write cycle. This creates a TOCTOU window between precheck and write.

The same pattern exists in Cockpit HTTP mutation routes in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, where a route-level `show_task` precheck is followed by a raw engine mutation call.

Question: given OwlBear's laptop-resident constraints, does prior D2 risk acceptance (concurrent access accepted for single-user system) still hold, and what mitigation should be prioritized?

## 2. Writer Surface Map (AC1)

### 2.1 AgentView read-precheck -> separate-write call sites

| Method | Read/precheck | Write call | TOCTOU window consequence |
|---|---|---|---|
| `AgentView.edit_task` | `existing = self.engine.show_task(...)` at ~L2485 | `self.engine.edit_task(..., source="agent")` at ~L2685 | Validation is done against snapshot A; write applies to snapshot B if file changed in between. |
| `AgentView.move_task` | `before = self.engine.show_task(...)` at ~L2704 | `self.engine.move_task(..., source="agent")` at ~L2730 | Transition predicate can be validated on stale body/status. |
| `AgentView.start_work` | `task_record = self.engine.show_task(...)` at ~L2750 | `self.engine.start_work(...)` at ~L2757 | Archived guard is checked on stale state; later claim path can observe newer state. |
| `AgentView.end_work` | `before = self.engine.show_task(...)` at ~L2939 | `self.engine.end_work(...)` at ~L2981 (or `release_task`) | Claim/predicate checks can pass on stale state; write uses a later snapshot. |

### 2.2 Cockpit HTTP read-precheck -> separate-write call sites

| Route | Read/precheck | Write call | TOCTOU/OCC posture |
|---|---|---|---|
| `POST /tasks/{id}/move` | `task = engine.show_task(...)` | `engine.move_task(...)` | No OCC token passed. Pure last-writer-wins route path. |
| `POST /tasks/{id}/edit` | `task = engine.show_task(...)` + timestamp compare in route | `engine.edit_task(...)` | Route checks staleness but does not pass `expected_updated` to engine CAS. |
| `POST /tasks/{id}/release` | `task = engine.show_task(...)` + claimed guard | `engine.release_task(...)` | No OCC token; check and mutation are split. |

## 3. Practical Exploitability Across Surfaces (AC2)

### 3.1 AgentView over MCP stdio

- In normal operation, MCP request handling is effectively serialized per server process, which reduces in-process racing.
- Remaining race vectors are inter-process writes (for example Cockpit backend or other tools writing task files) between facade precheck and engine write.
- Practical risk: low-to-moderate. Impact is mostly stale validation (predicate/claim check against older state), not storage corruption.

### 3.2 Cockpit HTTP over uvicorn

- Cockpit runs as a separate process and can mutate the same task files concurrently with MCP agents.
- Route-level prechecks and mutation calls are separate operations, so concurrent writes can invalidate route assumptions before mutation executes.
- Practical risk: moderate. This is the highest-probability writer race surface in current architecture.

### 3.3 Existing protections and their scope

- CAS/OCC primitive exists: `storage.write_task_if_unchanged(...)` in `serve/kanban/src/owlbear_kanban/storage.py`.
- Raw engine supports OCC for select methods: `edit_task(... expected_updated=...)`, `move_task(... expected_updated=...)`.
- `claim_task` already uses CAS retry logic.
- `CockpitView` requires OCC token for edit/move, but Cockpit HTTP routes currently call raw engine methods directly, bypassing that stronger facade contract.

## 4. Mitigation Strategies and Trade-offs (AC3)

| Option | Summary | Pros | Cons | Confidence |
|---|---|---|---|---|
| A. Accept risk (status quo) | Keep current facades/routes unchanged. | Zero implementation cost; aligns with earlier D2 stance for single-user laptop setup. | Leaves known stale-precheck window, especially on Cockpit route path. | 0.45 |
| B. Cockpit-first OCC hardening | Add OCC token to Cockpit mutation endpoints and enforce engine CAS at write time (edit/move; release via revision token or equivalent CAS path). | Targets highest-concurrency surface first; smallest blast radius; measurable regression tests possible. | API adjustment required for move/release request payloads and frontend client wiring. | 0.83 |
| C. Full facade CAS unification | Thread `expected_updated` (or equivalent revision token) through AgentView and Cockpit paths; collapse split precheck/write assumptions. | Strongest consistency semantics across all public mutation surfaces. | Larger contract change; more invasive across tools and tests; higher rollout risk. | 0.62 |
| D. Coarse file locking | Introduce per-task lock around facade precheck + engine mutate path. | Prevents interleaving races without API contract changes. | Longer lock duration, harder deadlock/failure semantics, weaker portability and UX under contention. | 0.38 |

## 5. Recommendation and D2 Re-evaluation (AC4)

Recommendation: **Defer implementation for now and keep explicit risk acceptance (Option A), with a narrowed scope and revisit trigger.**

Rationale:

1. The previous D2 risk acceptance remains credible for the primary single-user workflow and serialized MCP agent interactions.
2. Cockpit introduces a real concurrent-writer surface, but the observed impact is stale-precheck semantics (last-writer-wins), not data corruption in current architecture.
3. Option B is still the preferred future mitigation path, but immediate implementation is not mandatory for current risk tolerance and system constraints.

Outcome on D2: **Still valid but narrowed.** D2 should no longer be cited as a blanket guarantee across all writer surfaces; it now explicitly covers accepted last-writer-wins behavior unless concurrency incidents increase.

Revisit trigger:

- Any confirmed user-visible stale overwrite from Cockpit mutation routes.
- Expansion from single-user workflow to multi-client concurrent operation.

## 6. Follow-up Tasks (AC5)

No implementation follow-up task created in this cycle because the recommendation is to defer and keep risk acceptance with explicit revisit triggers.
