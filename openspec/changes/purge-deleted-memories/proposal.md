## Why

Soft-deleted memories are intentional tombstones that preserve provenance and prevent accidental reuse, but there is currently no supported way to remove tombstones once that protection is no longer useful. Projects need deliberate lifecycle cleanup without treating deleted memories as unhealthy or requiring manual filesystem changes.

## What Changes

- Add a Memory-specific purge operation that permanently removes deleted memories meeting a user-selected age threshold.
- Add a compact `Purge deleted (N)` action to the Memory header, where `N` is maintenance context rather than a primary page metric.
- Add an irreversible confirmation flow with an ephemeral PDS numeric stepper, defaulting to 30 days and accepting whole numbers from 0 upward.
- Make purge independent of active Memory filters and state that project-wide scope explicitly in the confirmation.
- Show total deleted, eligible, and too-recent counts before confirmation, then report purged, skipped, and failed counts after execution.
- Preserve immediate physical deletion for pending memories and soft deletion for all other currently deletable states.

## Normal Workflow

The user opens the Cockpit Memory tab and sees `Purge deleted (N)` as a compact secondary header action. The action remains visible but disabled when `N` is zero; otherwise it opens a confirmation dialog where the user can type or increment/decrement the minimum tombstone age in whole days.

The value starts at 30 on each Memory view load and applies only to that purge request. The dialog explains that purge considers all deleted memories across the project regardless of active state, category, agent, or search filters. It shows how many tombstones are eligible and how many are too recent. After explicit confirmation, the user receives purged, skipped, and failed counts and the Memory list and action count refresh. The action count otherwise follows the latest full Memory load on initial view mount, browser visibility return, and successful Memory mutations; filter changes do not refetch it and no polling is added.

## Boundaries

### In Scope

- Permanent deletion of age-eligible entries already in the `deleted` state.
- Core memory behavior and a Cockpit API operation for project-wide purge.
- Cockpit Memory action, count, PDS numeric control, validation, irreversible confirmation, result feedback, and refresh.
- A zero-day threshold that makes every existing deleted memory eligible, including newly deleted entries.

### Out of Scope

- Scheduled or automatic purge.
- Persisted, project-level, or global retention preferences.
- Restoring deleted memories.
- Adding purge to the Memory MCP tool interface.
- Treating deleted count as a health failure or primary Memory metric.

### Preserved Remainder

- Deleting a pending memory continues to remove its file immediately.
- Deleting any other currently deletable state continues to create a tombstone by transitioning it to `deleted`.
- Deleted memories remain excluded from the default Memory state filter but available through the existing deleted-state filter.
- Active Memory filters remain view-only and never constrain lifecycle cleanup.

## Capabilities

### New Capabilities

- `memory-tombstone-purge`: Project-wide discovery, confirmation, permanent deletion, and outcome reporting for age-eligible soft-deleted memories.

### Modified Capabilities

None.

## Impact

- `serve/memory/`: core eligibility, contained physical deletion behavior, and instance-level serialization of cache/index reads, reloads, and mutations.
- `serve/cockpit/src/owlbear_cockpit/routes/memory.py`: purge request and response API contracts.
- `serve/cockpit/web/`: Memory header action, confirmation flow, PDS numeric input, API client, result feedback, and refresh behavior.
- Memory and Cockpit tests covering cutoff boundaries, state preservation, invalid input, filter independence, partial outcomes, and assembled interaction behavior.
- No new runtime dependency is required; the installed Porsche Design System provides the numeric control.

## Success and Completion

- The Memory header keeps the normal entry count as its only primary metric and presents deleted volume only inside `Purge deleted (N)`.
- Valid whole-number thresholds from 0 upward produce one project-wide eligibility result based on tombstone deletion time; invalid, negative, empty, or fractional input cannot start purge.
- Purge permanently removes eligible deleted entries while preserving newer deleted entries and every non-deleted entry.
- Active filters do not alter preview counts or execution scope, and the confirmation explicitly communicates that behavior.
- Every considered deleted entry is accounted for as purged, skipped, or failed, and the visible Memory state refreshes after execution.
- Concurrent reads, mtime-triggered reloads, ordinary mutations, and purge cannot replace or mutate the engine's shared indexes at the same time.

## Technically Done but Wrong

- Deleted volume appears beside the primary entry metric or is presented as a health failure.
- Purge silently follows active state, category, agent, or search filters.
- The selected age persists across view loads or requests.
- Invalid input silently becomes 30 days instead of blocking confirmation.
- A positive threshold removes tombstones newer than the cutoff, or zero days fails to include newly deleted entries.
- The operation returns only an undifferentiated success response or loses partial-failure feedback when the dialog closes.
- Implementing purge changes pending hard-delete or ordinary soft-delete behavior.

## Decision Register

| Type | Statement | Basis | Status |
|---|---|---|---|
| User decision | Soft-deleted memories are intentional tombstones, not unhealthy records. | Provenance preservation and accidental-reuse prevention are the reason soft deletion exists. | Active |
| User decision | Deleted volume appears only in the compact `Purge deleted (N)` action, not as a primary page metric. | It is maintenance context rather than relevant Memory-page performance information. | Active |
| User decision | The action remains visible and disabled when no deleted memories exist. | Preserves discoverability while making availability clear. | Active |
| User decision | The threshold defaults to 30 days on every refresh and is ephemeral to one request. | Different project cadences need manual flexibility without preference storage. | Active |
| User decision | Zero days is valid; negative, fractional, empty, and nonnumeric values block purge. | Supports deliberate immediate cleanup while keeping malformed input predictable. | Active |
| User decision | Purge ignores all active Memory filters, and the confirmation warns that it applies across the project. | Filters are inspection tools, not hidden destructive-operation inputs. | Active |
| User decision | Confirmation and results expose counts for the affected lifecycle states. | The user requires explicit irreversible approval and purged, skipped, and failed outcomes. | Active |
| User decision | The deleted action count refreshes with full Memory loads and successful Memory mutations, not filter changes or polling. | Single-user operation does not justify background polling; the count must still reconcile after local lifecycle actions. | Active |
| Accepted exclusion | No retention value is persisted. | The user explicitly chose a refresh-reset 30-day default changed manually per request. | Active |
| Evidence conclusion | A deleted entry's `updated_at` represents its deletion transition because deleted entries cannot be edited. | Current memory engine transition and edit guards. | Active |