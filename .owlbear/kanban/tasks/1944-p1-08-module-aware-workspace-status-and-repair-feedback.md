---
id: 1944
title: 'P1-08: Module-aware Workspace Status and repair feedback'
status: verify
priority: medium
created: 2026-07-17T02:32:30.849128+02:00
updated: 2026-07-21T13:42:55.779229+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - health
parent: 1945
depends_on:
  - 1943
  - 1969
ac:
  - Given checking, healthy, attention, unhealthy, and check-failed module 
    states, Workspace Status renders an overall light plus 
    task/request/memory/ideas lights and labels; repair remains available when 
    task repairable_count is positive even if unresolved findings make the task 
    row red.
  - Given a completed or partially failed task repair, closing 
    confirmation/popover leaves a dismissible receipt showing completion time 
    and removed/moved/quarantined/skipped/failed/unresolved counts; only 
    unresolved/failed item details are shown, and polling does not erase the 
    receipt.
  - The assembled Cockpit Workspace Status has no generic Cleanup control or 
    task-only scan path, and VS Code integrated-browser observation shows gray 
    initial state followed by module results without overlap or lost feedback.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Replace the task-only status and generic Cleanup experience with a four-module Workspace Status, one task-repair action, and a dismissible repair receipt that survives overlay closure and polling.

## Scope
In scope: Cockpit Workspace Status components and Shell assembly, module and overall indicators, repair availability, confirmation/result presentation, receipt dismissal, generic Cleanup removal, and integrated-browser visual/workflow proof. Out of scope: backend contracts, provider ordering internals, memory purge, and broad keyboard/accessibility expansion.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted module rows, status colors, unresolved-only detail rule, and repair receipt lifetime. Ordered frontend state is supplied by dependency #1943.

## Complexity Waiver
Package-local behavior checks and the VS Code integrated browser are both required: component checks protect state/interaction behavior, while the assembled browser proves overlay lifetime, layout, and visible state transitions. They cover one UI failure domain and should finish in one frontend pass.

## Proof Guidance
Run package-local frontend checks and use the VS Code integrated browser for the assembled workflow. Capture screenshots where they materially prove initial gray state, module layout, or retained feedback; avoid adding durable visual tests unless they protect a recurring product risk.

[[2026-07-17T08:04:08+02:00]]
## Builder Notes

**Verdict:** REJECT to shape. No product files were changed.

**Change envelope:** The shaped implementation is limited to Cockpit Workspace Status components and Shell assembly, module/overall indicators, task-repair availability, confirmation/result presentation, receipt dismissal/lifetime, generic Cleanup removal, and integrated-browser proof. Backend contracts and provider ordering internals are explicitly out of scope; ordered frontend state is supplied by dependency #1943.

**Blocking source evidence:** Dependency #1943 remains in `shape` and depends on #1942. The required health contract is not available in the current source: `GET /health` is only a `{"status":"ok"}` stub; focused `/health/tasks`, `/health/requests`, `/health/memory`, and `/health/ideas` routes are absent; `POST /health/tasks/repair` is absent. Upstream #1942 is itself blocked by the unresolved cleanup-route contradiction in #1941, where the requested cleanup removal conflicts with existing Cockpit consumers while Cockpit route changes are out of scope. Implementing #1944 now would require inventing the provider/API contract, violating the change envelope.

**Files changed:** None.

**Change Module Map deviations:** None; implementation did not begin because the mapped dependency interface is unresolved.

**Proof selected:** Dependency/source inspection was the cheapest discriminating check. It falsified the assumption that the supplied frontend health contract exists. No package tests or browser proof were run because no implementation was made.

**Durable-test justification:** None; no tests were added or changed.

**Commands run:** None; source/dependency evidence was obtained through read-only task and codebase inspection.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|-----------------|---------|----------|
| 1 | shape | Resolve the cleanup-route contradiction and define the authoritative backend health route inventory, including ownership of existing Cockpit consumers. | #1941, #1942; `serve/cockpit/src/owlbear_cockpit/view.py`; `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Required `/health/*` routes and `POST /health/tasks/repair` are absent; existing cleanup consumers conflict with the upstream removal premise. |
| 2 | shape | Complete and advance dependency #1942, then implement and advance #1943 so the ordered module-health provider contract is available to #1944 without frontend guessing. | #1942, #1943 | #1943 is still `shape`; #1944 depends on it. |
| 3 | shape | Re-dispatch #1944 only after #1943 is build-ready and its provider/API contract is authoritative. | #1944 | Current task scope explicitly treats #1943 as the source of ordered frontend state. |

[[2026-07-17T16:29:05+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder rejection dated 2026-07-17 on task #1944.
- Classification: mechanical hold after rechecking the rejection chain. No product, architecture, acceptance, or dependency change is required for #1944.

### Facts Checked
- The cleanup-route contradiction cited in the rejection is resolved by the approved three-step migration recorded on #1941 and aggregate #1945. Task #1941 is now in build; final Kanban cleanup deletion is owned by #1959 after Cockpit consumer removal.
- Backend prerequisite #1939 is archived as completed.
- Task #1942 remains in shape and owns the authoritative Cockpit health and repair route inventory.
- Task #1943 remains in shape, depends on #1942, and owns the ordered frontend provider/API contract consumed by #1944.
- Task #1944 still depends directly on #1943, so its current scope and AC remain coherent and must not be implemented by inventing provider contracts.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Cockpit backend health routes | Health, repair, and explicit maintenance HTTP contract | Implement before frontend consumers | #1942 |
| Cockpit web provider/hooks | Ordered module state, refresh, repair merge, receipt state | Implement after #1942 | #1943 |
| Workspace Status and Shell UI | Module rows, repair flow, retained receipt, Cleanup removal | Implement after #1943 | #1944 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Backend health/repair contract is authoritative before frontend consumption | #1942 | Assembled FastAPI route inventory |
| Older responses cannot replace newer health/repair state | #1943 | Provider at fetch boundary |
| Module-aware status and retained receipt use the supplied provider contract | #1944 | Assembled Cockpit UI and integrated browser |

### Resulting Route And Board Audit
- No task fields, AC, parent, or dependencies changed.
- #1944 remains in shape, parent #1945, depending on #1943.
- Required sequence remains #1942, then #1943, then #1944.
- Re-enter `/shape 1944` only after #1943 has completed its own shape repair and advanced to build; until then, retaining #1944 in shape prevents implementation against an invented interface.

[[2026-07-21T10:44:56+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: the 2026-07-17 Builder rejection and latest mechanical-hold Shape Notes on #1944.
- Classification: mechanical reroute under `w-task-repair`. No product behavior, architecture, acceptance meaning, task ownership, parent link, or dependency change is required.

### Facts Checked
- The rejection required #1944 to remain in shape until #1943 supplied the authoritative ordered frontend health-state contract.
- #1942 is archived `completed` and supplies the assembled Cockpit health/repair HTTP contract.
- #1943 is archived `completed`; its final Verify and Collect Notes cover initial checking state, module precedence, refresh ordering, repair snapshot merge, and receipt retention.
- #1944 depends only on #1943 and the board reports its dependency state as `ok`.
- Parent #1945 still owns aggregate running-Cockpit closure and remains gated on #1944.
- No pending or resolved structured request exists for #1944.

### Contract And Artifact Audit
- Existing Outcome, Scope, Planning Authority, Change Module Map, Product Invariant Map, proof guidance, parent, dependency, and AC remain coherent and unchanged.
- The working tree contains a pre-existing seven-path candidate baseline-curation delta in Cockpit tests: `ErrorContract.test.tsx`, `Shell.callbacks.test.tsx`, `SidecarUX.test.tsx`, `useRepairFlow.test.ts`, and deletion of `TailwindStylelint.test.ts`, `repairStorage.edge-cases.test.ts`, and `repairStorage.test.ts`. Builder must compare those artifacts with the full #1944 UI scope and preserve unrelated dirty Cockpit work rather than treating the candidate test delta as the complete feature.

### Resulting Route And Board Audit
- Advance #1944 from shape to build.
- Preserve parent #1945, dependency #1943, all three AC lines, priority, and tags.
- Builder owns the Workspace Status/Shell UI boundary and must run package-local behavior proof plus assembled integrated-browser proof before DONE.

[[2026-07-21T10:51:12+02:00]]
## Builder Notes

Verdict: REJECT to shape. No product or test file was changed by this builder invocation; pre-existing dirty work was preserved.

Change envelope: #1944 owns only the Cockpit Workspace Status/Shell UI, module indicators, task repair interaction, retained receipt, generic Cleanup removal, and frontend/browser proof. Backend health assembly and deterministic repair contracts are supplied by archived dependency #1942 and are explicitly out of scope.

Blocking source evidence:
- Committed `HealthModule` and `_module_health()` omit `repairable_count`; `_module_health()` returns `unhealthy` for any finding rather than `attention` for repairable-only task findings. A real Workspace Status therefore cannot implement the accepted repair-availability and severity contract from the supplied response.
- Committed `POST /health/tasks/repair` calls legacy `KanbanEngine.repair_storage()`. That method quarantines files and creates action-request tasks, while the accepted authority requires `repair_task_storage()` to perform deterministic repair and return terminal counts, unresolved findings, and post-repair health.
- Existing dirty changes in `serve/cockpit/src/owlbear_cockpit/main.py` and `tests/test_cockpit_health_contract.py` already begin correcting the production repair call, confirming the missing upstream owner, but they are outside #1944 and are not committed at the delivered HEAD.
- The current frontend `WorkspaceRepairResponse` also omits receipt timing/count fields; that frontend projection is #1944-owned, but implementing it cannot make the real backend boundary valid.

Proof selected: direct comparison of the named OpenSpec authority, public Pydantic/FastAPI response boundary, frontend provider types, and real `KanbanEngine.repair_storage()` implementation. This is the cheapest check and falsifies exact-SHA assembled browser completion before UI edits.

Change Module Map deviation: none applied. Widening #1944 into Cockpit backend or Kanban domain code would violate its shaped boundary.

Durable-test justification: no tests added. The pre-existing seven-path frontend baseline-curation delta remains untouched and must be re-audited after the upstream contract is delivered.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|-----------------|---------|----------|
| 1 | shape | Add one corrective build leaf under parent #1945 that restores the accepted assembled health contract: task module repairability/severity fields and production deterministic repair invocation with a complete receipt. | `serve/cockpit/src/owlbear_cockpit/models.py`, `serve/cockpit/src/owlbear_cockpit/main.py`, `tests/test_cockpit_health_contract.py`; existing Kanban deterministic repair owner | Current committed response drops repairability and production repair invokes the legacy engine method. |
| 2 | shape | Make #1944 depend on that corrective leaf while preserving #1944 Outcome, Scope, AC, and frontend ownership. Add the corrective leaf to parent #1945's aggregate dependency gate. | #1944, #1945, new corrective task | Exact-SHA assembled UI proof requires the real supplied HTTP boundary. |
| 3 | shape | Re-dispatch #1944 only after the corrective leaf is verifier-closed; then consume the complete response, render the retained receipt, remove generic Cleanup/task-scan UI, and prove the assembled workflow. | #1944 | Current frontend-only implementation would false-green on fixtures. |

[[2026-07-21T10:57:11+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Builder rejection on #1944, which proved the archived #1942 delivery is incomplete at the real HTTP boundary.
- Classification: prescribed non-material graph repair under `w-task-repair`. Accepted product behavior, architecture, frontend ownership, and ordering are unchanged; the repair restores an already-approved prerequisite rather than inventing a new outcome.

### Corrective Graph
- Created #1969, `P1-11: Restore assembled workspace-health repair contract`, as a high-priority build leaf under parent #1945, depending on archived authority task #1942.
- #1969 owns `HealthModule` repairability projection, repairable-only versus mixed status mapping, production deterministic repair delegation, and real-engine FastAPI proof.
- Added #1969 as a dependency of #1944. Existing dependency #1943, parent #1945, Outcome, Scope, tags, priority, and all three AC lines remain unchanged.
- #1944 remains in shape until #1969 is verifier-closed, then mechanically resumes in build.

### Authority And Maps
- Accepted OpenSpec `redesign-workspace-health` authority determines the corrective behavior: repairable-only task findings are attention; mixed unresolved findings remain unhealthy while repair remains available; synchronous deterministic repair returns terminal timing/count/outcome/unresolved/post-health evidence.
- Change Module Map: #1969 owns Cockpit backend model/assembly and assembled HTTP proof; existing `owlbear_kanban.corruption.repair_task_storage` remains the read-only domain owner; #1944 retains Workspace Status/Shell UI ownership.
- Product Invariant Map: #1969 owns the real repairability/severity and deterministic receipt boundary; #1944 owns module rows, retained receipt, and Cleanup removal; #1945 owns aggregate running-Cockpit closure.

### Challenge And Audit
- Shaper-challenger: PASS. It confirmed the repair is non-material, the three AC lines are boundary-valid, real-engine proof fixes the fixture-only false archive, and invariant ownership is complete.
- Board audit target: #1969 in build with parent #1945 and dependency #1942; #1944 in shape with dependencies #1943 and #1969.

[[2026-07-21T11:13:49+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Builder rejection on #1944 and its prescribed corrective dependency #1969.
- Classification: mechanical reroute under `w-task-repair`. No product behavior, architecture, acceptance meaning, proof boundary, task ownership, parent link, or dependency change is required.

### Facts Checked
- The rejection required #1944 to remain in shape until #1969 restored and verifier-closed the real Cockpit HTTP contract.
- #1969 is archived `completed`. Its exact-SHA Verify Notes at `5f711cabec6870f413834c924bcca44ce809b562` prove repairable-only versus mixed task severity, preserved `repairable_count`, direct deterministic repair, complete terminal receipt fields, and the negative failure envelope through assembled FastAPI routes.
- #1943 is archived `completed` and remains the ordered frontend state owner.
- #1944 has no child tasks, no pending or resolved structured request, and dependency state `ok`.
- The pre-existing seven-path candidate baseline-curation delta remains an artifact-to-scope audit obligation for Builder; it is not treated as the complete feature.

### Resulting Route And Board Audit
- Advance #1944 from shape to build.
- Preserve parent #1945, dependencies #1943 and #1969, Outcome, Scope, Planning Authority, Change Module Map, Product Invariant Map, all three AC lines, priority, and tags.
- Builder now owns only the Workspace Status/Shell UI boundary: consume the delivered response, render four module rows and retained receipt, remove generic Cleanup/task-only scan UI while preserving memory purge, audit task-owned baseline-curation paths, and run package-local plus assembled integrated-browser proof.
- No board or planning-artifact mutation beyond this status transition and Shape Notes is required.

[[2026-07-21T13:42:55+02:00]]
## Builder Notes

**Verdict:** DONE to verify.

**Change envelope:** Replaced the task-only scan and generic Cleanup experience with a four-module Workspace Status, task repair confirmation, and a session-retained dismissible receipt. Memory purge remains a separate explicit flow. Provider ordering and receipt ownership continue to come from #1943.

**Files changed:** Cockpit Shell, repair API/types, Workspace Status, RepairPanel, RepairReceipt, provider/health/repair hooks, and removal of legacy Cleanup/HealthBadge/task-scan runtime paths. Retained Vitest and Playwright fixtures were migrated to `/health`; obsolete scan/Cleanup/legacy-repair tests were removed and durable Workspace Status/receipt regressions added. The task record and the two-file dependency correction below are included. The pre-existing candidate delta was audited: scan/repair portions in `ErrorContract`, `Shell.callbacks`, `SidecarUX`, legacy repair tests, and related fixtures now belong to this contract; unrelated `TailwindStylelint.test.ts`, `MemoryTab.routing.test.tsx`, `memoryPurgeFlow.verify.test.ts`, memory/config/domain changes, #1968 artifacts, and all memory candidates remain unstaged.

**Change Module Map deviation:** Assembled proof found archived dependency #1969 still returned file-only post-scan task health after repair, allowing a transient false-green state when graph findings remained. `serve/cockpit/src/owlbear_cockpit/main.py` now replaces that helper snapshot with canonical `engine.task_health()` and `tests/test_cockpit_health_contract.py` binds mixed repairable/unresolved graph evidence. This repairs #1969's existing complete-post-repair-health AC in its mapped Cockpit boundary; no new backend contract was added. Builder-challenger explicitly accepted this dependency correction with transparent deviation evidence.

**Proof selected:** Component tests bind state and pointer ownership; assembled FastAPI tests bind the canonical repair response; Playwright and VS Code integrated-browser proof bind portals, real pointer sequencing, overlay lifetime, and desktop/mobile geometry.

**Durable-test justification:** New tests protect three observed regressions that are easy to reintroduce and hard to prove in jsdom alone: a portaled confirmation unmounted on pointerdown before POST, file-only repair health falsely projected green despite unresolved graph evidence, and a fixed receipt overlapped its source popover/escaped the mobile viewport under PCanvas containment.

**Commands and results:**
- `npm test -- --maxWorkers=2`: 123 files passed; 1,879 passed, 2 skipped. Current provider contract also passed 49/49; post-format focused tests passed 42/42.
- `uv run pytest -q tests/test_cockpit_*.py`: 290 passed, 4 known Starlette/httpx deprecation warnings. Focused health contract: 7/7.
- `npm run build && npm run lint:css && npm run lint:html`: passed; existing Vite large-chunk advisory only.
- `uv run lint serve/cockpit/src/owlbear_cockpit/main.py tests/test_cockpit_health_contract.py`: passed; unrelated TODO warnings only.
- `npm run test:e2e:all -- --project=chromium --grep-invert "assembled Memory"`: 175/175 passed.
- Focused repair overlay Chromium regression: 2/2 passed. `git diff --check`: clean. Exhaustive maintained-source/E2E searches found no legacy task-scan/Cleanup symbols or selectors.

**Assembled browser evidence:** Real FastAPI/SPA fixture showed initial gray checking, then task unhealthy with 2 findings/1 repairable while requests/memory/ideas were healthy. Real repair POST returned 200 with moved=1, unresolved=1 and `MISSING_DEPENDENCY`; status stayed unhealthy immediately without a corrective GET. Success closed the source popover, receipt survived polling, measured 480x370 at x=784/y=72 in 1280x800 and 358x427.75 at x=16/y=72 in 390x844, then disappeared only on Dismiss.

**Builder-challenger:** `decision: pass`; no concrete blockers or auto-fixes. It accepted the #1969 correction as an accompanying dependency repair.

**Risks:** No functional blocker remains. Known non-task advisories are the Vite chunk-size warning and Starlette/httpx deprecation warnings.
