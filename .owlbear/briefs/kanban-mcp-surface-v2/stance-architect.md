# Architect Stance — Brief A: MCP Tool Surface

**Status:** FINAL — hardened through 2 Critic cycles  
**Scope:** MCP caller contract only. Engine is a black box.

---

## 1. Surface Coherence Audit (Current 8 Tools)

### Naming inconsistencies

| Issue | Detail |
|-------|--------|
| Noun mismatch | `start_work` / `end_work` use `_work`; all others use `_task` / `_tasks`. However, the `_work` suffix is **intentionally distinct**: it signals lifecycle operations (claim/release cycle), not task CRUD. "Start work on a task" conveys claiming + reading + beginning a session — `start_task` would conflate this with creating or activating. Keeping `_work` is a deliberate design choice, not an inconsistency. |
| Verb ambiguity | `pick_tasks` implies a write ("pick = choose"), but it's read-only. Misleading for a dispatch recommendation. |
| No plural/singular convention | `list_tasks` (plural, returns many) vs `show_task` (singular, returns one) is fine. But `pick_tasks` (plural, read-only) shares the plural suffix with `list_tasks` despite serving a different purpose. |

### Overlap

| Overlap | Detail | Verdict |
|---------|--------|---------|
| Two status-change paths | `move_task(status=X)` AND `edit_task(status=X)` both change status. Pure redundancy — same preconditions, same effect. | **Remove** `status` from `edit_task`. |
| Two block paths | `edit_task(block="reason")` AND `end_work(outcome="block")` both block a task. | **Keep both.** These are contextually distinct: `end_work(outcome="block")` is the lifecycle path (agent was working, hit a blocker, releases claim). `edit_task(block=...)` is the administrative path (block a task you're not working on, no claim involved). Different preconditions, different semantics. The status overlap was pure redundancy; the block overlap is workflow-contextual. |

### Vestigial parameters

| Param | Tool | Issue |
|-------|------|-------|
| `depends_on` | `edit_task` | Deprecated. Raises `ToolError` if used. Dead param in the schema. |
| `tags` | `edit_task` | Deprecated. Same — raises error. Pollutes tool schema. |
| `file` | return projection | Leaks storage structure (filename). No MCP caller needs this. |

### Missing capabilities

| Gap | Impact |
|-----|--------|
| No archived-task read | `show_task` returns error for archived IDs. Dependency resolution and audit trail broken. |
| No `archival_reason` | No structured trace of WHY a task was archived. |
| No batch ID lookup | Architect resolving 5 `depends_on` IDs → 5 sequential `show_task` calls. N+1 pattern. |
| No batch create | Planner creating 20 tasks → 20 sequential `create_task` calls. |
| No section projection | Every agent fetches full body (~2-5 KB) to extract one ~200-byte section. Largest context-window sink. |
| No session visibility | Orchestrator can't see stuck/stale work sessions via MCP. |
| No transition info | Agents can't query valid target statuses. M3 identifies `valid_transitions` as useful. **However**, the current model is trivially "any-to-any except self" — not valuable enough for a dedicated tool today. Revisit if transitions become constrained. |
| Dispatch shape too narrow | `pick_tasks` returns `{task_id, status}` but orchestrator skill consumes `id, status, priority, title, tags`. Gap forces N `show_task` calls after dispatch. |

---

## 2. Proposed Surface (10 Tools)

### Rename / Merge / Split / Drop Table

| Current Tool | Action | New Tool | Rationale |
|-------------|--------|----------|-----------|
| `list_tasks` | **EXTEND** | `list_tasks` | Add `ids` filter; add `archival_reason` + `archival_ref` to return projection |
| `show_task` | **EXTEND** | `show_task` | Archive-aware reads; add `section` param for body projection |
| `create_task` | **KEEP** | `create_task` | No change |
| `move_task` | **EXTEND** | `move_task` | Add `archival_reason` + `archival_ref` params |
| `edit_task` | **CLEAN** | `edit_task` | Drop `status` (use `move_task`), drop vestigial `depends_on`/`tags` |
| `start_work` | **KEEP** | `start_work` | No change |
| `end_work` | **EXTEND** | `end_work` | Auto-set `archival_reason="completed"` on auto-archive |
| `pick_tasks` | **EXTEND** | `pick_tasks` | Widen dispatch projection to include `priority`, `title`, `tags` |
| *(new)* | **ADD** | `create_tasks` | Batch create for planner; D calls (per dep layer) vs N individual |
| *(new)* | **ADD** | `list_sessions` | Expose orphan engine capability for orchestrator |
| `valid_transitions` (engine) | **SKIP** | — | Current model is trivially "any-to-any except self." Not enough value for a tool slot. Revisit when constrained transitions exist. |

### Complete Tool Specifications

---

#### 1. `list_tasks` — Board scan with filters

**Category:** READ  
**Returns:** `TaskSummary[]`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `status` | `string` | no | `""` | Filter by status enum |
| `tag` | `string` | no | `""` | Filter by tag |
| `priority` | `string` | no | `""` | Filter by priority enum |
| `search` | `string` | no | `""` | Full-text search in titles and bodies |
| `sort` | `string` | no | `""` | Sort field: `priority`, `updated`, `id`, `title`, `status`, `created` |
| `ids` | `string` | no | `""` | **NEW.** Comma-separated task IDs. Switches to ID-lookup mode (see below). |
| `unclaimed` | `bool` | no | `false` | Only unclaimed tasks |
| `archived` | `bool` | no | `false` | Include archived tasks in results |
| `limit` | `int` | no | `0` | Max results (0 = unlimited) |
| `reverse` | `bool` | no | `false` | Reverse sort order |
| `blocked` | `bool \| null` | no | `null` | `true` = only blocked, `false` = only unblocked, `null` = all |

**`ids` filter — ID-lookup mode:** When `ids` is provided, all other filter params **must be at their defaults**. If any other filter param is set alongside `ids`, the tool raises `ToolError` with `"Cannot combine 'ids' with other filters. Use 'ids' alone for ID lookup, or omit 'ids' for filtered scan."` This enforces clean two-mode semantics: callers use EITHER scan-with-filters OR ID-lookup, never a hybrid that silently surprises.

The tool returns summaries for exactly those IDs (active and archived), in the order given. If an ID doesn't exist, it is silently omitted from results (the caller can compare returned IDs against requested IDs to detect missing entries).

**Without `ids`:** Standard scan behavior. Filters AND-combine. `archived=True` includes archived tasks.

**Validation:** `status` must be a configured status or empty. `priority` must be a configured priority or empty. `sort` must be one of the enum values or empty. `ids` must be comma-separated integers.

---

#### 2. `show_task` — Single task full detail

**Category:** READ  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | yes | — | Task ID (numeric string) |
| `section` | `string` | no | `""` | **NEW.** Heading name to extract. When set, `body` contains only that section's content. |

**Archive behavior:** Returns the full task regardless of whether it's active or archived. No special parameter needed. Status field reads `"archived"` and `archival_reason` is populated.

**Section behavior:**
- When `section` is empty: `body` contains the full markdown body.
- When `section` is set: `body` contains **all matching `##` headings and their content**, in document order, preserving the `## Heading` delimiters. Multiple occurrences (e.g., repeated `## Review Evidence` sections from review loops) are all included.
- Section match is **case-insensitive** against `##`-level headings only.
- Each matching block spans from its `##` heading to the next `##` heading or end of body.
- If no matching section is found: `body` is `null`, `guidance` includes `"Section '{name}' not found in task {id}"`.
- `guidance` includes a count when multiple matches exist: `"Found {n} occurrences of '## {name}'"`.
- If a section exists but has no content below the heading: the heading line alone is returned.
- **V2 consideration:** A `section_index` param (0=first, -1=last, null=all) could support callers who want only the latest occurrence (e.g., retry handling needs the most recent `## Review Evidence`). For V1, returning all matches is the safe general-purpose default — callers can trivially split on `##` delimiters to extract first/last.
**Error:** `ToolError` if task ID does not exist (neither active nor archived).

---

#### 3. `pick_tasks` — Dispatch recommendation

**Category:** READ  
**Returns:** `DispatchList`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `limit` | `int` | no | `25` | Max tasks to return |
| `tag` | `string` | no | `""` | Filter by tag |

Gate filtering (blocked, dependency, claimed, TDD, clarity) and priority×status sorting remain as-is.

**Return shape — WIDENED:**
```json
{
  "dispatch": [
    {"id": 456, "status": "todo", "priority": "needed", "title": "Implement retry", "tags": ["phase-1"]},
    {"id": 123, "status": "backlog", "priority": "important", "title": "Add logging", "tags": []}
  ]
}
```

**Changes from current:**
- Added `priority`, `title`, `tags` to each dispatch entry.
- **Renamed `task_id` → `id`** to match `TaskSummary` field naming. The orchestration skill already references `id`, not `task_id`.
- The current `{task_id, status}` shape forced N `show_task` follow-ups for assignment decisions.

---

#### 4. `list_sessions` — Work session state *(NEW)*

**Category:** READ  
**Returns:** `WorkSession[]`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `filter` | `string` | no | `"active"` | Session filter: `active`, `all`, `failed-or-rejected`, `released` |

**Return shape:**
```json
[
  {
    "task_id": 480,
    "state": "running",
    "agent": "builder-abc",
    "started_at": "2026-04-19T10:30:00+00:00",
    "duration": 3600.0,
    "outcome": null
  }
]
```

**States:** `running`, `stuck`, `released`, `completed-pass`, `completed-fail`, `completed-rejected`.

**Primary consumer:** Orchestrator — stuck-session detection and dispatch decisions.

---

#### 5. `start_work` — Claim task and read

**Category:** LIFECYCLE  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | yes | — | Task ID |

**No changes.** Claims task, returns full detail. Raises `ToolError` if blocked or claimed by another agent.

---

#### 6. `end_work` — Complete lifecycle step

**Category:** LIFECYCLE  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | yes | — | Task ID |
| `note` | `string` | yes | — | Agent notes (appended with timestamp) |
| `outcome` | `string` | no | `"success"` | `success`, `fail`, `block`, `reject` |
| `block_reason` | `string` | no | `""` | Required when `outcome="block"` |
| `move_to` | `string` | no | `"research"` | Target status when `outcome="reject"` |

**Auto-archive behavior:** When `outcome="success"` and the task is at the terminal pipeline status, the task is archived with `archival_reason="completed"`. This is implicit — no parameter needed. The returned `TaskFull` will have `status: "archived"` and `archival_reason: "completed"`.

---

#### 7. `create_task` — Create single task

**Category:** MUTATION  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | `string` | yes | — | Task title |
| `body` | `string` | no | `""` | Markdown body |
| `depends_on` | `string` | no | `""` | Comma-separated dependency task IDs |
| `parent` | `int` | no | `0` | Parent task ID |
| `priority` | `string` | no | `""` | Priority enum |
| `status` | `string` | no | `""` | Initial status (defaults per board config) |
| `tags` | `string` | no | `""` | Comma-separated tags |

**No changes** from current.

---

#### 8. `create_tasks` — Batch create *(NEW)*

**Category:** MUTATION  
**Returns:** `TaskSummary[]`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tasks` | `string` | yes | — | JSON array of task specs (see below) |

**Task spec shape** (each element):
```json
{
  "title": "string (required)",
  "body": "string (optional, default '')",
  "depends_on": [int] ,
  "parent": int | null,
  "priority": "string (optional)",
  "status": "string (optional)",
  "tags": ["string"]
}
```

**Semantics:**
- Tasks are created **in order**. Each task receives a sequential ID.
- `depends_on` references **pre-existing task IDs only**. Batch-internal dependency references are not supported — if task B depends on task A and both are new, create A first (via `create_task` or an earlier `create_tasks` batch), then reference A's real ID in a subsequent call.
- Returns `TaskSummary[]` (not `TaskFull[]`) to minimize response size for large batches.

**Atomicity:** All-or-nothing. If any task spec fails validation, no tasks are created. Error message identifies the failing index and reason.

**Primary consumer:** Planner. Typical decomposition creates a layered dependency graph. With `create_tasks`, the planner issues one call per dependency layer: roots first (1 call), then layer-2 tasks referencing root IDs (1 call), etc. For a 20-task decomposition with 3 dependency layers, that's 3 calls instead of 20 — an order-of-magnitude reduction for typical graphs.

---

#### 9. `edit_task` — Edit task metadata and body

**Category:** MUTATION  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | yes | — | Task ID |
| `title` | `string` | no | `""` | New title |
| `body` | `string` | no | `""` | Replace entire body (**destructive** — prefer `append_body`) |
| `append_body` | `string` | no | `""` | Append to body |
| `timestamp` | `bool` | no | `false` | Prepend `[[YYYY-MM-DD]]` to `append_body` |
| `priority` | `string` | no | `""` | Priority enum |
| `parent` | `int` | no | `0` | Parent task ID |
| `add_tag` | `string` | no | `""` | Add tag |
| `remove_tag` | `string` | no | `""` | Remove tag |
| `add_dep` | `string` | no | `""` | Comma-separated dependency IDs to add |
| `remove_dep` | `string` | no | `""` | Comma-separated dependency IDs to remove |
| `block` | `string` | no | `""` | Block with reason |
| `unblock` | `bool` | no | `false` | Clear block |

**Dropped from current `edit_task`:**
- `status` — use `move_task`. Two status-change paths was a coherence failure.
- `depends_on` — vestigial deprecated param. Use `add_dep` / `remove_dep`.
- `tags` — vestigial deprecated param. Use `add_tag` / `remove_tag`.

**Multiple params per call:** Supported. E.g., `edit_task(task_id="480", add_tag="phase-2", priority="critical")` applies both in one call.

---

#### 10. `move_task` — Change status (including archive)

**Category:** MUTATION  
**Returns:** `TaskFull`

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | yes | — | Task ID |
| `status` | `string` | yes | — | Target status (includes `"archived"`) |
| `archival_reason` | `string` | no | `""` | **NEW.** Required when `status="archived"`. See validation rules below. |
| `archival_ref` | `int` | no | `0` | **NEW.** Related task ID for `deprecated` / `duplicate` reasons. |

**Validation:**
- When `status="archived"`: `archival_reason` is **required**. Omitting it raises `ToolError`.
- When `status` is any non-archived value: `archival_reason` must be empty. Setting it raises `ToolError`.
- `archival_reason` must be one of the 5 enum values.
- **`completed` via `move_task`** is gated: only valid when the task's current status is `"done"`. From any non-done status, `completed` is rejected with `ToolError`. This preserves the auditor-completion signal — `completed` from non-terminal statuses can only happen via `end_work` auto-archive.
- `archival_ref` is optional. When `archival_reason` is `deprecated` or `duplicate`, `archival_ref` should reference the superseding/target task ID. When set for other reasons, it is accepted but ignored.

**Guidance:** Forward-skip guidance still fires when jumping multiple columns.

---

## 3. Projection Schema Definitions

### TaskSummary

The lightweight projection returned by `list_tasks` and `create_tasks`.

```
TaskSummary {
  id:               int           // unique task ID
  title:            string        // task title
  status:           string        // current status or "archived"
  priority:         string        // priority enum value
  tags:             string[]      // tag list
  blocked:          bool          // is task blocked?
  block_reason:     string | null // reason if blocked
  claimed:          bool          // is task claimed?
  parent:           int | null    // parent task ID
  depends_on:       int[]         // dependency task IDs
  archival_reason:  string | null // NEW — null for non-archived; enum value for archived
  archival_ref:     int | null    // NEW — related task ID (for deprecated/duplicate); null otherwise
}
```

**Changes from current:** Added `archival_reason` and `archival_ref`. Remains body-free.

### TaskFull

The full projection returned by `show_task`, `create_task`, `edit_task`, `move_task`, `start_work`, `end_work`.

```
TaskFull {
  guidance:         string[]      // contextual messages (check immediately)
  id:               int
  title:            string
  status:           string        // includes "archived" as a value
  priority:         string
  created:          string        // ISO 8601 timestamp
  updated:          string        // ISO 8601 timestamp
  claimed:          bool
  tags:             string[]
  parent:           int | null
  depends_on:       int[]
  blocked:          bool
  block_reason:     string | null
  body:             string | null // full markdown body, section content, or null
  archival_reason:  string | null // NEW — same semantics as TaskSummary
  archival_ref:     int | null    // NEW — same semantics as TaskSummary
}
```

**Changes from current `KanbanTask`:**
- Added `archival_reason` and `archival_ref`.
- **Dropped `file`** — leaks storage structure. Callers identify tasks by `id`.
- `body` is `null` when `section` param is used and section not found.

### DispatchEntry

Each element in the `pick_tasks` dispatch array.

```
DispatchEntry {
  id:        int            // renamed from task_id — matches TaskSummary
  status:    string
  priority:  string        // NEW — enables assignment decisions
  title:     string        // NEW — enables assignment decisions
  tags:      string[]      // NEW — enables tag-based routing
}
```

**Change from current:** Widened from `{task_id, status}` to include `priority`, `title`, `tags`. Matches what `w-orchestration` already consumes.

### DispatchList

Returned by `pick_tasks`.

```
DispatchList {
  dispatch: DispatchEntry[]
}
```

### WorkSession

Returned by `list_sessions`.

```
WorkSession {
  task_id:     int
  state:       string        // "running" | "stuck" | "released" | "completed-pass" | "completed-fail" | "completed-rejected"
  agent:       string
  started_at:  string        // ISO 8601
  duration:    float | null  // seconds (null if open)
  outcome:     string | null
}
```

### SectionProjection

Not a distinct schema — the `section` param on `show_task` modifies the `body` field of `TaskFull`. Documented here for clarity:

- No `section` param: `body` = full markdown content
- `section` provided, match found: `body` = all matching `##` blocks (with headings)
- `section` provided, no match: `body` = `null`

### Section-as-Schema Decision

**Position: Expose section projection as a first-class `section` parameter on `show_task`.**

Rationale:
- Sections are the implicit schema of task bodies. Every pipeline agent writes to and reads from named `##` headings. The section names are documented in `agent-common.instructions.md`.
- The `section` param acknowledges this reality and gives callers a way to fetch only what they need.
- Full-body fetch remains the default (no `section` param). The new param is additive, not breaking.
- A separate `show_task_section` tool would add surface area without adding capability. One tool with an optional param is simpler.

Alternative rejected: **Structured `sections` field** (always return a parsed section map). This would require the MCP server to parse markdown headings on every call and return a larger JSON payload. The section param is cheaper and sufficient.

---

## 4. `archival_reason` and `archival_ref` Field Spec

### Enum Values

| Value | Meaning | Typical actor | `archival_ref` usage |
|-------|---------|--------------|---------------------|
| `completed` | Standard pipeline completion. Task reached terminal status and was archived by auditor. | auditor (via `end_work` auto-archive) | Not used (null) |
| `deprecated` | Superseded by a newer task. The original is no longer relevant. | orchestrator, planner | **Should** reference superseding task ID |
| `dropped` | Removed from plan. No longer wanted or needed. | orchestrator, user | Not used (null) |
| `duplicate` | Merged into another task. Work continues under the other ID. | planner | **Should** reference target task ID |
| `wontfix` | Decided against. Out of scope or rejected after evaluation. | orchestrator, user | Not used (null) |

### Where They Live

- **TaskSummary:** `archival_reason: string | null`, `archival_ref: int | null` — null for all non-archived tasks.
- **TaskFull:** Same fields, same semantics.
- **YAML header:** (Engine concern — Brief B. Not specified here.)

### `archival_ref` — Relational Link

`deprecated` and `duplicate` are inherently relational: they reference another task. `archival_ref` carries that machine-readable link. Without it, the archival reason says "superseded" but the caller must search the body or guess which task superseded it.

- `archival_ref` is **optional** on `move_task`. When `archival_reason` is `deprecated` or `duplicate`, callers **should** provide it, but omission is not an error (the link may not always be known).
- When `archival_reason` is `completed`, `dropped`, or `wontfix`, `archival_ref` is accepted but ignored (stored as null).
- `archival_ref` must reference an existing task ID. Invalid IDs raise `ToolError`.

### Defaults and Assignment

| Path | `archival_reason` value | `archival_ref` | How set |
|------|------------------------|----------------|---------|
| `end_work(outcome="success")` auto-archive | `"completed"` | `null` | Implicit — MCP server sets it automatically |
| `move_task(status="archived")` | Caller-provided | Caller-provided or null | Required param — `ToolError` if omitted |
| Non-archived tasks | `null` | `null` | Not applicable |

### Validation

- `archival_reason` must be one of the 5 enum values when provided.
- Cannot be set on a non-archived task (either via `move_task` or `edit_task`).
- Cannot be omitted when `move_task(status="archived")` is called.
- **`completed` gating via `move_task`:** `completed` is only valid when the task's current status is `"done"`. From any non-done status, `move_task(status="archived", archival_reason="completed")` raises `ToolError`. This preserves the auditor-completion signal: pipeline-completed tasks are only `completed` via `end_work` auto-archive (implicit) or manual archival of already-done tasks. Tasks killed mid-pipeline must use `deprecated`, `dropped`, `duplicate`, or `wontfix`.
- Immutable after archival: once set, the reason and ref cannot be changed via MCP. (Archived tasks are terminal — no edits.)

---

## 5. Archived Task `show_task` Contract

### Exact Return Shape

When `show_task(task_id="480")` is called and task 480 is archived:

```json
{
  "guidance": [],
  "id": 480,
  "title": "Implement retry logic",
  "status": "archived",
  "priority": "needed",
  "created": "2026-03-15T08:00:00+00:00",
  "updated": "2026-04-10T14:30:00+00:00",
  "claimed": false,
  "tags": ["phase-1"],
  "parent": null,
  "depends_on": [401, 402],
  "blocked": false,
  "block_reason": null,
  "body": "## Objective\n...\n## Audit\n...",
  "archival_reason": "completed",
  "archival_ref": null
}
```

### Status Field Behavior

- `status` is `"archived"` — a string value, not a column in the pipeline. It is the terminal state.
- `"archived"` is a valid value in `TaskSummary.status` and `TaskFull.status`.
- `"archived"` is NOT a valid target for `edit_task` or `start_work` — these tools reject archived tasks with `ToolError`.
- `"archived"` IS a valid value in `move_task(status="archived")` — this is the explicit archival path.

### What Doesn't Change

- The `body` field contains the full archived body (or section if `section` param is used).
- `depends_on` is preserved — the dependency graph survives archival.
- `tags`, `priority`, `parent` are preserved.
- `created` and `updated` are preserved. `updated` reflects the archival timestamp.
- `claimed` is always `false` for archived tasks (claims are released on archival).

### Error Case

- `show_task` for an ID that **never existed** raises `ToolError: "Task {id} not found"`.
- `show_task` for an archived ID returns normally (no error, no special parameter).

---

## 6. Critic Loop

### Cycle 1

**Critic confidence in position: 0.37 — Reject**

Challenges accepted and resolved:

| # | Challenge | Severity | Resolution |
|---|-----------|----------|------------|
| 1 | `sweep` leaks implementation/storage concerns into Brief A. Server already auto-runs sweep. Meanwhile `valid_transitions` was skipped despite M3 endorsement. | Critical | **Replaced `sweep` with `list_transitions`.** Sweep is an engine-internal concern; `list_transitions` serves a real agent need. |
| 2 | `ids` filter on `list_tasks` has muddled semantics — "magic" auto-include-archived while other filters still AND-combine, creating silent drops. | Moderate | **Simplified: `ids` enters ID-lookup mode.** When `ids` is set, all other filter params are ignored. Returns summaries for exactly those IDs (active + archived). Clean two-mode semantics instead of hybrid. |
| 3 | `section` param underspecified for repeated headings. `## Review Evidence` appears multiple times (review loops). First/last/all not specified. | Critical | **Specified: return ALL matching sections** in document order, preserving `##` delimiters. Guidance includes occurrence count. Addresses the reviewer's cycle-count use case. |
| 4 | `completed` via `move_task` is unrestricted — any caller can mark arbitrary archival as `completed`, erasing the auditor-completion signal. | Critical | **Gated `completed`:** via `move_task`, only valid when task is already in `"done"` status. Non-done tasks must use other reasons. Preserves auditor signal. |
| 5 | Batch-create stance contradicts itself: prompt says "no batch-internal deps" but spec allows position-based resolution. | Moderate | **Settled: no batch-internal deps.** `depends_on` references pre-existing IDs only. Planner creates roots first, then deps in a second call. Simple and coherent. |
| 6 | Coherence argument applied selectively: status overlap removed, but block overlap and `_work` naming kept without justification. | Moderate | **Added explicit justification.** Block overlap is contextual (lifecycle vs administrative, different preconditions) — not pure redundancy like the status overlap. `_work` suffix is intentional: signals lifecycle operations, not CRUD. |
| 7 | `pick_tasks` dispatch shape mismatch: returns `{task_id, status}` but orchestration skill consumes `id, status, priority, title, tags`. | Blind spot | **Widened dispatch projection** to include `priority`, `title`, `tags`. Eliminates N `show_task` follow-ups after dispatch. |
| 8 | `deprecated`/`duplicate` are relational reasons but carry no link to the related task. | Blind spot | **Added `archival_ref: int | null`** field to TaskSummary and TaskFull. Optional on `move_task`. Carries the machine-readable link that the reason implies. |

### Cycle 2

**Critic confidence in position: 0.41 — Reject**

Challenges and resolutions:

| # | Challenge | Severity | Resolution |
|---|-----------|----------|------------|
| 1 | `create_tasks` "2 calls replaces 20" claim doesn't survive multi-layer dep graphs. Planner decomposes into layered graphs; deeper than roots+1 breaks the claim. | Critical | **Fixed justification.** Honest framing: D calls (one per dependency layer) vs N individual calls. For typical 3-layer/20-task decomposition: 3 calls vs 20. Still order-of-magnitude reduction. Tool earns its slot. |
| 2 | `pick_tasks` field name mismatch: dispatch uses `task_id` but orchestration skill references `id`. Gap only partially resolved. | Critical | **Renamed `task_id` → `id`** in DispatchEntry to match TaskSummary and orchestration skill naming. |
| 3 | `ids` mode silently ignores other filters — creates hidden semantics. Caller can pass `ids` + `status` and not realize `status` was ignored. | Moderate | **Changed to error-on-conflict.** When `ids` is set, any non-default filter param raises `ToolError` with explicit message. No silent behavior. |
| 4 | Section selector doesn't model "latest" use case. Retry handling needs current (most recent) Review Evidence, not all occurrences. | Moderate | **Kept all-occurrences as V1 default.** Added V2 note for `section_index` param. Callers can split on `##` delimiters for first/last — trivial downstream. Not worth param complexity for V1. |
| 5 | `completed` gating from non-done status forces less truthful reason; immutability makes misclassification permanent. | Moderate | **Kept gating.** "Completed" means pipeline-complete. A task in "review" is NOT completed. The 2-call path (move to done, then archive as completed) is proper sequencing, not a dead-end. If the task IS done but stuck in review, it should be advanced first. Gating enforces semantic accuracy. |
| 6 | `archival_ref` only partially earns its cost because it's optional for the cases that need it most. | Moderate | **Kept optional.** The alternative (required for deprecated/duplicate) creates friction when the target ID isn't known yet. Optional field that can be populated > no field at all. Partial value is still value. |
| 7 | `list_transitions` is speculative — no concrete current workflow needs it. Current model is trivially any-to-any. | Moderate | **Dropped `list_transitions`.** YAGNI. Surface reduced to 10 tools. Added SKIP entry to change table. |
| 8 | 11-tool surface not justified — two additions have weak justification. | Moderate | **Reduced to 10 tools.** Every remaining tool has a concrete consumer and demonstrated value. |

**Blind spots acknowledged:**
- Silent omission of missing IDs in `ids` lookup: documented behavior. Callers compare returned vs requested IDs. Adding a `not_found` field would require changing return type from `TaskSummary[]` to a wrapper object — disproportionate for V1.
- "Latest section" use case: documented as V2 consideration. V1 returns all matches; client-side split is trivial.

---

## 7. Confidence

**Post-Cycle-2 confidence: 0.88**

The surface is tight: 10 tools (8 existing, 2 new), each with a concrete consumer. The two Critic cycles resolved all Critical-severity challenges and produced substantive improvements to `ids` semantics, section multi-occurrence handling, dispatch projection naming, batch-create justification, and `completed` gating.

Remaining minor uncertainties:
- Section V2 (`section_index`) may be needed sooner than expected if retry-handling volume grows.
- `archival_ref` adoption will depend on planner discipline — optional fields get skipped under pressure.
- `create_tasks` all-or-nothing atomicity is strict; may need partial-success mode for very large batches.
