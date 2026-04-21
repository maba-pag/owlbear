# Synthesis — Brief A: MCP Tool Surface

**Panelists:** End-User (0.82), Architect (0.88)  
**Scope:** MCP caller contract only. Engine-agnostic.

---

## 1. Convergences

Both panelists agree on the following — these form the stable core of the recommendation.

| # | Point | Agreed by |
|---|-------|-----------|
| 1 | **Transparent archived reads.** `show_task` returns a standard task object with `status: "archived"` and `archival_reason` set. No error, no special parameter, no header-only mode. | End-User, Architect |
| 2 | **`archival_reason` enum:** `completed \| deprecated \| dropped \| duplicate \| wontfix`. Validated at MCP surface. Invalid value → ToolError. | End-User, Architect |
| 3 | **`archival_ref` field** on both output projections. Machine-readable link for deprecated/duplicate pointing to the superseding/target task. | End-User, Architect |
| 4 | **`completed` gating.** `move_task(status="archived", archival_reason="completed")` only valid when task is currently in `done` status. Preserves auditor-completion signal. | End-User, Architect |
| 5 | **`archival_reason` required on `move_task` archive.** Omitting it when `status="archived"` → ToolError. No reason-less archival. | End-User, Architect |
| 6 | **Section projection on `show_task`.** New optional param to fetch specific `## Heading` content from body instead of full body. Case-insensitive match against `##`-level headings. All matching occurrences returned (handles repeated headings like `## Review Evidence`). | End-User, Architect |
| 7 | **`ids` param on `list_tasks`.** Batch ID lookup mode. Exclusive — cannot combine with other filter params (ToolError if attempted). Returns summaries for requested IDs including archived. Missing IDs silently omitted. | End-User, Architect |
| 8 | **`create_tasks` (new tool).** Batch create for planner. All-or-nothing atomicity. Failure identifies failing index. | End-User, Architect |
| 9 | **`pick_tasks` dispatch projection widened** to `{id, status, priority, title, tags}`. `task_id` renamed to `id` for consistency with `TaskSummary`. | End-User, Architect |
| 10 | **Drop `file` from output projections.** Leaks storage structure. No MCP caller uses it. | End-User, Architect |
| 11 | **Drop vestigial params from `edit_task`.** Remove deprecated `depends_on` (trap param), deprecated `tags`, and `status` (use `move_task`). | End-User, Architect |
| 12 | **`end_work` auto-archive.** `outcome="success"` at terminal status → auto-archives with `archival_reason="completed"`. Implicit, no parameter needed. | End-User, Architect |
| 13 | **`archival_reason` + `archival_ref` on both `TaskSummary` and `TaskFull`** (or `KanbanTask`). Both null for non-archived tasks. | End-User, Architect |
| 14 | **No-silent-ignore principle.** Invalid or inapplicable parameter combinations raise ToolError, not silent drop. | End-User, Architect |

---

## 2. Disagreements

### D1. Tool count: 9 vs 10 — `list_sessions`

- **Architect** proposes `list_sessions` as tool #10 — exposes orphan engine capability for orchestrator stuck-session detection. Concrete consumer identified.
- **End-User** does not include it. Lists it under "Out-of-Scope Follow-ups" as low-effort engine exposure, but not part of the archive-focused surface.

### D2. Section param: singular vs plural

- **End-User** proposes `sections` (plural) — comma-separated heading names in one param. Returns matched sections in body order. Adds `missing_sections: list[str]` to the response shape listing requested-but-not-found headings.
- **Architect** proposes `section` (singular) — one heading name per call. Missing section → `body` is `null` and `guidance` includes a "not found" message. No dedicated `missing_sections` field.

**Sub-divergence — missing section signaling:**
- End-User: explicit `missing_sections` list on response; body is empty string if all missing.
- Architect: `body` is `null` when not found; guidance string is the signal.

### D3. `archival_ref` — required vs optional, type, forbidden-when rules

- **End-User:** `archival_ref: str` (coerced to int). **REQUIRED** for deprecated/duplicate (ToolError if omitted). **FORBIDDEN** for completed/dropped/wontfix (ToolError if set).
- **Architect:** `archival_ref: int` (default 0). **Optional** for deprecated/duplicate ("should" provide but omission is not an error). Accepted but ignored for other reasons.

### D4. Batch-create intra-batch dependencies

- **End-User** proposes `depends_on_batch: list[int]` — 0-indexed position references within the batch (backward refs only, no cycles). Enables full 20-task graph in 1 call.
- **Architect** proposes no intra-batch deps — `depends_on` references pre-existing IDs only. Planner issues D calls (one per dependency layer, typically 3 for a 20-task graph).

### D5. `list_tasks` `archived` param — keep vs drop

- **End-User:** **DROP** `archived: bool`. Replace with `status="archived"` (explicit filter). Rationale: no overlapping modes.
- **Architect:** **KEEP** `archived: bool`. Purpose: `archived=true` includes archived tasks *alongside* active tasks in scan results. `status="archived"` filters to archived-only.

### D6. `end_work` archive-reject path

- **End-User** adds `archival_reason` + `archival_ref` params to `end_work` for `outcome="reject"` with `move_to="archived"`. Enables one-call reject-and-archive. Without it, agent needs 3 calls (append, release, archive).
- **Architect** keeps `end_work` lean — only auto-archive on success. No explicit archival params.

### D7. `edit_task` on archived tasks — mutable vs immutable

- **End-User** allows `archival_reason` and `archival_ref` editing on archived tasks. One-call correction beats un-archive/re-archive.
- **Architect** makes archived tasks immutable via MCP. "Archived tasks are terminal — no edits."

### D8. `create_tasks` return type

- **End-User:** returns `KanbanTask[]` (full task objects).
- **Architect:** returns `TaskSummary[]` (lightweight, no body). Rationale: minimize response size for large batches.

### D9. Projection naming: `KanbanTask` vs `TaskFull`

- **End-User** uses `KanbanTask` (current name).
- **Architect** renames to `TaskFull` to pair with `TaskSummary`. More descriptive of the projection role.

---

## 3. Recommended Resolution

For each divergence, a resolution optimized for: minimum agent context cost, surface coherence, and no-backwards-compat freedom.

### D1. `list_sessions` → **Defer (side with End-User)**

`list_sessions` has a concrete consumer (orchestrator) but is not archive-related. Brief A's scope is archive + surface coherence. Adding it here increases the brief's surface without serving the stated outcomes. Capture as a 1-line follow-up for the next surface pass.

### D2. Section param → **Singular `section` (side with Architect), but adopt `missing_sections` signaling from End-User**

Plural `sections` invites multi-heading requests that balloon response size — the exact problem section projection exists to solve. Singular `section` enforces surgical extraction. However, Architect's "body is null" signaling is weaker than End-User's explicit `missing_sections` list. Recommended hybrid:

- Param: `section` (singular, one heading name).
- Missing: `body` is `null`, `missing_sections: ["requested_heading"]` on the response.
- Found: `body` contains all matching `##` blocks, `missing_sections` absent.
- Multiple matches: `guidance` includes occurrence count (per Architect).

This gives agents a programmatic signal (check `missing_sections` field) rather than parsing guidance strings.

**Open tension:** the End-User's multi-section request has a real use case (memory-curator wants 2 sections from 1 task). Single `section` means 2 calls. Accept this as a V2 consideration — the common case is 1 section per call.

### D3. `archival_ref` → **Required for deprecated/duplicate, forbidden otherwise (side with End-User), but keep `int` type (side with Architect)**

The End-User's strict enforcement is correct: if you're archiving as deprecated, you *must* name the successor. "Optional" archival_ref will be skipped under pressure (Architect acknowledges this risk). Strict validation at the MCP surface is free and prevents data quality decay from day one.

Type: `int` with `0` as sentinel for "not provided" (Architect) is cleaner than string-coerced-to-int (End-User). Follows existing `parent` param pattern.

Combined: `archival_ref: int` (default 0). Required when reason is `deprecated` or `duplicate` (ToolError if 0). Forbidden for `completed`, `dropped`, `wontfix` (ToolError if non-zero).

### D4. Batch-create intra-batch deps → **No intra-batch deps (side with Architect)**

`depends_on_batch` adds meaningful complexity: index validation, cycle detection, backward-ref-only enforcement, a second dependency addressing scheme. The Architect's alternative (D calls per dependency layer, typically 3 for 20 tasks) is a 7x reduction from 20 individual calls. The marginal gain from 3→1 calls does not justify the param complexity and the dual-addressing semantics. KISS.

### D5. `list_tasks` `archived` param → **Drop it (side with End-User)**

The `archived: bool` flag has ambiguous semantics: does `archived=true` mean "only archived" or "include archived alongside active"? The End-User's approach is cleaner: `status="archived"` for archived-only, `ids` for mixed lookups. The one case Architect's `archived=true` serves (scan all tasks including archived) is rare enough to not justify a dedicated boolean.

### D6. `end_work` archive-reject → **Add it (side with End-User)**

The 3-call alternative (append + release + archive) is exactly the kind of agent-hostile multi-step dance the outcomes target. One atomic call for "this task is dead, here's why, release my claim" is a clear win. The params are narrowly scoped (only valid for reject+archived, ToolError otherwise) so they don't bloat the common `end_work` path.

### D7. `edit_task` on archived tasks → **Allow archival metadata correction (side with End-User)**

Immutability sounds clean but creates a practical dead-end: if an archival_reason is wrong, the only fix is un-archive, correct, re-archive — which the surface doesn't even support (no un-archive path). Allow `archival_reason` and `archival_ref` edits on archived tasks only. All other `edit_task` params remain forbidden on archived tasks (ToolError).

### D8. `create_tasks` return type → **`TaskSummary[]` (side with Architect)**

Batch create is a planner operation. The planner needs assigned IDs to wire dependencies in subsequent calls — `TaskSummary` provides that. Returning 20 full task bodies that the planner just authored is pure waste. Lightweight return for batch operations.

### D9. Projection naming → **`TaskFull` (side with Architect)**

`TaskFull` / `TaskSummary` is a self-documenting pair. `KanbanTask` doesn't signal "this is the full projection." No backwards compat constraint. Rename.

---

## 4. Open Decisions for the Mediator

These are not auto-resolvable — they involve genuine preference trade-offs.

### Q1. `list_sessions` — in Brief A or follow-up?

Outcome note (post walkthrough): final Brief A approval resolved this by **excluding `list_sessions` from the MCP surface**. Session/history capability moved to the Cockpit/engine path in Brief B. The discussion below is retained as historical synthesis, not the approved contract.

The Architect argues it's a concrete 1-tool addition with an identified consumer (orchestrator). The End-User scopes it out as non-archive. Both positions are defensible. **The question is scope discipline vs opportunistic cleanup.** If the Mediator wants Brief A to be archive+coherence only, defer it. If the Mediator wants "one surface pass, ship it all," include it.

### Q2. Multi-section projection — accept the V2 gap?

Both panelists acknowledge the multi-task and multi-section N+1 patterns (memory-curator, reviewer) remain unsolved. Singular `section` leaves the "2 sections from 1 task" case as 2 calls. The Mediator should confirm this is acceptable for V1 or decide whether plural `sections` is worth the response-size risk.

### Q3. `archival_ref` strictness — required or optional for deprecated/duplicate?

The synthesis recommends required (End-User position). The Architect's counterargument is real: "the link may not always be known" (e.g., deprecated before the successor is created). **If the Mediator anticipates frequent deprecation-before-successor scenarios, optional is safer. If data quality is paramount and the workflow can be sequenced (create successor first, then archive old), required is correct.**

---

## 5. Final Recommended Surface

Historical synthesis snapshot only: this section predates the final walkthrough decisions. The approved Brief A surface is the **8-tool** set in `brief.md` / `decisions.md`; `list_sessions` and `create_tasks` were both declined.

### Tool List

| # | Tool | Category | Change | Primary Consumer |
|---|------|----------|--------|-----------------|
| 1 | `list_tasks` | READ | EXTEND — add `ids`, drop `archived` bool, add `archival_reason` filter, `status` accepts `"archived"` | All agents |
| 2 | `show_task` | READ | EXTEND — transparent archived reads, add `section` param | All agents |
| 3 | `pick_tasks` | READ | EXTEND — widen dispatch to `{id, status, priority, title, tags}` | Orchestrator |
| 4 | `create_task` | MUTATION | KEEP | All agents |
| 5 | `create_tasks` | MUTATION | NEW — batch create, all-or-nothing, returns `TaskSummary[]` | Planner |
| 6 | `edit_task` | MUTATION | CLEAN — drop `status`, `depends_on`, `tags`; allow `archival_reason`/`archival_ref` on archived tasks | All agents |
| 7 | `move_task` | MUTATION | EXTEND — `status` accepts `"archived"`, add `archival_reason` (required) + `archival_ref: int` | Orchestrator, auditor |
| 8 | `start_work` | LIFECYCLE | KEEP | Builder, reviewer, auditor |
| 9 | `end_work` | LIFECYCLE | EXTEND — auto-archive on success; add `archival_reason`/`archival_ref` for reject+archived path | All pipeline agents |
| 10 | `list_sessions` | READ | NEW (conditional on Q1) | Orchestrator |

### Projection Schemas

#### TaskSummary (list operations, batch create)

```
TaskSummary {
  id:               int
  title:            string
  status:           string           // includes "archived"
  priority:         string
  tags:             string[]
  blocked:          bool
  block_reason:     string | null
  claimed:          bool
  parent:           int | null
  depends_on:       int[]
  archival_reason:  string | null    // enum or null (non-archived = null)
  archival_ref:     int | null       // successor/target ID or null
}
```

#### TaskFull (single-task operations)

```
TaskFull {
  guidance:         string[]
  id:               int
  title:            string
  status:           string           // includes "archived"
  priority:         string
  created:          string           // ISO 8601
  updated:          string           // ISO 8601
  claimed:          bool
  tags:             string[]
  parent:           int | null
  depends_on:       int[]
  blocked:          bool
  block_reason:     string | null
  body:             string | null    // full body, section content, or null (section not found)
  archival_reason:  string | null
  archival_ref:     int | null
  missing_sections: string[] | null  // present only when section param used and heading not found
}
```

#### DispatchEntry (pick_tasks)

```
DispatchEntry {
  id:        int
  status:    string
  priority:  string
  title:     string
  tags:      string[]
}
```

### `archival_reason` Enum

| Value | Meaning | `archival_ref` |
|-------|---------|---------------|
| `completed` | Pipeline completion (auditor) | Forbidden (must be 0) |
| `deprecated` | Superseded by newer task | Required (successor ID) |
| `dropped` | Removed from plan | Forbidden (must be 0) |
| `duplicate` | Merged into another task | Required (target ID) |
| `wontfix` | Out of scope / decided against | Forbidden (must be 0) |

Validation: enum-checked at MCP surface on every tool that accepts it. `archival_ref` must reference an existing task ID when required.

### `completed` Gating

`move_task(status="archived", archival_reason="completed")` → ToolError unless task is currently in `done` status. Pipeline-completed tasks reach `completed` via `end_work` auto-archive or manual archival of already-done tasks only.

### Legacy Archived Tasks

Pre-migration archived tasks will have `archival_reason: null` and `archival_ref: null`. Consuming agents must handle null. Migration is Brief C scope.

---

## Confidence

**0.85**

Strong panelist alignment on the core surface (14 convergence points covering all 4 locked outcomes). The 9 divergences are mostly shape/strictness decisions, not directional conflicts. Three open questions (Q1–Q3) require Mediator judgment — resolution of any of them doesn't invalidate the rest of the surface.
