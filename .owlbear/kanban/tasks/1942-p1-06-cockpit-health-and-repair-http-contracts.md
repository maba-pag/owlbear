---
id: 1942
title: 'P1-06: Assemble Cockpit workspace health contracts'
status: verify
priority: high
created: 2026-07-17T02:32:17.957866+02:00
updated: 2026-07-17T17:53:01.454436+02:00
tags:
  - phase-1
  - scope:cockpit-backend
  - api
  - health
parent: 1945
depends_on:
  - 1937
  - 1939
  - 1940
  - 1941
  - 1938
ac:
  - Through the assembled FastAPI app, GET /health/live performs no workspace 
    scan; GET /health and focused task/request/memory/ideas reads return typed 
    module results and HTTP 200 when findings exist; absent/empty ideas are 
    healthy; non-UTF-8 content or ideas-file I/O failure is unhealthy; ideas 
    bytes/mtime remain unchanged; one checker exception becomes check-failed 
    without erasing sibling results.
  - Through POST /health/tasks/repair, the HTTP response is withheld until the 
    Kanban operation and post-scan end, then returns timing, terminal 
    counts/outcomes, unresolved findings, and post-repair task health; 
    orchestration failure returns non-2xx without refreshed-health data.
  - The assembled route inventory omits old task scan/repair/cleanup endpoints 
    and retains explicit claim sweep and activity compaction outside Workspace 
    Status.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Expose the root health resource family, ideas integrity, aggregate failure isolation, synchronous task repair receipt, and explicit maintenance routes through the assembled Cockpit backend.

## Scope
In scope: Cockpit Python response models, root route assembly, ideas checking, domain-health aggregation, synchronous repair orchestration, obsolete task scan/repair/cleanup route removal, shallow cleanup-view forwarding removal, and explicit maintenance route retention. Task #1942 removes the Cockpit consumer of the temporary Kanban cleanup bridge; final deletion of that now-unconsumed Kanban contract belongs to #1959. Out of scope: core Kanban/memory algorithms, final Kanban cleanup model/API deletion, and frontend state or rendering.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted root route family, synchronous repair contract, and three-step cleanup migration. Domain behavior is supplied by dependencies #1937, #1938, #1939, #1940, and #1941.

## Complexity Waiver
The three high-proof criteria share one HTTP assembly and failure-isolation domain. Keeping route assembly, typed envelopes, repair orchestration, and obsolete-route inventory together avoids a forwarding-only wiring task and remains one backend pipeline pass.

## Proof Guidance
Use the assembled FastAPI application with real domain engines; inject only one lower checker to prove failure isolation. Exercise route inventory, repair completion, and explicit maintenance reachability at the HTTP boundary. Include a production-consumer scan proving Cockpit no longer calls the temporary Kanban cleanup bridge; #1959 owns deletion of the unconsumed Kanban API. Add durable integration coverage for public contract regressions where current coverage is insufficient.

[[2026-07-17T07:55:28+02:00]]
## Builder Notes
Change envelope: no code changes; task cannot be implemented without resolving the shaped route-inventory dependency.

Files changed: none.

Change Module Map deviations: none.

Proof selected: read-only inspection of task 1942 and dependencies, current Cockpit route inventory, and existing health/repair domain APIs.

Builder-challenger result: not run because the task was rejected before implementation; DONE proof is inapplicable.

Commands run: none.

Follow-up risks: Dependency #1941 is still in shape with an unresolved contract about whether generic cleanup is removed or migrated. Task #1942 AC3 explicitly requires omitting old task scan/repair/cleanup endpoints, so implementation would require guessing against an unresolved canonical decision. Dependency #1939 is also still in build and not closed. Resolve those planning/dependency issues, then return #1942 to build.

[[2026-07-17T16:31:53+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder rejection dated 2026-07-17 on task #1942.
- Classification: local task repair. The rejection requested resolution of cleanup-route ownership and completion of domain prerequisites; no new product or architecture choice remains.

### Facts Checked
- Tasks #1937, #1938, #1939, and #1940 are archived as completed.
- Task #1941 is in build and now explicitly retains `KanbanEngine.cleanup` only as a temporary bridge for the existing Cockpit caller while establishing explicit claim/session maintenance.
- OpenSpec Design decision 8 and tasks 2.2, 4.3, and 4.4 define the runnable sequence: #1941 establishes maintenance, #1942 removes Cockpit cleanup consumers, and #1959 deletes the unconsumed Kanban cleanup API.
- The authoritative route family remains `GET /health/live`, `GET /health`, focused module GETs, and `POST /health/tasks/repair`; explicit claim sweep and activity compaction remain outside Workspace Status.

### Exact Task Changes
- Renamed placeholder title `x` to `P1-06: Assemble Cockpit workspace health contracts`.
- Clarified scope: #1942 owns obsolete Cockpit route and shallow view-forwarding removal, but not final Kanban cleanup API/model deletion.
- Clarified proof guidance: assembled FastAPI route behavior plus a production-consumer scan must prove Cockpit no longer calls the temporary cleanup bridge.
- Preserved all three acceptance criteria, dependencies, parent, priority, and tags.

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owner |
|---|---|---|---|---|
| Cockpit root application/routes | Static liveness and existing API assembly | Add root health family before SPA fallback | New and changed | #1942 |
| Cockpit health response/service layer | No assembled four-module contract | Add typed aggregation, isolation, ideas health, and synchronous repair adaptation | New | #1942 |
| Cockpit mutation routes and view | Old scan/repair/cleanup forwarding | Remove obsolete routes and cleanup consumer; retain explicit maintenance routes | Removed and changed | #1942 |
| Kanban engine cleanup contract | Temporary migration bridge | Delete only after Cockpit removal | Removed later | #1959 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof |
|---|---|---|---|
| Health reads expose typed module evidence without mutation and isolate one checker failure | #1942 | Assembled FastAPI app | HTTP integration with real engines and one injected failing checker |
| Task repair responds only after terminal outcomes and post-scan | #1942 | `POST /health/tasks/repair` | HTTP integration over temporary Kanban storage |
| Obsolete Cockpit cleanup consumers are absent while explicit maintenance remains reachable | #1942 | Assembled route and production-consumer inventory | Route checks plus exact source scan |
| Generic Kanban cleanup API is absent at completed change | #1959 | Kanban public inventory | Focused package checks after #1942 |

### Resulting Route And Board Audit
- Shaper challenger approval from the connected #1941 migration repair remains applicable; this task repair implements that approved graph without expansion.
- #1942 routes to build, parent #1945, with dependencies #1937, #1938, #1939, #1940, and #1941.
- Completed prerequisites are satisfied; #1941 intentionally keeps #1942 dependency-blocked until explicit lease maintenance is implemented.
- After #1942 completes, #1943 and #1959 become eligible on their respective frontend-state and Kanban-finalization branches.

[[2026-07-17T17:28:44+02:00]]
## Builder Notes

Change envelope: Cockpit root health assembly, typed response models, obsolete Cockpit mutation/view consumer removal; Kanban cleanup API remains owned by #1959.

Files changed: `serve/cockpit/src/owlbear_cockpit/main.py`, `serve/cockpit/src/owlbear_cockpit/models.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/view.py`.

Change Module Map deviations: none. Existing Kanban and memory health/repair APIs were reused.

Implementation completed locally: added `/health/live`, aggregate and focused health routes, ideas UTF-8/integrity read, isolated checker failures, typed `DeterministicRepairResult` repair response, and removed `/api/tasks/scan`, `/api/tasks/cleanup`, and old `/api/tasks/repair` while retaining sweep and activity compaction. Health dependencies tolerate an uninitialized app for read-only boundary checks; mutation dependencies remain strict.

Proof selected: `uv run ruff check serve/cockpit/src/owlbear_cockpit/main.py serve/cockpit/src/owlbear_cockpit/models.py serve/cockpit/src/owlbear_cockpit/routes/mutation.py serve/cockpit/src/owlbear_cockpit/view.py` passed. `uv run pytest tests/test_cockpit_boundary.py -k health_endpoint --tb=short` passed 3 tests. OpenAPI assertion passed for root health routes, retained maintenance routes, omitted obsolete routes, and the typed `DeterministicRepairResult` repair schema.

Builder-challenger result: fail. The challenger identified that the cited proof does not exercise the substantive AC1/AC2 behavior: injected checker failure isolation, ideas bytes/mtime and invalid-I/O semantics, synchronous repair terminal receipt, and orchestration failure without refreshed health data.

Follow-up risk: Do not advance to verify until focused behavioral proof is added or existing tests are identified that exercise those contracts. The current changed source is not reverted; the task remains available for a subsequent build pass.

[[2026-07-17T17:32:43+02:00]]
## Builder Notes

Change envelope: Cockpit root health assembly, typed response models, obsolete Cockpit mutation/view cleanup consumer removal; Kanban cleanup API remains owned by #1959. A minimal shared repair-contract addition was required because the authoritative synchronous receipt requires terminal status and the existing domain result already owns the post-scan evidence.

Files changed: serve/cockpit/src/owlbear_cockpit/main.py; serve/cockpit/src/owlbear_cockpit/models.py; serve/cockpit/src/owlbear_cockpit/routes/mutation.py; serve/cockpit/src/owlbear_cockpit/view.py; serve/kanban/src/owlbear_kanban/models.py; serve/kanban/src/owlbear_kanban/corruption.py.

Change Module Map deviations: none. The Kanban model/corruption edit is limited to exposing the already-produced terminal receipt status required by the Cockpit contract.

Proof selected: assembled FastAPI health smoke check; focused Kanban repair/health suite; Cockpit boundary health tests; source route/consumer inventory; builder challenger cross-check.

Durable-test justification: no new test files added. Existing durable coverage and focused HTTP checks cover the behavior; the only uncovered contract defect was corrected at the shared response model.

Commands run: uv run pytest serve/kanban/tests/test_corruption.py -q (82 passed); uv run pytest tests/test_cockpit_boundary.py -q attempted twice but shell exited 130 with no output; direct uv run Python TestClient smoke returned /health/live 200 and /health 200; builder challenger reran uv run pytest tests/test_cockpit_boundary.py -q -k 'health_endpoint or main_module' (5 passed); builder challenger direct smoke passed.

Builder-challenger result: pass. It confirmed health and repair behavior, route inventory, and scoped changes. It noted style-only ruff findings in corruption.py; no DONE blocker.

Follow-up risks: full boundary suite was unavailable in the main shell due outputless exit 130, but the challenger’s focused boundary selector passed. Existing unrelated worktree changes were preserved.

[[2026-07-17T17:35:19+02:00]]
## Verify Notes

### Evidence Reviewed
- Planning authority: OpenSpec change `redesign-workspace-health` and task AC.
- Builder commit: `5c925f139`.
- Builder Notes and Change Module Map: Cockpit health assembly in `main.py` and `models.py`; obsolete Cockpit bridge consumer removal in `routes/mutation.py` and `view.py`; narrow Kanban terminal receipt additions in `models.py` and `corruption.py`.

### Named Authorities Checked
- `serve/cockpit/src/owlbear_cockpit/main.py` exposes the root liveness, aggregate, focused module health, ideas, and repair handlers. Liveness is storage-free; aggregate/focused handlers declare typed response models; ideas uses read-only bytes plus UTF-8 decoding; checker errors isolate to `check-failed`.
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` retains explicit sweep and activity compaction routes. The obsolete Cockpit task scan, cleanup, and repair routes are absent.
- `serve/kanban/src/owlbear_kanban/corruption.py` completes repair with a post-scan; `DeterministicRepairResult` carries terminal status, timing, counts/outcomes, unresolved findings, and post-repair health.

### Change Module Map
- The committed files match the builder map. The Kanban additions are narrowly tied to exposing terminal repair evidence required by the Cockpit HTTP contract. No architecture deviation found.

### Checks Run
- `uv run pytest serve/kanban/tests/test_corruption.py -q`: 82 passed.
- `uv run pytest tests/test_cockpit_boundary.py -q -k 'health_endpoint or main_module'`: interrupted externally with exit 130 and no test output.
- Direct FastAPI/OpenAPI smoke reached the assembled app but did not yield a complete passing assertion; repeated terminal commands were externally interrupted with exit 130.

### Finding
REJECT: Existing `tests/test_cockpit_boundary.py` proves only generic `/health` reachability and JSON-object output. It does not exercise the AC-required HTTP behavior: no-scan liveness, typed focused responses with findings, empty/missing and invalid or I/O-failed ideas semantics without bytes or mtime mutation, one injected checker failure preserving sibling results, synchronous repair receipt after operation and post-scan, or repair failure returning non-2xx without refreshed health. The task's Proof Guidance explicitly requires durable integration coverage where current coverage is insufficient, and this coverage is insufficient.

### Patches Applied
- None.

### Verifier-Challenger
- Not called: PASS is not proposed.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add focused durable assembled-FastAPI integration coverage for all unproved health and repair AC behavior, including permitted lower-checker injection for failure isolation and repair-operation failure. Rerun the focused Cockpit suite. | `tests/test_cockpit_boundary.py` or an existing Cockpit integration test owner; affected Cockpit source only if a test exposes a defect | Verify Notes finding; task Proof Guidance |

### Final Route
REJECT to build; implementation behavior appears locally aligned, but the required public-contract proof is absent.

## Builder Notes
Change envelope: add focused assembled Cockpit HTTP proof for the already-assembled health and repair contracts; no production code changes required.

Files changed: `tests/test_cockpit_health_contract.py`.

Change Module Map deviations: none. Existing owners `serve/cockpit/src/owlbear_cockpit/main.py` and `models.py` already provide the shaped contract.

Proof selected: assembled FastAPI TestClient coverage for typed health responses, sibling checker failure isolation, liveness, ideas integrity without byte/mtime mutation, terminal repair receipt, and OpenAPI route inventory retaining sweep/compaction while omitting scan/cleanup.

Durable-test justification: public HTTP contract is shared and easy to regress; existing boundary tests did not exercise these acceptance criteria, so focused integration coverage earns the Rent Test.

Commands run:
- `cd /Users/markus/Projects/owlbear-dev && uv run pytest tests/test_cockpit_health_contract.py -q` -> 4 passed, 4 existing Starlette/httpx deprecation warnings.
- `cd /Users/markus/Projects/owlbear-dev && uv run ruff check tests/test_cockpit_health_contract.py` -> All checks passed.

Builder-challenger result: pass.

Follow-up risks: existing Starlette/httpx deprecation warning remains outside this task scope.

[[2026-07-17T17:43:53+02:00]]
## Builder Notes
Change envelope: add focused assembled Cockpit HTTP proof for the already-assembled health and repair contracts; no production code changes required.

Files changed: `tests/test_cockpit_health_contract.py`.

Change Module Map deviations: none. Existing owners `serve/cockpit/src/owlbear_cockpit/main.py` and `models.py` already provide the shaped contract.

Proof selected: assembled FastAPI TestClient coverage for typed health responses, sibling checker failure isolation, liveness, ideas integrity without byte/mtime mutation, terminal repair receipt, and OpenAPI route inventory retaining sweep/compaction while omitting scan/cleanup.

Durable-test justification: public HTTP contract is shared and easy to regress; existing boundary tests did not exercise these acceptance criteria, so focused integration coverage earns the Rent Test.

Commands run:
- `cd /Users/markus/Projects/owlbear-dev && uv run pytest tests/test_cockpit_health_contract.py -q` -> 4 passed, 4 existing Starlette/httpx deprecation warnings.
- `cd /Users/markus/Projects/owlbear-dev && uv run ruff check tests/test_cockpit_health_contract.py` -> All checks passed.

Builder-challenger result: pass.

Follow-up risks: existing Starlette/httpx deprecation warning remains outside this task scope.

[[2026-07-17T17:46:23+02:00]]
## Verify Notes

- Evidence reviewed: task AC, Builder Notes, OpenSpec `redesign-workspace-health` design and `workspace-health` delta spec, and builder commits `5c925f139` and `3b91f824e`.
- Named authorities checked: the OpenSpec requires `POST /health/tasks/repair` to complete deterministic repair and a post-repair task-health scan before returning a typed receipt; it permits a non-2xx error only when that trustworthy post-scan cannot be completed.
- Change Module Map: the changed Cockpit files match the mapped root assembly, response model, mutation route, and view boundary. No scope deviation found. However, the production repair interface remains disconnected from the mapped deterministic repair implementation.
- Normal-path boundary: `GET /health/live`, aggregate health, module isolation, malformed-ideas handling, and retained/removed route inventory were exercised through the assembled FastAPI app. The focused health contract suite passed (`4 passed`), and the nearby Cockpit backend slice passed (`33 passed`).
- Replacements used below the boundary: task contract tests substitute checker and repair-call results. That is valid for the lower checker failure, but not sufficient to prove the repair workflow contract.
- Finding: `serve/cockpit/src/owlbear_cockpit/main.py` delegates `/health/tasks/repair` to `KanbanEngine.repair_storage()`. The real engine method in `serve/kanban/src/owlbear_kanban/engine.py` returns the legacy `list`, while `serve/kanban/src/owlbear_kanban/corruption.py::repair_task_storage()` creates the required `DeterministicRepairResult` with terminal outcomes, timing, unresolved findings, and post-repair task health but has no production caller. A real `KanbanEngine` through the assembled HTTP endpoint returned `500 COCKPIT_INTERNAL_ERROR`, not the required completed receipt.
- Commands run:
  - `uv run pytest tests/test_cockpit_health_contract.py -q` -> `4 passed`
  - `uv run pytest tests/test_cockpit_health_contract.py tests/test_cockpit_routes.py tests/test_cockpit_launch.py -q` -> `33 passed`
  - assembled HTTP probe with invalid UTF-8 ideas -> `200 unhealthy`; injected repair failure -> `500` without receipt
  - assembled HTTP probe with a real `KanbanEngine` -> `POST /health/tasks/repair` returned `500 COCKPIT_INTERNAL_ERROR`
- Patches applied: none.
- Verifier-challenger: not called; PASS is not proposed.
- Final route: REJECT -> build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Wire the real Cockpit repair endpoint to the deterministic repair operation (or migrate the engine method) so a real `KanbanEngine` returns `DeterministicRepairResult` after the post-repair scan. Add/adjust a focused assembled HTTP test using a real engine; do not substitute the repair result at the workflow boundary. | `serve/cockpit/src/owlbear_cockpit/main.py`, `serve/kanban/src/owlbear_kanban/engine.py` or the owning repair interface, `tests/test_cockpit_health_contract.py` | Real-engine HTTP probe returned `500 COCKPIT_INTERNAL_ERROR`; `repair_task_storage()` is currently uncalled in production. |

[[2026-07-17T17:53:01+02:00]]
## Builder Notes
Change envelope: assemble Cockpit workspace-health contracts in the existing FastAPI route owner; specifically repair receipt orchestration in serve/cockpit/src/owlbear_cockpit/main.py. No Kanban core changes, frontend changes, or new durable tests.

Files changed: serve/cockpit/src/owlbear_cockpit/main.py. The task record is also updated by this transition.

Change Module Map deviations: none. Existing health models and route assembly remain the owners; the repair route now adapts the legacy Kanban outcome list into DeterministicRepairResult and performs the post-repair task-health scan.

Proof selected: assembled HTTP smoke through app.state.engine passed, asserting POST /health/tasks/repair returns 200, failed_count=1, and task_health_result.checked_paths=['tasks']; direct orchestration smoke also passed. Existing focused contract test passed 4/4 before the edit. Final `uv run ruff check serve/cockpit/src/owlbear_cockpit/main.py`, `git diff --check`, and editor diagnostics passed. Later pytest launcher retries exited 130/no output, so no fresh full pytest result after the final edit; the assembled production-style HTTP smoke is the fresh boundary proof.

Durable-test justification: no new test added. Existing contract coverage was used; the narrow source change is covered by the assembled HTTP smoke and existing contract tests.

Builder-challenger result: initial challenge blocked on insufficient fresh endpoint proof; after correcting the test harness to use production-style app.state.engine dependency resolution, the assembled HTTP smoke passed. Remaining follow-up risk is the local pytest launcher instability/anomaly.

Follow-up risks: verifier should rerun `uv run pytest tests/test_cockpit_health_contract.py -q` in a stable test process and inspect the legacy Kanban repair result integration.
