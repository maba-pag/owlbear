## Context

Cockpit currently derives Workspace Status from two unrelated sources: task-feed freshness in `serve/cockpit/web/src/hooks/useBoard.ts` and a 60-second POST poll of `/api/tasks/scan` in `useScanPolling.ts`. `serve/kanban/src/owlbear_kanban/engine.py::scan_corruption` checks individual active/archive task files, while `corruption.py::scan_and_fix` separately performs board-wide duplicate handling. The visible Cleanup action calls `KanbanEngine.cleanup`, which releases claims, reconciles archived files, removes some duplicates, and closes stale sessions under one label. Its portaled confirmation closes the status popover, so the component-local result is no longer visible; this was reproduced in the running Cockpit through VS Code's integrated browser.

Request listing and activity parsing skip malformed records with logging rather than returning diagnostics. Memory already counts parse failures but silently selects one record for duplicate UUIDs. Ideas reads one UTF-8 Markdown file and reports I/O failures only as request failures. These observed behaviors are controlled by the source modules named above, `serve/memory/src/owlbear_memory/engine.py`, and `serve/cockpit/src/owlbear_cockpit/routes/ideas.py`.

HTTP does not reserve a mandatory health route format. An expired IETF health-check draft documents the common `status` plus component checks shape, while Kubernetes distinguishes cheap liveness/readiness probes from verbose operator diagnostics. The design uses ordinary HTTP safety semantics and keeps process liveness separate from workspace integrity.

Current Kanban writes use atomic replacement, selected compare-and-swap paths, no-overwrite moves, and a process-local allocation lock. There is no board-wide cross-process transaction honored by every Cockpit and MCP writer. A repair-only global lock would therefore create false confidence. Repair must revalidate each destructive candidate against current disk content and describe its post-scan as an observation at a timestamp, not as a state guaranteed to remain unchanged.

## Goals / Non-Goals

**Goals:**

- Provide one trustworthy health model for tasks, requests, memory, and ideas with independent module results.
- Keep health reads safe and non-mutating while supporting focused module reads.
- Detect complete task-file and task-graph integrity failures, especially every duplicate-ID topology.
- Apply only the agreed deterministic task repairs, without per-file decisions or automatic ID migration.
- Make repair completion and result lifetime explicit: synchronous terminal response, included post-repair health, session-retained receipt.
- Keep domain checks in their owning core packages and aggregation/presentation in Cockpit.
- Separate claim and activity maintenance from storage health repair.

**Non-Goals:**

- Purging soft-deleted memories.
- Treating workflow volume or valid lifecycle states as health failures.
- Providing server-persisted repair history, asynchronous job infrastructure, or arbitrary receipt expiry.
- Providing transactional isolation from every external filesystem editor or agent process.
- Automatically renumbering task IDs or rewriting graph references.
- Adding per-file comparison or repair-choice UI.

## Decisions

### 1. Use a health resource family with distinct liveness

Expose:

```text
GET  /health/live
GET  /health
GET  /health/tasks
GET  /health/requests
GET  /health/memory
GET  /health/ideas
POST /health/tasks/repair
```

`GET /health/live` replaces the current static `/health` response and performs no workspace scan. `GET /health` performs a fresh aggregate read; focused GETs run one owning check. A successfully assembled health document returns HTTP 200 even when integrity findings exist, because Cockpit remains available to diagnose them. A module exception becomes a typed `check-failed` result while siblings remain usable. Failure to construct the response itself uses the existing Cockpit error envelope and non-2xx status.

The health family is mounted explicitly at the FastAPI application root, before the SPA fallback, rather than under the existing `/api` router prefix. This intentionally gives the user-requested health resource a short operator-facing namespace. It also deliberately repurposes conventional `/health` from cheap liveness to application integrity; `/health/live` is the stable cheap probe that external monitors must use after migration.

The resource-first repair path keeps the repaired component explicit. There are no generic `/scan` or `/repair` verbs and no `GET /health/status` alias.

**Rejected alternatives:** Keep `/api/tasks/scan` (cannot represent other modules); use `/api/workspace-health` (unnecessarily clumsy); make `/health` both liveness and integrity (ambiguous operational semantics); encode scans as POST actions (violates the read-only model).

### 2. Use terminal backend states and frontend-only transient states

Backend module results use terminal states `healthy`, `attention`, `unhealthy`, and `check-failed`. Each contains `checked_at`, summary counts, and unresolved findings. `attention` means deterministic repair or reconciliation is available and no unresolved integrity failure has higher precedence. `unhealthy` means at least one unresolved finding. `check-failed` means the check itself did not produce trustworthy evidence.

Frontend state adds `checking` and `unknown`, both gray. Aggregation precedence is:

```text
unhealthy/check-failed > attention > checking/unknown > healthy
```

Connection failure is explicit overall context; it does not masquerade as task-storage health. A failed aggregate request marks overall status check-failed and leaves modules without new evidence unknown.

Check failure remains red by explicit product decision: although the module's integrity is unknown, monitoring itself is known to have failed. Visible `check failed` text distinguishes it from proven corruption. Connection loss likewise makes the overall indicator red while module rows without evidence remain gray.

**Rejected alternative:** Reuse task-feed `green/yellow/red` as workspace health. It conflates transport freshness with persisted integrity and caused the observed false initial `Stale` state.

### 3. Put checks and repairs in owning domains

- Kanban owns task file parsing, task graph validation, request validation, archive reconciliation, duplicate classification, and deterministic task repair.
- Memory owns unreadable-record and duplicate-UUID diagnostics. Loading for health must retain duplicate-path evidence rather than only the selected canonical entry.
- Cockpit owns ideas-path readability because ideas storage is currently a Cockpit feature.
- A new Cockpit health route/service adapts domain results into one API contract and isolates module exceptions.
- Cockpit frontend owns transient checking/unknown state, polling, aggregation presentation, and repair receipts.

Core packages do not import Cockpit or one another for aggregation. Cockpit may depend on the Kanban and memory libraries according to the existing package boundary.

**Rejected alternative:** Expand `kanban/corruption.py` into a workspace scanner. That would make Kanban know about memory and ideas and would combine per-file parsing, graph analysis, API aggregation, and UI policy.

### 4. Split task health into file evidence and board analysis

The Kanban task scanner first gathers per-path evidence without mutating files:

- raw bytes/read error;
- parsed frontmatter and normalized task data when available;
- normalized body with LF line endings and body line count;
- all independently determinable persisted-field violations;
- path location and filename identity.

A second board pass uses the gathered records to detect duplicate ID sets, invalid active/archive placement, missing graph targets, self-reference, and dependency cycles. It returns repairable counts separately from unresolved finding details. An unreadable file is a finding, never a clean skip.

Normalized frontmatter is the typed persisted task value, including preserved supported extra fields, with representation-only YAML differences removed. Semantic equality requires equal normalized frontmatter and equal normalized body. The implementation must define this normalization once and use it for both classification and pre-delete revalidation.

### 5. Apply the agreed deterministic duplicate matrix

Task repair re-scans current storage rather than accepting a client finding list. Classification and repair operate on the complete set of records sharing an ID. A rule applies only when its predicate holds for every member of that set; repair never selects a convenient pair from a heterogeneous set. For each duplicate set:

| Condition | Action |
|---|---|
| Complete cross-directory set is semantically identical and archived | Delete active copies; retain one deterministic archive copy |
| Complete same-directory set is semantically identical | Keep the canonical generated filename when present, otherwise the lexicographically first path; delete the rest |
| Complete same-directory set has identical normalized frontmatter and one unique greatest body line count | Retain the unique largest-body record; move every smaller-body record to `.owlbear/kanban/quarantine/` without creating action-request tasks |
| Same-directory set has different bodies and a tie for greatest body line count | Leave complete set unchanged; unresolved |
| Any records in the set have different normalized frontmatter | Leave complete set unchanged; unresolved |
| Cross-directory set is semantically identical but not archived | Leave complete set unchanged; unresolved location conflict |
| Cross-directory set is not semantically identical | Leave complete set unchanged; unresolved |
| Any heterogeneous set not wholly matching a rule | Leave complete set unchanged; unresolved |

Archive reconciliation moves an archived-state record from active to archive storage when no destination conflict exists. Destination conflicts enter the duplicate matrix before any move.

Before unlinking, moving, or quarantining a candidate, repair re-reads and re-normalizes every involved path and confirms that the classification still holds. A changed or missing candidate becomes a skipped/failed terminal outcome and is not destructively handled based on stale evidence. Moves retain no-overwrite semantics. Git history is the recovery safety net for completed deterministic deletions.

**Rejected alternatives:** Offer comparison screens (the user wants fix-or-report); quarantine exact copies (unnecessary retained clutter); use title, raw filename, character count, or fuzzy similarity as extra heuristics (weak evidence); renumber IDs (breaks task and request identity references).

### 6. Keep repair synchronous and return its postcondition

`POST /health/tasks/repair` executes in the request handler and does not return until all candidate operations have terminal outcomes and a post-repair task scan has completed. The response contains:

- `status: completed` for an ended orchestration, even when some item outcomes failed;
- `started_at` and `completed_at`;
- counts and outcome records for removed, moved, quarantined, skipped, failed, and unresolved items;
- remaining unresolved findings;
- the post-repair task-health result with its own `checked_at`.

Per-item failures do not abort unrelated candidates. A failure that prevents a trustworthy post-scan returns a non-2xx error and no refreshed-health claim. The post-scan is evidence observed after repair outcomes, not a promise against later concurrent writes.

No immediate GET follows a completed repair. The client merges the returned task result into its current aggregate state. Normal health polling later supersedes that health snapshot but does not erase the action receipt.

Every health request carries a client request generation, and every terminal module result carries `checked_at`. The frontend accepts only a result newer than the module result it already holds. This prevents an aggregate request started before repair from overwriting the repair response's newer task snapshot when it completes afterward.

If measured runtime later exceeds a suitable synchronous request budget, a separate change may introduce `POST /health/tasks/repairs` returning 202 plus an operation resource. No queue, operation persistence, or retention policy is introduced now.

### 7. Retain repair feedback as session UI state

The latest task repair receipt lives above the popover/confirmation component so closing either overlay cannot destroy it. It remains visible from Workspace Status until the user dismisses it or a later task repair replaces it. Full page reload or Cockpit restart clears it. Health polling updates health only.

The task repair action remains available whenever `repairable_count > 0`, even when unresolved findings make the task module red rather than yellow. Status severity and action availability are independent fields.

The receipt reports completion time and aggregate removed, moved, quarantined, unresolved, skipped, and failed outcomes. Detailed rows are shown only for unresolved and failed items. This separates current derived health from historical action feedback without creating a server audit store.

### 8. Remove generic cleanup and preserve explicit maintenance

Remove the Cockpit `/api/tasks/cleanup` route, Cleanup UI, and the old task scan/repair routes. Decompose the engine behavior so archive reconciliation and duplicate correction are owned by task health repair. Preserve `/api/tasks/sweep` or its explicit Kanban-maintenance successor for expired claims outside Workspace Status. Activity compaction remains explicit maintenance.

Stale activity-session closure remains coupled to claim maintenance rather than health repair. If the existing sweep result cannot report both released claims and reconciled sessions without breaking its callers, adapt the engine internally while preserving the explicit sweep operation's user meaning; do not reintroduce a generic cleanup action.

### 9. Prove behavior at owning and assembled boundaries

Load-bearing invariants and proof boundaries are:

| Invariant | Normal proof boundary | Replaceable lower dependency |
|---|---|---|
| Health GETs never mutate storage | Domain health API test with before/after filesystem snapshot | Temporary filesystem |
| Aggregate survives one module failure | Cockpit route test with one injected failing checker | One domain checker |
| Duplicate matrix is deterministic | Kanban engine repair tests over real temporary task/archive trees | Filesystem root |
| Repair response follows terminal operations and post-scan | Cockpit repair route integration test using real Kanban engine | Clock only |
| No follow-up GET is required | Frontend integration test from repair click through returned health/receipt | HTTP client |
| Receipt survives overlay closure and polling | Assembled component/browser workflow | API responses |
| Loading is gray, never false healthy/stale | Assembled initial-load browser/component test | Delayed health response |

Static typecheck/build and focused package tests supplement but do not replace these behavioral boundaries.

## Risks / Trade-offs

- **[Race with external writers]** Per-file revalidation cannot provide a transaction across arbitrary editors or processes. → Re-read immediately before destructive operations, use no-overwrite moves, report changed candidates, timestamp the post-scan, and avoid immutable-snapshot claims.
- **[Aggressive deletion removes a wanted exact copy]** Deterministic rules intentionally favor cleanup over preservation. → Require semantic equality, deterministic survivor selection, immediate revalidation, and rely on Git history as the accepted recovery mechanism.
- **[Larger body is not necessarily better]** The user explicitly chose body line count as the same-header conflict heuristic. → Apply it only within one directory with identical normalized frontmatter; ties and all cross-directory differences remain unresolved.
- **[Full scans become slow on very large boards]** Aggregate reads inspect four local stores. → Keep focused module endpoints, avoid duplicate follow-up scans after repair, measure before introducing caching or asynchronous jobs, and expose `checked_at`.
- **[Route replacement breaks current frontend/tests]** The change intentionally has no compatibility requirement. → Migrate backend and frontend in one change and delete stale route tests rather than preserving aliases.
- **[Existing monitor calls `/health`]** Repurposing the current liveness path could make an external probe run full scans. → This laptop-local project accepts the breaking route change; document and test `/health/live` as the replacement probe.
- **[Partial repair completes with failures]** A blanket success message could mislead. → Distinguish orchestration completion from item success and retain failed/unresolved details in both response and receipt.
- **[Module status terminology diverges from infrastructure conventions]** Workspace integrity is not service availability. → Keep `/health/live` conventional and document the workspace-health response as application-specific.

## Migration Plan

1. Introduce domain health/result models and read-only Kanban task/request scans with focused tests.
2. Add deterministic Kanban repair and archive reconciliation with per-path revalidation and post-repair task health.
3. Add memory duplicate diagnostics and Cockpit ideas health.
4. Add Cockpit health aggregation and the new route family; replace static `/health` with `/health/live`.
5. Move claim/session maintenance out of generic cleanup and remove obsolete task scan/cleanup/repair routes.
6. Replace frontend task-scan polling with aggregate health state, module rows, gray transient states, task repair, and session receipts.
7. Validate the assembled normal workflow and failure states in the integrated browser, then remove stale components and tests.

Rollback is a normal Git revert. Deterministic repair can mutate user data, so implementation testing uses fixtures only; production repair is user-triggered and Git history remains the content rollback mechanism.

## Open Questions

None currently block implementation. The asynchronous-operation threshold is deliberately measurement-driven and outside this change rather than an unresolved design choice.
