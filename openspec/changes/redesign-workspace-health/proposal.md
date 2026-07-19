## Why

Cockpit's Workspace Status currently combines task-feed freshness with a partial Kanban corruption scan, labels loading as stale or healthy, and presents an ambiguous Cleanup action whose result disappears after confirmation. Users need a trustworthy, module-aware view of the runtime-mutated workspace data that can actually break, plus deterministic repair of safe cases and explicit reporting of everything that still requires attention.

## What Changes

- Replace the task-only status calculation with aggregate workspace health for tasks, decision/action requests, memories, and ideas, with an independent status indicator for each module.
- Represent checking and not-yet-checked states as gray instead of inferring stale, failed, or healthy state before evidence exists; aggregate the overall indicator from completed module results and connection state.
- **BREAKING**: replace the task-specific scan and generic cleanup/repair API surface with a health resource family: read-only aggregate and module health reads plus explicit module repair actions. Keep cheap process liveness distinct from workspace integrity.
- Expand task validation from first-error-per-file frontmatter checks to complete readable-file validation and board-wide integrity checks, including duplicate IDs/locations, invalid storage placement, broken parent/dependency/archival references, self-reference, and dependency cycles.
- Validate structured request storage independently, including unreadable or invalid records, duplicate request IDs, missing owning tasks, and pending/resolved placement drift.
- Report unreadable memory records and duplicate memory UUIDs as memory health findings. Treat memory lifecycle states, including deleted, as workflow state rather than health failure.
- Check the ideas document only for expected runtime failure modes: filesystem accessibility and UTF-8 readability. Missing or empty ideas content remains healthy.
- Repair deterministic task duplicate and placement drift without per-file choices: delete redundant identical copies, quarantine the smaller-body copy for same-directory records with identical normalized frontmatter, and leave ambiguous conflicts unresolved for the user.
- Make task repair synchronous and convergent. Its response includes timing, repair outcomes, failures, remaining unresolved findings, and a post-repair task-health snapshot produced before the response completes.
- Replace disappearing cleanup output with an action receipt retained in the current Cockpit session until dismissed or superseded, while health remains the latest derived workspace snapshot.
- Separate expired-claim sweeping and activity maintenance from storage health. Remove the generic Cleanup action that currently combines unrelated operations; preserve claim sweeping as a Kanban maintenance operation outside health.

## Normal Workflow

1. The user opens Cockpit and sees a gray overall Workspace Status indicator while tasks, requests, memory, and ideas are checked.
2. The indicator and module rows settle to green, yellow, or red from the returned evidence. A failed module check is explicitly labeled instead of allowing a false green.
3. If task health contains deterministic repair opportunities, the user runs the single task repair action without choosing among files or reviewing comparisons.
4. The repair request completes synchronously. Cockpit immediately uses the returned post-repair task-health snapshot, shows a retained receipt with removed, quarantined, unresolved, and failed counts, and exposes details only for unresolved or failed findings.
5. Later workspace mutations are reflected by the next health read; old action receipts do not become health state.

## Capabilities

### New Capabilities

- `workspace-health`: Module-aware read-only health checks, deterministic task repair, status aggregation, and durable-in-session repair feedback for Cockpit workspace data.

### Modified Capabilities

None. The repository currently has no canonical OpenSpec capabilities.

## Impact

- Cockpit backend routes and response models gain aggregate/module health resources and explicit repair contracts; the current `/api/tasks/scan`, generic cleanup, and task repair wiring are replaced.
- Kanban owns task-file, task-graph, request-storage, duplicate-repair, archive-reconciliation, and claim-maintenance behavior.
- Memory exposes health diagnostics for unreadable records and duplicate UUIDs without changing its lifecycle.
- Cockpit owns the ideas readability check and cross-module health aggregation.
- Cockpit frontend polling, status derivation, Workspace Status presentation, repair flow, and action feedback are redesigned around module results and synchronous repair receipts.
- Existing focused backend, frontend, and browser tests require replacement or extension for the new API and assembled workflow.

## Boundaries

### In Scope

- Runtime-mutated task, request, memory, and ideas storage.
- Process liveness as a distinct cheap endpoint and connection state as distinct status context.
- Read-only health scans, deterministic task repair, archive reconciliation, and explicit repair feedback.
- Claim sweeping remaining available outside health rather than being bundled into repair.

### Out of Scope

- Purging soft-deleted memories; the user explicitly reserved this as a separate feature.
- Treating pending requests, pending/stale/contested/deleted memories, empty ideas, or ordinary work volume as unhealthy.
- Automated task ID renumbering or graph-wide identity migration.
- Per-file repair choices, comparison screens, or server-persisted repair history.
- Background repair jobs and operation-resource polling unless measured runtime later proves synchronous repair unsuitable.

### Preserved Remainder

- Existing task, request, memory, and ideas mutation workflows remain unchanged except where health and maintenance APIs currently overlap them.
- Activity compaction and claim lease semantics remain Kanban maintenance concerns.
- Git history remains the recovery mechanism for deterministic destructive repairs.

## Success And Completion

- No overall or module indicator reports green or stale while its first check is still pending.
- One aggregate read returns independently typed results for tasks, requests, memory, and ideas even when one module check fails.
- Duplicate task IDs are detected within each task directory and across active/archive storage.
- Every agreed deterministic duplicate case is repaired without per-file interaction; ambiguous cases remain intact and are reported.
- A completed task repair response proves completion by including its post-repair task-health snapshot; the client does not need an immediate follow-up health request.
- Cleanup no longer combines claim release, archival movement, duplicate repair, and session reconciliation behind one unexplained action.
- Repair success, partial success, and failure remain visible after the confirmation dialog closes.

## Technically Done But Wrong

- The status light becomes gray during loading, but module rows still disappear or default to green before their checks complete.
- `/health` merely forwards the old task scan and omits requests, memory, or ideas.
- Duplicate IDs are displayed but deterministic copies are never repaired, forcing the user to adjudicate obvious cases.
- Repair returns `200` before background work finishes, then the client guesses when to refresh.
- Repair completes synchronously but returns only counts, requiring a second scan to learn whether storage is now healthy.
- A successful repair closes the dialog and loses its receipt, reproducing the current lack of feedback.
- Soft-deleted memories or pending decisions turn the overall indicator red despite being valid workflow states.

## Decision Register

| Type | Statement | Basis | Status |
|---|---|---|---|
| User decision | Overall and per-module health use gray for checking/unknown and evidence-based green/yellow/red states. | Explicit agreement after review of the live initial `Stale` state. | Active |
| User decision | Health covers tasks, requests, memory, and ideas because they are mutated during normal work and can break. | Explicit scope preference; tasks receive highest integrity priority because records move and reference one another. | Active |
| User decision | `/health` is a read-only aggregate resource with module reads and resource-first repair actions; cheap liveness remains separate. | Endpoint discussion informed by HTTP semantics and common health conventions. | Active |
| User decision | Expired claims are maintenance, not health, and must not be bundled with archive reconciliation. | Explicit disagreement with the current generic cleanup responsibility. | Active |
| User decision | Deterministic duplicate repairs execute directly; the UI exposes only unresolved or failed details. | Git history makes obvious deletion/quarantine acceptably low risk, and comparison workflows add no value. | Active |
| User decision | Task repair is synchronous and returns outcomes plus a post-repair health snapshot; no immediate follow-up GET is required. | Avoids timing assumptions, duplicate scans, and ambiguous result lifetime. | Active |
| Accepted exclusion | Soft-deleted memory purge is excluded from this change. | User reserved purge as a separate new feature. | Active |
| Rejected direction | Do not renumber duplicate task IDs automatically. | Identity changes would require graph-wide reference migration and carry materially higher risk. | Active |
| Rejected direction | Do not persist repair receipts forever or for an arbitrary server timeout. | Health is derived state; repair feedback is session-scoped action state, not a new audit subsystem. | Active |
