## Context

The canonical `MemoryEntry` in `serve/memory` already owns seven states, score and assessment counters, and contested-task provenance. The Cockpit memory response and TypeScript model expose only the older field subset and four states; `MemoryTab` displays and sorts by confidence. The engine owns edit and resolve transitions, while both Cockpit and the MCP tools delegate to it.

The current engine blocks edits to contested, disputed, and stale entries to prevent an edit from escaping review. This also blocks Cockpit, and `resolve()` has no Cockpit or MCP route, leaving exceptional entries without a normal recovery path. Human approval already establishes the intended authority pattern: Cockpit may expose a domain operation that agents do not receive through MCP.

Observed implementation facts:

- `MemoryEngine.edit()` is the shared mutation boundary and currently rejects exceptional states.
- `curate_memory` loads the current entry and delegates to `MemoryEngine.edit()` through `_update_entry`.
- Cockpit memory routes delegate directly to `MemoryEngine` with optimistic concurrency tokens.
- Cockpit task navigation already uses the shared `openTaskDetail()` event utility.
- The current project store has no non-null `contested_by_task`, so no existing-file repair is required at proposal time.

## Goals / Non-Goals

**Goals:**

- Make Cockpit's memory API and UI represent all operator-relevant canonical fields and states.
- Preserve a compact overview while providing complete details and a structurally consistent edit mode.
- Separate field mutation from lifecycle resolution so exceptional entries can be corrected without escaping review.
- Keep resolution and exceptional-state editing under the human Cockpit surface while preserving agent restrictions in MCP.
- Repair contested provenance and stale recovery semantics at the owning domain layer.

**Non-Goals:**

- Add fields to the canonical memory schema.
- Expose raw unremarkable or non-use counters in Cockpit.
- Add authentication or a new remote trust boundary; Cockpit remains the laptop-local operator surface.
- Add an MCP resolve tool or permit MCP curation of exceptional states.
- Formalize pinning, confidence provenance, score colors, or score thresholds.

## Decisions

### 1. Keep transition semantics in `MemoryEngine`

`MemoryEngine.edit()` will permit every state except deleted. Existing approved edits will still transition to curated and clear `approved_at`; exceptional-state edits will retain their state and existing lifecycle metadata. `MemoryEngine.resolve()` will remain the sole resolution operation and will:

- allow only contested, disputed, and stale source states;
- transition to approved and set `approved_at` and `updated_at`;
- clear `contested_by_task` for every resolvable state; and
- reset `didnt_use_count` only when the source state is stale.

When an edit changes confidence, `MemoryEngine.edit()` will recompute score from the new confidence and the existing outstanding and unremarkable counts in the same persisted update. Other edits retain the existing score.

`record_factually_wrong()` will clear `contested_by_task` when a different task escalates contested to disputed. The same-task no-op remains unchanged.

Rationale: field editing and lifecycle resolution are distinct domain operations. Preserving state during an exceptional edit prevents dispute escape without creating an unusable entry.

Rejected alternative: resolve before editing. This erases the review condition before the correction is made and is currently impossible through normal UI.

Rejected alternative: implement exceptional editing or recovery in the Cockpit route. This would duplicate state-machine behavior outside the canonical engine.

### 2. Enforce agent restrictions at the MCP boundary

The MCP `_update_entry` path will explicitly reject contested, disputed, and stale entries before calling the now-more-permissive engine. No resolve tool will be registered. Cockpit will continue to call the engine directly and can therefore expose operator-only exceptional edits and resolution.

Rationale: the engine expresses valid domain operations; adapters express caller authority. Keeping the old engine-level restriction would prevent the human surface, while removing it without an MCP guard would silently expand agent authority.

Implementation sequencing is explicitly domain-first: make `MemoryEngine.edit()` permissive, then add the MCP adapter guard in the dependent task. This preserves the generated task order but temporarily allows MCP curation of exceptional states between those commits. The operator accepted that bounded authority expansion during shaping; it is not valid final behavior.

Rejected alternative: add an actor or privilege parameter to `MemoryEngine.edit()`. There are only two known adapters and no broader authorization framework; adapter-level policy is simpler and keeps identity concerns out of the domain method.

### 3. Expand the Cockpit response without exposing internal counters

`MemoryEntryResponse` will add `outstanding_count`, `score`, and `contested_by_task`; its existing fields, including title and content, remain. It will not add `unremarkable_count` or `didnt_use_count`. The frontend `MemoryEntry` type will mirror that response and expand `MemoryState` to all seven canonical values.

A new `POST /api/memories/{entry_id}/resolve` route will accept only `expected_updated_at`, delegate to `MemoryEngine.resolve()`, and return the standard entry envelope. Existing exception translation will preserve optimistic-concurrency conflict behavior.

Rationale: the API should expose exactly what the operator surface uses. Negative counters remain implementation inputs, while score and outstanding marks are user-facing signals.

Rejected alternative: return the full domain model. This would expose explicitly excluded counters and couple the UI contract to every storage field.

### 4. Preserve scan/detail duplication intentionally

The overview row will retain title, scope agents, and categories, replace confidence with score, and display score to two decimals without semantic color. Sorting will compare score descending first, then retain the current state-priority, created-time, and ID tie-breakers. The state-priority map and filters will explicitly cover all seven states.

Expanded details will show title as the accordion heading, content as the content panel, and the confirmed metadata fields. Scope agents, categories, and score remain duplicated because they serve both scanning and complete-detail contexts. Outstanding count will appear as **Outstanding marks** with a star icon and count.

Rationale: removing duplicated scan fields would make the overview less useful; omitting them from details would make details incomplete.

### 5. Make edit mode structurally correspond to details

Edit mode will expose controls for title, content, categories, confidence, and scope agents. ID, state, outstanding marks, score, source agent, timestamps, and contested task remain visible as read-only metadata. Deleted entries expose no edit action. Exceptional entries expose edit and resolve; edits preserve state, and resolve remains a separate explicit action.

Rationale: the operator should not lose system context while editing, and computed, provenance, lifecycle, identity, and timestamp fields must not become mutable through presentation changes.

### 6. Reuse Cockpit task-selection integration

When `contested_by_task` is a valid non-negative task identifier, the detail view will call the existing `openTaskDetail()` utility. Null values render an em dash. A malformed stored identifier will render as non-interactive text rather than throwing or dispatching an invalid task event.

Rationale: this matches Decisions-page navigation and avoids a second routing mechanism. Graceful fallback protects detail rendering from legacy or manually edited frontmatter.

### 7. Prove behavior at assembled boundaries

Load-bearing invariants and proof boundaries are:

- Domain transitions: memory engine tests cover state-preserving edits, provenance clearing, stale reset, and unchanged counters.
- Adapter authority: MCP tool tests prove exceptional curation remains rejected; Cockpit route tests prove exceptional editing and resolution with OCC.
- Operator workflow: Memory page component tests cover fields, sorting, states, editability, resolve actions, and task dispatch.
- Assembled experience: a browser check with representative approved, contested, disputed, stale, and deleted entries verifies layout, actions, navigation, and non-overlap.

Mocks may replace persistence beneath route or component tests, but proof of the human-only authority split must exercise both real adapters rather than only the engine.

## Risks / Trade-offs

- [The domain-first sequence temporarily broadens MCP authority between commits] → Keep the MCP guard as the immediate dependent task, do not dispatch downstream Cockpit work before it lands, and prove the final adapter restriction directly.
- [A permissive engine could accidentally broaden another adapter] → Audit all `MemoryEngine.edit()` callers and retain explicit rejection tests at the MCP boundary.
- [Existing frontend tests assert an exact older API field set or four-state union] → Update those tests as obsolete contract artifacts while adding scenarios for the canonical fields and states.
- [A stale entry could immediately stale again after resolution] → Reset only `didnt_use_count` in the same atomic domain update that resolves it.
- [Malformed string task IDs cannot open numeric Cockpit tasks] → Validate before dispatch and render a non-interactive fallback without breaking the detail view.
- [Duplicated overview/detail values can drift within the component] → Render both from the same typed entry object and shared formatters.
- [Confidence edits could leave score-led ordering stale] → Recompute score atomically whenever confidence changes.
- [Exceptional edits may change the factual content while preserving an old challenge] → This is intentional: the state remains exceptional until the operator explicitly resolves it.

## Migration Plan

1. Change and test domain transitions, then add the MCP adapter guard before relying on the permissive engine.
2. Expand the Cockpit response and add the resolve route with route-level tests.
3. Update frontend types, rendering, editing, and navigation with component tests.
4. Update memory lifecycle documentation and run the assembled browser check.

No schema migration is needed because all fields already exist and the current project store contains no non-null contested provenance. Rollback consists of reverting code and documentation; persisted entries remain readable by the prior schema. Entries resolved while the change is active retain valid existing fields, including a reset non-use count.

## Open Questions

None. Product behavior and authority boundaries were confirmed during refinement.