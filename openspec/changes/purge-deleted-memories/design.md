## Context

Memory entries are markdown files managed by `MemoryEngine`, which owns an mtime-aware parsed-entry cache and an ID-to-path index. Its current `delete()` operation physically removes pending entries but transitions every other deletable state to `deleted`; editing or deleting an already-deleted entry is rejected. Consequently, a tombstone's `updated_at` is the observed deletion-transition time under current behavior.

Cockpit holds one `MemoryEngine` on application state and exposes synchronous FastAPI memory routes. The Memory page already receives all entries, excludes `deleted` from its default state selection, and can display deleted entries through the existing state filter. It has no purge API or maintenance action. The installed Porsche Design System v4.1 provides `PInputNumber` with direct entry, numeric bounds, step granularity, validation feedback, and built-in increment/decrement controls.

This change crosses the core memory package, Cockpit backend, and Cockpit frontend. The core engine remains the authority for eligibility and physical deletion; the UI must not derive destructive scope from its filtered list.

## Goals / Non-Goals

**Goals:**

- Permanently remove only deleted entries at or beyond a request-specific whole-day age threshold.
- Give preview and execution one server-owned eligibility definition and one clock authority.
- Preserve filesystem containment and symlink protections during every unlink.
- Return useful partial outcomes when one eligible file cannot be removed.
- Keep deleted volume subordinate to the Memory page's primary entry metric.
- Make project-wide, filter-independent scope explicit before irreversible confirmation.

**Non-Goals:**

- Persisting a retention preference or adding configuration.
- Scheduling or automatically invoking purge.
- Restoring tombstones or changing ordinary delete transitions.
- Exposing purge through the Memory MCP server.
- Turning tombstone volume into a health signal.

## Decisions

### 1. Core engine owns eligibility, preview, and execution

Add a small typed purge result/preview contract and public `MemoryEngine` methods for previewing and executing purge. Both paths call one private eligibility helper that:

1. validates `min_age_days` as an integer greater than or equal to zero;
2. captures one timezone-aware UTC `now` per invocation;
3. computes `cutoff = now - timedelta(days=min_age_days)`;
4. considers only entries whose state is `deleted`; and
5. treats `updated_at <= cutoff` as eligible.

The engine must parse each tombstone timestamp through its existing ISO datetime handling rather than compare strings. Preview returns `deleted_total`, `eligible`, and `too_recent`; execution returns `purged`, `skipped`, and `failed`. Execution's `skipped` count is the too-recent deleted set. Each request computes against one cutoff instant so its categories reconcile.

**Why:** the engine owns entry state, paths, timestamps, and storage safety. Duplicating eligibility in React would introduce browser clock differences and risk coupling purge to visible filters.

**Rejected alternative:** compute preview entirely from `MemoryTab` entries. This is responsive but makes the browser an independent authority and cannot guarantee parity with execution.

### 2. Purge is a synchronous best-effort batch

Execution snapshots the current deleted entries and classifies them before mutation. For each eligible entry, it calls `storage.delete_entry(path, memory_dir=...)`, preserving containment and symlink checks. After each successful unlink, it removes that entry from `_id_to_path` and `_entries`. If the file is already absent, it reconciles the stale indexes and counts the desired absent outcome as purged. It catches and records other per-entry storage/filesystem failures, logs enough context for diagnosis, and continues with other eligible entries. Non-deleted entries never enter the candidate set.

The engine serializes every path that reads, reloads, replaces, or mutates `_entries`, `_id_to_path`, and the mtime cache with an instance-level re-entrant lock. This includes `load()`, `get_entries()`, ordinary write/delete transitions, preview, and purge. The lock must cover the `has_changed()` check together with any following reload so a purge-triggered directory mtime change cannot race a list request that replaces the indexes. Re-entrancy permits existing methods such as `get_entry()` to compose these guarded operations without deadlock. This is deliberately local synchronization for one process and one engine instance; no distributed lock is introduced.

**Why:** files are small, current mutations are synchronous, and the user requires failed counts rather than all-or-nothing rollback. Updating indexes immediately after each successful unlink keeps the in-memory result truthful even when later files fail.

**Rejected alternative:** fail the entire operation on the first unlink error. It loses useful cleanup and cannot provide meaningful purged/failed partial outcomes.

**Rejected alternative:** implement rollback. Restoring already-unlinked markdown safely would require retaining full source bytes and creates more destructive complexity than a best-effort maintenance action warrants.

### 3. Cockpit exposes separate preview and execution actions

Add two Memory routes using a nested action hierarchy:

- `POST /api/memories/purge/preview` with `{ "min_age_days": <integer> }`, returning `{ "deleted_total", "eligible", "too_recent" }`.
- `POST /api/memories/purge` with the same request body, returning `{ "purged", "skipped", "failed" }`.

Pydantic validates a strict non-negative integer and forbids extra fields. The backend does not accept filter criteria. Preview is non-mutating; execution is the only permanent-delete route. Route models map the core typed outcomes without exposing filesystem paths.

The execution response is authoritative if store contents change after preview. The UI refreshes afterward, so the current deleted count can differ from the preview without implying that filters affected execution.

**Why:** the nested preview route groups both operations under the purge capability, while the base `purge` action retains the unsurprising destructive meaning. Separate endpoints make irreversible mutation explicit and allow preview counts to change with the stepper before confirmation. Omitting filter fields structurally enforces project-wide scope.

**Rejected alternative:** one endpoint with a `dry_run` flag. It combines read and destructive semantics behind one boolean and makes accidental mutation easier at the API boundary.

**Rejected alternative:** use `/purge` for preview and `/purge/confirmed` for execution. `confirmed` exposes client interaction state as server API semantics and makes the base purge action non-destructive despite its name.

### 4. Memory header action carries the only deleted count

Derive `deletedCount` from the unfiltered `entries` collection returned by the latest complete Memory fetch. Reuse the current initial view load, browser-visibility refetch, and post-mutation refetch paths, including the new post-purge refresh. Filter state remains client-side and does not initiate a count fetch; keep polling paused and add no count-specific timer. Pass a compact secondary `PButton` through `WorkspaceHeader.actions` with label `Purge deleted (N)`. Keep it rendered and disabled when `N === 0`. Do not add another `WorkspaceHeaderMetric`, health color, filter badge, or count inside the state selector.

**Why:** the count explains action availability but is not a page-level metric. The unfiltered collection keeps the label independent of filter state, while existing load and mutation triggers keep it current for normal single-user use without background polling.

### 5. Confirmation owns ephemeral input, preview, and explicit warning

Opening the action creates local dialog state initialized to `30`; it is not stored outside the mounted Memory flow. Use `PInputNumber` with `controls`, `step={1}`, and `min={0}`. The frontend accepts only a finite integer greater than or equal to zero, renders PDS error feedback for invalid, negative, empty, nonnumeric, or fractional values, and disables confirmation while invalid.

For valid input, request a server preview and show:

- total deleted memories across the project;
- eligible at the selected age;
- too recent and therefore skipped; and
- a direct warning that active filters are ignored and purge applies across the project.

Disable confirmation while preview is loading or stale for the current value. Confirmation sends the exact previewed threshold to execution. Cancelling closes the dialog without mutation. A zero-day value is not special-cased in the UI or backend beyond the normal cutoff rule.

**Why:** associating preview state with the exact valid value prevents confirmation against counts from a prior threshold. Reset-on-mount provides the agreed ephemeral default without a settings mechanism.

### 6. Results remain visible outside the confirmation modal

After execution, close the confirmation, retain a Memory-page result receipt with purged, skipped, and failed counts, and refetch entries. The receipt remains until dismissed or another purge flow begins. If the request itself fails before producing a result, show an actionable error and preserve the current list.

**Why:** an irreversible maintenance action needs an inspectable receipt, particularly when partial failures occur. This follows Cockpit's existing cleanup phase model without coupling memory purge to workspace cleanup.

## Invariants and Proof Boundaries

| Invariant | Normal assembled proof | Replaceable lower dependency |
|---|---|---|
| Only age-eligible tombstones are physically removed. | Core engine test with eligible, exact-cutoff, too-recent, and non-deleted files, plus route-level request proof. | Clock provider and temporary filesystem fixture may be controlled. |
| Preview and execution ignore active filters and use the same eligibility rule. | Cockpit component/API integration test opens purge under restrictive filters and compares preview/result behavior. | Network transport may be mocked, but the component's unfiltered count and payload must remain real. |
| Every considered tombstone is reconciled. | Engine test forces one storage deletion failure and one already-absent file, then asserts `purged + skipped + failed == deleted_total at classification`. | Storage unlinks may be replaced with deterministic failing or already-absent test doubles. |
| Invalid input cannot mutate storage. | Component test proves confirmation disabled; route test rejects invalid payloads; engine test rejects invalid direct calls. | PDS shadow DOM internals need not be asserted. |
| Deleted count remains maintenance context. | Rendered Memory header proof shows one primary entry metric and `Purge deleted (N)` in actions, disabled at zero. | Styling implementation may change while hierarchy and labels remain. |
| Result feedback survives modal close and list refresh. | Component integration test completes a partial outcome, observes receipt, and observes refetched count. | Fetch responses may be controlled. |

## Risks / Trade-offs

- **[Preview becomes stale before confirmation]** → Execution re-evaluates against its own single cutoff and returns authoritative counts; the UI refreshes afterward.
- **[Concurrent reads, reloads, or mutations corrupt engine indexes]** → Serialize the mtime check/reload and every shared index read/replacement/mutation with one instance-level re-entrant lock; test a purge interleaved with an mtime-triggered `get_entries()` reload as well as an ordinary mutation.
- **[Partial physical deletion cannot be rolled back]** → Treat purge as explicit best-effort maintenance, retain per-request counts, log failed entry IDs internally, and preserve failed files/index entries.
- **[Filesystem timestamps or malformed entry times produce surprising eligibility]** → Use the validated model's ISO `updated_at`, existing parser, UTC arithmetic, and fail the request before unlink if classification cannot be completed coherently.
- **[Repeated preview requests race while stepping quickly]** → Abort or sequence client requests and accept only the response associated with the current threshold.
- **[Zero days removes fresh tombstones]** → Keep zero explicit in the input and eligible count, and retain irreversible project-wide warning; this is an accepted product choice.

## Migration Plan

1. Add core preview/purge contracts, comprehensive engine index/cache locking, and focused engine tests without changing existing delete outcomes.
2. Add Cockpit request/response models and routes with API tests.
3. Add the frontend API client and Memory purge flow with component tests.
4. Build and exercise the assembled Cockpit workflow, including restrictive filters, zero days, and a partial outcome.

No data migration is required. Existing tombstones already carry the state and timestamp needed for eligibility. Rollback removes the new routes and UI; tombstones not yet purged remain compatible. Permanently purged files cannot be restored by application rollback and rely on the repository's existing git safety net if recovery is required.

## Open Questions

None. Product choices and repository-controlled contracts needed for implementation are resolved.