## Why

Cockpit's Memory page exposes an older subset of the memory model, so operators cannot see the assessment score, exceptional lifecycle states, outstanding marks, or contested-task provenance that now determine how entries behave. Exceptional entries are also operational dead ends in Cockpit: they cannot be edited or resolved even though those are human moderation decisions.

## What Changes

- Replace overview confidence with the computed score, sort entries primarily by score descending, and continue showing title, scope agents, and categories for scanning.
- Support all seven memory states in Cockpit rendering and filters.
- Expand memory details to show content and all operator-relevant schema fields while leaving internal negative assessment counters hidden.
- Keep score, scope agents, and categories intentionally present in both the overview and details.
- Make edit mode mirror the detail layout: title, content, categories, confidence, and scope agents are editable; identity, lifecycle, provenance, computed, and timestamp fields remain visible and read-only.
- Allow Cockpit to edit every non-deleted entry. Edits to contested, disputed, and stale entries preserve their state; approved-entry edits retain the existing downgrade to curated.
- Add a human-only Cockpit resolve action for contested, disputed, and stale entries without adding an MCP resolve tool or enabling MCP curation of those states.
- Link an active contested entry to the task that first reported it factually wrong.
- Correct lifecycle provenance by clearing `contested_by_task` when a second task escalates an entry to disputed and when an exceptional entry is resolved.
- Give resolved stale entries a fresh non-use window by resetting only `didnt_use_count` while preserving positive and score-relevant assessment history.

## Normal Workflow

The operator opens Memory and scans entries ordered by score, with each row also showing its title, scope agents, and categories. Expanding a row reveals the content and complete operator-relevant metadata; entering edit mode keeps the same information structure, adds editable controls for mutable fields, and retains system-managed values as read-only context.

For a contested entry, the operator can open the reporting task directly. For a contested, disputed, or stale entry, the operator can correct mutable content without escaping its state and then explicitly resolve it through Cockpit, returning it to approved under human authority.

## Boundaries

### In Scope

- Cockpit memory API response and resolve endpoint.
- Memory overview sorting, summary fields, state filters, detail metadata, editing, task navigation, and resolution UI.
- Domain behavior needed for state-preserving exceptional edits, provenance clearing, and stale recovery.

### Out of Scope

- Score coloring or confidence-based visual markers.
- Pinning or overloading confidence as a formal priority mechanism.
- Displaying `unremarkable_count` or `didnt_use_count`.
- Adding MCP resolution or allowing MCP curation of contested, disputed, or stale entries.

### Preserved Behavior

- Approved-entry edits downgrade the entry to curated and require reapproval.
- Deleted entries remain non-editable tombstones.
- Normal MCP curation for pending, curated, and approved entries is unchanged.
- Score continues to derive from confidence, outstanding assessments, and unremarkable assessments.

## Product Promise

Cockpit becomes the complete human management surface for the current memory lifecycle: operators can accurately scan retrieval value, inspect relevant state and provenance, edit every live entry, and recover exceptional entries without granting agents authority to erase disputes or revive stale content.

## Capabilities

### New Capabilities

- `cockpit-memory-lifecycle`: Operator-facing memory overview, details, editing, provenance navigation, and human-only lifecycle resolution in Cockpit.

### Modified Capabilities

None. The repository currently has no main OpenSpec capability specs.

## Impact

- Memory domain engine state transitions and their tests.
- Cockpit FastAPI memory response and mutation routes.
- Cockpit React memory API types, Memory page rendering, task-selection integration, and component tests.
- Memory lifecycle documentation describing edit, dispute, and resolution semantics.
- No new external dependencies and no MCP surface expansion.

## Success and Completion

- Real entries display score-based ordering, all seven states, the confirmed overview fields, and complete operator-relevant detail metadata.
- Edit mode mirrors the detail structure and changes only title, content, categories, confidence, and scope agents.
- A contested-task reference opens the corresponding Cockpit task detail and an absent reference renders safely.
- Exceptional-state edits preserve state, while explicit Cockpit resolution returns entries to approved.
- Dispute and resolution clear obsolete contested-task provenance; stale resolution also resets only accumulated non-use pressure.
- Backend route and state-machine tests, frontend component tests, and an integrated browser check cover representative approved, contested, disputed, stale, and deleted entries.

## Technically Done but Wrong

- Showing score while continuing to sort by confidence.
- Adding new states to TypeScript without exposing them in filters and state-dependent actions.
- Letting an edit silently resolve or otherwise escape contested, disputed, or stale state.
- Exposing resolution through MCP and allowing agents to erase human-review conditions.
- Showing a contested-task link after dispute or resolution when no active first challenge remains.
- Resolving stale without clearing its accumulated non-use pressure, causing immediate re-staling.
- Calling outstanding assessments "Starred," which implies a manual bookmark.
- Hiding read-only system fields in edit mode or making identity, lifecycle, provenance, computed, or timestamp fields editable.

## Decision Register

| Type | Statement | Basis | Status |
|---|---|---|---|
| User decision | Overview score has no color or special marker; pinning is excluded. | Score is a ranking value, and confidence does not encode formal pin provenance. | Confirmed |
| User decision | Score, scope agents, and categories appear in both overview and details. | The overview supports scanning while details provide complete context. | Confirmed |
| User decision | `outstanding_count` is presented as **Outstanding marks** with a star icon and count. | It records repeated exceptional assessments, not user bookmarking. | Confirmed |
| User decision | Resolution and exceptional-state editing are available through Cockpit but not MCP. | These operations are human moderation authority. | Confirmed |
| User decision | Resolving stale resets only `didnt_use_count`. | Resolution grants a fresh non-use window without erasing positive or score-relevant history. | Confirmed |
| User decision | Implement permissive engine edits before adding the MCP exceptional-state guard. | Preserves the generated domain-first implementation order; accepts a temporary MCP authority expansion between commits. | Confirmed |
| Evidence conclusion | Exceptional edits can preserve state instead of being blocked to prevent dispute escape. | State transition and field mutation are separate domain concerns. | Active |
| Accepted exclusion | Raw unremarkable and non-use counters remain hidden. | They are internal factors; outstanding marks alone provide operator-relevant positive evidence. | Confirmed |