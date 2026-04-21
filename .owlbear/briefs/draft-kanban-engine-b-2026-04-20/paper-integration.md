# Paper Integration — Brief A → Brief B

This document maps every Brief A surface element (tool, parameter, validation rule, projection, cross-cutting contract, AC) to the Brief B engine API element that fulfills it. Argument-level mapping. Each cell answers: **what engine call(s), with what arguments, validates/returns/raises what.**

References:
- Brief A: `.owlbear/briefs/kanban-mcp-surface-v2/brief.md` (post-revision per Brief B "Brief A Revision List" in `decisions.md`)
- Brief B decisions: `decisions.md` in this directory (D1–D65)

Conventions:
- `Engine.method(...)` is a method on `KanbanEngine` (full surface).
- `AgentView.method(...)`, `CockpitView.method(...)` are role-view facades per D9 (D59 retired — `pick_tasks` lives on `AgentView`; role isolation is documentary).
- All engine writes raise `KanbanError` subclasses (D27, D48, D57). MCP adapter maps `code` to `ToolError(user_message)`. Cockpit adapter maps subclass to HTTP status.
- All MCP tools dispatched via `AgentView` per D9 (including `pick_tasks`).
- Brief A revisions tracked in `decisions.md` "Brief A Revision List" — paper-integration here reflects the **post-revision** Brief A.

Scope notes:
- Round-trip behavior of body string (byte-exact vs normalized) is **Brief C's contract**, not Brief B's (D40). Brief B specifies only that `create_task`/`edit_task` accept `body: str` (markdown) and that engine parses internally for predicate evaluation and section projection.
- Storage-layer behavior is **Brief C's** entirely. Brief B contract is the engine surface.

---

## §1 — Tool Mapping (Brief A §5 → Engine API)

### 1.1 `list_tasks`

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `list_tasks(status, priority, tag, archival_reason, ids, unclaimed, blocked, parent, search, sort, reverse, limit) → ListTasksResponse` | `AgentView.list_tasks(status: str \| None, priority: str \| None, tag: str \| None, archival_reason: str \| None, ids: list[int] \| None, unclaimed: bool, blocked: bool \| None, parent: int \| None, search: str \| None, sort: str \| None, reverse: bool, limit: int) → ListTasksResponse` | 1:1 signature passthrough. Adapter is mechanical (O6). Same signature on `CockpitView`. |
| **Validation:** `ids` exclusive with other filters | If `ids is not None` and any of {status, priority, tag, archival_reason, unclaimed, blocked, parent, search} is non-default → `ValidationError(code="ERR_IDS_EXCLUSIVE")` | Per D57. |
| **Validation:** invalid `status` enum | `ValidationError(code="ERR_INVALID_STATUS")` if `status` not in `BoardConfig.statuses ∪ {"archived"}` | Per D57. |
| **Validation:** invalid `priority` enum | `ValidationError(code="ERR_INVALID_PRIORITY")` | Per D57. |
| **Validation:** invalid `archival_reason` enum | `ValidationError(code="ERR_ARCHIVAL_REASON_INVALID")` | Per D37 + D57. |
| **Default:** excludes archived unless `status="archived"` or `ids` used | Engine default in query construction | |
| **Return:** `ListTasksResponse {tasks: list[TaskSummary], missing_ids: list[int] \| None, guidance: list[str]}` | Engine returns the envelope. `missing_ids` populated only when `ids is not None`. `guidance` per D39 (envelope-only). | |
| **`dep_status` on each TaskSummary** | Engine computes per D38 (pure function, every read) per task during projection | Per §3.3. |

### 1.2 `show_task`

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `show_task(id, section) → ShowTaskResponse` | `AgentView.show_task(id: int, section: str \| None = None) → ShowTaskResponse` | Same on `CockpitView`. The gate where `archival_reason="completed"` requires current status `done` (informally "the completed-requires-done gate") is enforced by `move_task` and `edit_task`, not `show_task`. |
| **Validation:** `id` not found | `NotFoundError(code="ERR_NOT_FOUND", user_message="task {id} not found")` | Per D27 + D57. |
| **Validation:** `section` empty string | `ValidationError(code="ERR_SECTION_EMPTY")` | Per D57. |
| **Behavior:** archived tasks readable | Engine read path treats archived identically to active; no special branch | `Task.status == "archived"`. |
| **Behavior:** `section` filter | Per D56: matches by `Section.heading` (case-insensitive, whitespace-stripped), regardless of `Section.level`. All matches concatenated in document order. Engine parses body to `list[Section]` per D26+D40, filters, serializes matching sections back to markdown for `body: str` per D30 wire shape. | If no match: `body=None`, `missing_sections=[section]`. Brief A §5.2 wording revised to drop "##" literal per Brief A Revision List #7. |
| **Behavior:** multiple matches | Engine emits guidance string e.g. `"section '{name}' matched {n} times"` when n > 1. Per D39+D54-style. | |
| **Return:** `ShowTaskResponse = TaskFull ⊕ {missing_sections: list[str] \| None, guidance: list[str]}` | Engine returns the envelope | `body: str \| None` per D30. |

### 1.3 `pick_tasks` (orchestrator-intended; `AgentView`)

**Algorithm (4-step pipeline; the consolidated form of D42 + D58 + D60 + D62 + D63):**

1. **Filter** — read all tasks; exclude any of: `claimed_at != null`, status `"archived"`, `dep_status == "blocked"`, `blocked == true` (D42 + D58).
2. **Sort** the filtered list by `(priority_rank ASC, age DESC, id ASC)` per D60. `priority_rank` is the index in `BoardConfig.priorities` (0 = highest). `age` is `now - created`. This produces a deterministic input order; it is **not** the output shape.
3. **Greedy wave assembly** in sort order. For each task `t` (with bucket `b = BoardConfig.agent_types[BoardConfig.agent_map[t.status]]`):
   - Try each existing wave in order; place `t` in the lowest-index wave that satisfies ALL three constraints:
     - `len(wave) < wave_size` (size).
     - No task in `wave` has a dep edge to `t` in either direction (intra-wave dep-disjointness).
     - For every task `t'` already in `wave` with bucket `b'`: `b in agent_compatibility[b']` (per D63 — the relation is init-validated symmetric, so checking one direction suffices).
   - If no existing wave fits and `len(waves) < max_waves`: create a new wave containing `t`.
   - Otherwise: drop `t` from this cycle (it will be picked up on the next call).
4. **Return** `PickTasksResponse{waves: list[Wave], guidance: list[str]}` where `Wave = {index: int, tasks: list[DispatchEntry]}` and `DispatchEntry` carries the computed `agent` from `BoardConfig.agent_map[task.status]`.
**Output cardinality:** `len(waves) ≤ max_waves` (default 3); `len(wave.tasks) ≤ wave_size` (default 4). One call returns one cycle; the orchestrator agent calls `pick_tasks` again to start the next cycle.

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `pick_tasks(wave_size, max_waves) → PickTasksResponse` | `AgentView.pick_tasks(wave_size: int \| None = None, max_waves: int = 3) → PickTasksResponse` | Per D42: dispatcher capability lives on the agent surface. Role isolation (orchestrator-only-in-practice) is documented in the tool docstring and the orchestrator skill, not type-enforced. Not on `CockpitView`. |
| **Validation:** `wave_size < 1` or `max_waves < 1` | `ValidationError(code="ERR_INVALID_WAVE_PARAM")` | Per D57. |
| **Default `wave_size`** | Falls back to `BoardConfig.wave_size` (new field per D42, default 4) | Pydantic-validated. |
| **Behavior:** filter + sort + assemble + return | Per the 4-step algorithm above. | Locks D42 (composition), D58 (dispatchability filter), D60 (sort), D62 (agent buckets), D63 (compatibility matrix). Default wave-assembly behaviour codifies `share/skills/w-orchestration/SKILL.md` "Wave Assembly" section. |
| **Return:** `PickTasksResponse {waves: list[Wave], guidance: list[str]}` where `Wave = {index: int, tasks: list[DispatchEntry]}` | Engine returns envelope | `DispatchEntry` per §2.3. |

### 1.4 `create_task` (post-Brief A revision per D50)

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature (post-revision)** `create_task(title, body, priority, tags, parent, depends_on) → SingleTaskResponse` | `AgentView.create_task(title: str, body: str = "", priority: str = "needed", tags: list[str] \| None = None, parent: int \| None = None, depends_on: list[int] \| None = None) → SingleTaskResponse` | **No `status` parameter** per D50. Tasks created at `BoardConfig.entry_status` (new field, default `"research"`). Brief A Revision List #2. **Not exposed on `CockpitView`** — task creation is an agent action via MCP only. |
| **Validation:** `parent` non-existent | `ValidationError(code="ERR_PARENT_NOT_FOUND")` | Per §3.4 + D57. |
| **Validation:** any `depends_on` element non-existent | `ValidationError(code="ERR_DEP_NOT_FOUND", detail="missing: {ids}")` | Per §3.4. |
| **Validation:** invalid `priority` enum | `ValidationError(code="ERR_INVALID_PRIORITY")` | Per BoardConfig enum check. |
| **Validation:** body size | UTF-8 byte length of `body: str` parameter. > 500 KB → `ValidationError(code="ERR_BODY_TOO_LARGE")` per D35+D47. > 100 KB → succeeds; response `guidance` includes warning per D35. | D47 measurement basis. |
| **Behavior:** predicate on entry status | If `BoardConfig.status_predicates[entry_status]` exists, engine evaluates against parsed body per D15. Failure → `ValidationError(code="ERR_PREDICATE_FAILED", detail="<predicate name>")`. Task is not created. | The "predicate on create" question (Finding 8) was resolved by D50 (drop `status` param); the entry-status predicate fires here as the natural consequence. |
| **Config validation (engine init):** `BoardConfig.entry_status` must reference a declared status | If `entry_status not in BoardConfig.statuses` → `ConfigError(code="ERR_ENTRY_STATUS_INVALID")` raised by `KanbanEngine.__init__` per D50+D57. Default value `"research"`. | Resolves Critic Finding 5. |
| **Behavior:** atomic ID allocation | Engine guarantees unique monotonic `id` under concurrent creation per D13 | Brief C implements the locking primitive. |
| **Behavior:** `created` and `updated` set to current ISO 8601 with offset | Per D14 | UTC, ISO 8601 with `+00:00` or `Z`. |
| **Return:** `SingleTaskResponse = TaskFull ⊕ {guidance: list[str]}` | Engine returns envelope | |

### 1.5 `edit_task`

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `edit_task(id, body, append_body, timestamp, priority, parent, add_dep, remove_dep, add_tag, remove_tag, block_reason, archival_reason, archival_refs) → SingleTaskResponse` | `AgentView.edit_task(id: int, body: str \| None = None, append_body: str \| None = None, timestamp: bool = False, priority: str \| None = None, parent: int \| None = None, add_dep: list[int] \| None = None, remove_dep: list[int] \| None = None, add_tag: list[str] \| None = None, remove_tag: list[str] \| None = None, block_reason: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None) → SingleTaskResponse` | **No OCC `expected_updated` parameter on AgentView** per D46. **CockpitView signature additionally requires `expected_updated: str`** per D22+D46. `block_reason` parameter retained per D53. |
| **Validation:** `id` not found | `NotFoundError(code="ERR_NOT_FOUND", user_message="task {id} not found")` | Per D57. |
| **Validation:** `parent` set to non-existent ID | `ValidationError(code="ERR_PARENT_NOT_FOUND")` per §3.4 + D57 | |
| **Validation:** `body` AND `append_body` both set | `ValidationError(code="ERR_BODY_EXCLUSIVE")` | AC14. Per D57. |
| **Validation:** `add_dep` non-existent | `ValidationError(code="ERR_DEP_NOT_FOUND")` | AC25. |
| **Validation:** `archival_reason` / `archival_refs` on non-archived task | `ValidationError(code="ERR_ARCHIVAL_FIELDS_FORBIDDEN")` per D37+D57 | |
| **Validation:** `archival_reason="completed"` (target task is archived → not in terminal) | `ValidationError(code="ERR_COMPLETED_REQUIRES_DONE")` per D37 + D65 (`BoardConfig.terminal_status`) | AC6. The completed-requires-terminal gate. |
| **Validation:** `archival_refs` rules per `archival_reason` (D37 matrix) | Codes per §3.2: `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_ARCHIVAL_REF_MISSING`, `ERR_ARCHIVAL_REF_SELF`, `ERR_ARCHIVAL_REF_CYCLE` | |
| **Validation:** invalid `archival_reason` enum | `ValidationError(code="ERR_ARCHIVAL_REASON_INVALID")` | Per D37. |
| **Validation:** invalid `priority` enum | `ValidationError(code="ERR_INVALID_PRIORITY")` | |
| **Validation:** no-op call (no field would change) | `ValidationError(code="ERR_NO_OP")` raised by engine after computing the diff | Per Brief A §5.5 + D57. |
| **Validation:** body size (per D47) | If `body=` provided: UTF-8 byte length checked against 100 KB warn / 500 KB error. **For `append_body=`: post-append total body byte length checked against same caps.** Fail → `ValidationError(code="ERR_BODY_TOO_LARGE")`. | Resolves Critic Finding 10 ambiguity by extending D47 measurement to post-append result. |
| **Validation (CockpitView only):** OCC | Engine routes the write through `storage.write_task_if_unchanged(task, expected_updated, kanban_dir)` (Brief C §3.2 + AC-C4a). The storage primitive holds a per-task `flock`, re-reads, compares, and either writes atomically or raises `ConcurrencyError(code="ERR_STALE")` per D22+D23+D46. AgentView has no token check and uses plain `write_task` (last-writer-wins by design). |
| **Behavior:** `block_reason` non-empty sets blocked; empty/null clears block | Engine maps semantics: non-empty sets `blocked=true` + `block_reason`; empty/null clears both | Replaces former `block_task`/`unblock_task`. Per D53 retained for state-assertion use. |
| **Behavior:** `append_body` with `timestamp=true` prepends ISO 8601 with offset | Engine prepends per D20 + D14 | AC30. |
| **Behavior:** `updated` advanced to current time on any successful change | Per D14 | Required for D23/D46 OCC tokens (Cockpit). |

### 1.6 `move_task`

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `move_task(id, status, archival_reason, archival_refs) → SingleTaskResponse` | `AgentView.move_task(id: int, status: str, archival_reason: str \| None = None, archival_refs: list[int] \| None = None) → SingleTaskResponse` | **CockpitView signature additionally requires `expected_updated: str`** per D22+D46. AgentView has no token. |
| **Validation:** `id` not found | `NotFoundError(code="ERR_NOT_FOUND")` | Per D57. |
| **Validation:** `status="archived"` requires `archival_reason` | `ValidationError(code="ERR_ARCHIVAL_REASON_REQUIRED")` per D37 | AC4. |
| **Validation:** `archival_reason` set when `status != "archived"` | `ValidationError(code="ERR_ARCHIVAL_FIELDS_FORBIDDEN")` per D37 | |
| **Validation:** `archival_reason="completed"` requires current status = `BoardConfig.terminal_status` | `ValidationError(code="ERR_COMPLETED_REQUIRES_DONE")` per D37 + D65 (configurable terminal_status) | AC5 (the completed-requires-terminal gate). |
| **Validation:** `archival_refs` rules | Per D37 matrix (same set as `edit_task`) | AC7, AC8, AC26. |
| **Validation:** invalid `status` enum | `ValidationError(code="ERR_INVALID_STATUS")` | Per D49: there is **no `ERR_TRANSITION_FORBIDDEN`** code; "unsupported transition" wording in Brief A §5.6 re-reads as "invalid status enum." Brief A Revision List #3. |
| **Validation:** invalid `archival_reason` enum | `ValidationError(code="ERR_ARCHIVAL_REASON_INVALID")` | |
| **Validation (CockpitView only):** OCC | Engine routes the write through `storage.write_task_if_unchanged` (same primitive as `edit_task`); `ConcurrencyError(code="ERR_STALE")` on mismatch | |
| **Behavior:** D15 write-time predicate on destination `status` | If `BoardConfig.status_predicates[status]` exists, engine parses body and evaluates the predicate. Failure → `ValidationError(code="ERR_PREDICATE_FAILED", detail=<predicate name>)`. Transition does NOT occur (D41 atomicity). | Per D15 + D49. |
| **Behavior:** archive operation clears claim atomically | Per D17. If `status="archived"` and task was claimed: claim cleared as part of the move. On transition failure (predicate or archival validation), claim NOT cleared (D41 atomicity). | |
| **Behavior:** skip-transition guidance | Per D54: if transition skips more than one position in `BoardConfig.statuses` order, response `guidance` includes a soft warning. | Doesn't block. |
| **Behavior:** `updated` advanced | Per D14. | |

### 1.7 `start_work`

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature** `start_work(id) → SingleTaskResponse` | `AgentView.start_work(id: int) → SingleTaskResponse` | **Not on `CockpitView`** (no human "claims" via Cockpit). No identity per D11. No OCC token per D46. |
| **Validation:** `id` not found | `NotFoundError(code="ERR_NOT_FOUND")` | Per D57. |
| **Validation:** task already claimed | `ConcurrencyError(code="ERR_ALREADY_CLAIMED", detail="claimed_at={ts}")` | If `claimed_at is not None` and `claimed_at + claim_timeout > now`. If claim is expired, lazy-release first per D18+D36 by routing the release through `storage.write_task_if_unchanged(cleared_task, expected_updated=current.updated, ...)`; on `ERR_STALE` (another writer beat us to it), re-read and re-evaluate from the top; otherwise proceed to claim via the same CAS primitive. |
| **Validation:** task is archived | `ValidationError(code="ERR_ARCHIVED_NOT_CLAIMABLE")` | |
| **Validation:** task is blocked (`blocked==true`) | `ValidationError(code="ERR_BLOCKED_NOT_CLAIMABLE")` | |
| **Behavior:** sets `claimed_at = now()` | Per D11. No `claimed_by`. | |
| **Behavior:** `updated` advanced | Per D14. | |

### 1.8 `end_work` (post-Brief A revision per D52)

| Brief A surface | Engine API | Notes |
|---|---|---|
| **Signature (post-revision)** `end_work(id, outcome, move_to, note, block_reason, archival_reason, archival_refs) → SingleTaskResponse` | `AgentView.end_work(id: int, outcome: str, move_to: str \| None = None, note: str \| None = None, block_reason: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None) → SingleTaskResponse` | **Adds `block_reason` parameter** per D52. **Not on `CockpitView`** (no human end-work via Cockpit; admin release uses `release_task`). No agent-side OCC token per D46: by harness invariant, the orchestrator does not re-dispatch a task while the original worker can still later emit `end_work`. Brief A Revision List #4. |
| **Validation:** `id` not found | `NotFoundError(code="ERR_NOT_FOUND")` | Per D57. |
| **Validation:** outcome enum (4 values per D52) | `outcome not in {"success", "reject", "release", "block"}` → `ValidationError(code="ERR_INVALID_OUTCOME")` per D52+D57 | |
| **Validation:** ~~`outcome="success"` from non-`done` status → ToolError~~ | **Removed per D52.** `success` is now valid from any non-archive status (auto-advances one step). Brief A Revision List #5; AC18 wording revised. | |
| **Forbidden-parameter matrix** (deterministic; no silent ignore per D27+D51) | See table below this row. | Resolves Critic Findings 1, 2. |
| **Validation:** `outcome="reject"` with `move_to="archived"` and missing `archival_reason` | `ValidationError(code="ERR_ARCHIVAL_REASON_REQUIRED")` per D37+D51 | |
| **Validation:** `outcome="reject"` with `move_to="archived"` and `archival_refs` rules | Full D37 matrix per §3.2 | |
| **Validation:** `end_work` on unclaimed task | If `outcome=="release"`: succeeds idempotently (pure no-op — `updated` NOT advanced, `note` NOT appended; nothing written) per D55. If `outcome in {"success", "reject", "block"}`: `ValidationError(code="ERR_NOT_CLAIMED")` per D55+D57. | Resolves Critic Finding 12. |
| **Behavior `outcome="success"`:** any-status auto-advance | Per D52: status advances one step in `BoardConfig.statuses` order. From last non-archive status: auto-archives `completed`/`[]` (engine-set per D51). Predicate on destination per D15+D41 atomicity. Clears claim. | Brief A Revision List #5. |
| **Behavior `outcome="reject"`:** appends note (if set), moves to `move_to`, archives if `move_to="archived"` (caller supplies reason/refs), clears claim | Per D41 atomicity: predicate on `move_to` evaluates; on failure entire call fails (claim NOT cleared, note NOT appended). | AC19. |
| **Behavior `outcome="release"`:** clears claim, no status change, note appended if set | No predicate (no transition). Pure no-op (no writes) when task is already unclaimed per D55. | AC20. |
| **Behavior `outcome="block"`:** sets `blocked=true`, `block_reason=<value>`, optional `move_to` (per D52 may move forward or backward), clears claim, note appended if set | If `move_to` is set, predicate on destination per D15+D41 atomicity. If predicate fails: entire call fails (claim NOT cleared, note NOT appended, blocked flag NOT set, `block_reason` NOT set). Engine emits guidance per D54 suggesting Action-Request / Decision-Request creation. | Brief A Revision List #6. |
| **Behavior:** note prepended with ISO 8601 timestamp on append | Per D20 / AC30 | |
| **Behavior:** `updated` advanced on any successful call | Per D14 | |

**Forbidden-parameter matrix for `end_work`** (every cell is deterministic; engine raises the listed code, never silently drops):

| `outcome` ↓ / parameter → | `move_to` | `archival_reason` | `archival_refs` | `block_reason` |
|---|---|---|---|---|
| `success` | `ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS` (engine drives the transition per D52) | `ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS` (engine sets `completed`/`[]` on terminal-step archive per D51) | `ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS` per D51 | `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK` per D52+D57 |
| `reject` | **required**; absent → `ERR_REJECT_REQUIRES_MOVE_TO` per D52+D57 | allowed only when `move_to=="archived"` per D37; otherwise → `ERR_ARCHIVAL_FIELDS_FORBIDDEN` per D37+D51 | same rule as `archival_reason` (allowed only when `move_to=="archived"`); D37 matrix applies | `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK` per D52+D57 |
| `release` | `ERR_MOVE_TO_FORBIDDEN_ON_RELEASE` per D52+D57 (release does not transition) | `ERR_ARCHIVAL_FIELDS_FORBIDDEN` per D51 | `ERR_ARCHIVAL_FIELDS_FORBIDDEN` per D51 | `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK` per D52+D57 |
| `block` | **allowed (optional)** per D52; if present, predicate fires on destination per D15+D41 atomicity | `ERR_ARCHIVAL_FIELDS_FORBIDDEN` per D51 | `ERR_ARCHIVAL_FIELDS_FORBIDDEN` per D51 | **required**; absent or empty → `ERR_BLOCK_REASON_REQUIRED` per D52+D57 |

Notes: engine validates the matrix **before** any state mutation; partial application is impossible per D41. When multiple parameter-level errors apply to a single call, engine raises the leftmost-row, leftmost-column violation (deterministic ordering for tests).

---

## §2 — Brief A §6 Projection Schemas → Brief B Models

### 2.1 `TaskSummary`

| Brief A field | Type | Brief B source | Notes |
|---|---|---|---|
| `id` | int | `Task.id` | Atomic per D13. |
| `title` | str | `Task.title` | No size cap (D47). |
| `status` | str | `Task.status`; includes literal `"archived"` | |
| `priority` | str | `Task.priority` | From `BoardConfig.priorities` enum. |
| `tags` | list[str] | `Task.tags` | No size cap (D47). |
| `parent` | int \| None | `Task.parent` | |
| `depends_on` | list[int] | `Task.depends_on` | |
| `blocked` | bool | `Task.blocked` | Maintained by `edit_task(block_reason=...)` and `end_work(outcome="block")`. |
| `block_reason` | str \| None | `Task.block_reason` | |
| `claimed_at` | str \| None | `Task.claimed_at` (ISO 8601 with offset) | Per D11+D14. |
| `claimed` | bool | Computed: `Task.claimed_at is not None` | Convenience field, computed by engine projection. |
| `archival_reason` | str \| None | `Task.archival_reason` | Enum per D37 / §3.1. |
| `archival_refs` | list[int] | `Task.archival_refs` (empty list when N/A) | Per D37 / §3.2. |
| `dep_status` | str \| None | Computed per D38 every read | Pure function of dep states. |

### 2.2 `TaskFull`

Extends `TaskSummary` with:

| Brief A field | Type | Brief B source | Notes |
|---|---|---|---|
| `created` | str | `Task.created` (ISO 8601 with offset) | Per D14. |
| `updated` | str | `Task.updated` (ISO 8601 with offset) | Per D14. OCC token per D23/D46 (Cockpit only). |
| `body` | str \| None | Engine serializes `list[Section]` to markdown per D30 wire shape. `None` only when `section=...` was requested and not found. | Internal model is `list[Section]` (D7+D26); wire is `str` (D30). Round-trip behavior is Brief C's contract (D40). |

### 2.3 `DispatchEntry`

| Brief A field | Type | Brief B source | Notes |
|---|---|---|---|
| `id` | int | `Task.id` | |
| `status` | str | `Task.status` | |
| `priority` | str | `Task.priority` | |
| `title` | str | `Task.title` | |
| `tags` | list[str] | `Task.tags` | |
| `agent` | str | `BoardConfig.agent_map[Task.status]` per D24 | Fail-fast at config load if a status is missing from `agent_map` per D24. |

### 2.4 `Wave`

| Brief A field | Type | Brief B source | Notes |
|---|---|---|---|
| `index` | int | Engine assigns 0-based ordinal during cycle assembly | Per D42. |
| `tasks` | list[DispatchEntry] | Engine assembles per D42 | Size 1..wave_size. |

### 2.5 Response Envelopes

| Brief A envelope | Brief B engine return | Notes |
|---|---|---|
| `ListTasksResponse {tasks, missing_ids, guidance}` | Engine returns directly. `guidance` per D39. `missing_ids` only when `ids` arg used. | |
| `ShowTaskResponse = TaskFull ⊕ {missing_sections, guidance}` | Engine merges. `missing_sections` only when `section` arg used. | |
| `PickTasksResponse {waves, guidance}` | Engine returns. `guidance` per D39. | |
| `SingleTaskResponse = TaskFull ⊕ {guidance}` | Engine returns. Used by create_task / edit_task / move_task / start_work / end_work. | |

---

## §3 — Brief A §7 Cross-Cutting Contracts → Brief B

### 3.1 `archival_reason` enum (5 values)

`BoardConfig.archival_reasons = {"completed", "deprecated", "dropped", "duplicate", "wontfix"}` (frozen literal). Validated at every write site that accepts the field per D37: `move_task`, `edit_task`, `end_work` (when archiving via reject path; engine-set on success path per D51). Invalid → `ValidationError(code="ERR_ARCHIVAL_REASON_INVALID")`.

The completed-requires-terminal gate (`archival_reason="completed"` requires current status equal to `BoardConfig.terminal_status`): engine checks current status before allowing the field to be set or changed to `"completed"`. Failure → `ValidationError(code="ERR_COMPLETED_REQUIRES_DONE")`. The terminal status name is configurable via **D65**: `BoardConfig.terminal_status: str = "done"`, validated at init to be in `statuses` and to equal `statuses[-1]` (init-time `ConfigError(ERR_TERMINAL_STATUS_INVALID)` else); this is what makes the gate well-defined for any board configuration.

### 3.2 `archival_refs` rules

Per D37, engine validates at every write that sets/mutates `archival_refs`:

| Rule | Failure code |
|---|---|
| `deprecated` / `duplicate` require non-empty `archival_refs` | `ERR_ARCHIVAL_REFS_REQUIRED` |
| `completed` / `dropped` / `wontfix` require empty `archival_refs` | `ERR_ARCHIVAL_REFS_FORBIDDEN` |
| Each `archival_refs` ID must exist | `ERR_ARCHIVAL_REF_MISSING` |
| `task.id ∉ archival_refs` (no self-ref) | `ERR_ARCHIVAL_REF_SELF` |
| No archival cycle (transitive `archival_refs` does not form a cycle) | `ERR_ARCHIVAL_REF_CYCLE` |

Engine does NOT promise transitive following — caller walks each hop.

### 3.3 `dep_status` semantics

Per D38, engine computes per task per read (pure function):

| Condition | `dep_status` |
|---|---|
| `Task.depends_on == []` | `None` |
| All deps active OR archived as `completed` | `"ok"` |
| Any dep archived as `deprecated` or `duplicate` | `"redirect"` |
| Any dep archived as `dropped` or `wontfix` | `"blocked"` |

Order of precedence when a task has multiple archived deps: `blocked` > `redirect` > `ok` (worst wins).

`pick_tasks` excludes tasks with `dep_status == "blocked"` per D42, and tasks with `blocked == true` per D58.

### 3.4 Cross-reference validation (write-time existence)

Engine validates at every write that sets/mutates a reference field:

| Field | Failure code |
|---|---|
| `parent` | `ERR_PARENT_NOT_FOUND` |
| `depends_on` (any element) | `ERR_DEP_NOT_FOUND` |
| `add_dep` (any element) | `ERR_DEP_NOT_FOUND` |
| `archival_refs` (any element) | `ERR_ARCHIVAL_REF_MISSING` |

All raised as `ValidationError`.

### 3.5 Timestamp wire format

Per D14: UTC, ISO 8601 with explicit offset (`+00:00` or `Z`). Engine produces via `datetime.now(tz=UTC).isoformat()`. All projection timestamp fields (`created`, `updated`, `claimed_at`) and the `edit_task(append_body=..., timestamp=true)` prepend follow this format. Per D20: legacy `[[YYYY-MM-DD]]` historical entries in body text are not rewritten.

### 3.6 No-silent-ignore

Per D27+D57: every engine validation failure raises a `KanbanError` subclass with a `code` and `user_message`. Adapter (MCP or Cockpit) maps to surface error. There is no "best effort," no warning mode, no silent drop.

**Engine-init failure modes** (raised by `KanbanEngine.__init__`, not request-time):

- `ConfigError(code="ERR_ENTRY_STATUS_INVALID")` — `BoardConfig.entry_status` not in `BoardConfig.statuses` (D50).
- `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")` — malformed `claim_timeout` string (D29).
- `ConfigError(code="ERR_TERMINAL_STATUS_INVALID")` — `BoardConfig.terminal_status` not in `statuses` or not the final element (D65).
- `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` — active task files still carry `claimed_by` frontmatter; user must run `uv run kanban-migrate` (Brief C C11/AM-12, AC-C47). Surfaced from Brief C as an engine-init gate; included here so Brief B's error catalogue is complete.

### 3.7 `guidance` field

Per D39: engine emits guidance on response envelopes only. Never on `Task` model. Never persisted. Sources include:
- `show_task` section occurrence count (multi-match)
- `create_task`/`edit_task` body size warning (>100 KB)
- `pick_tasks` dispatch hints
- `move_task` / `end_work(reject, move_to=...)` skip-transition warning per D54
- `end_work(outcome="block")` Action-Request / Decision-Request suggestion per D54

### 3.8 Board-level activity stream

Board-level activity is first-class admin data, not diagnostic logging. Brief B requires a single gitignored `.owlbear/kanban/activity.jsonl` runtime file, persisted by Brief C, with structured JSONL activity events for every mutating engine operation.

- `CockpitView.list_activity(...)` exposes filtered raw events for cockpit/admin use.
- `CockpitView.list_sessions(filter=...)` is a derived read model over the same event stream.
- Agent-facing MCP surfaces do not expose raw activity.
- **`ActivityEvent.source`** is populated by the engine based on which role view (or auto-operation) performed the mutation: `"agent"` (AgentView, including `pick_tasks` — the dispatcher mutation surface is part of AgentView post D59-revised), `"cockpit"` (CockpitView), `"engine"` (auto-archive, sweep, repair). The enum has three values; `"orchestrator"` is retired together with `OrchestratorView`. No caller identity (`claimed_by` or similar) is recorded — consistent with D11. The `actor` field has been removed; `source` is the single identity field.

### 3.9 Archived-task rollout precondition

Brief A's archived-task guarantees (AC1–AC3 and the archived portions of the projection contract) are enabled only after Brief C has metadata-normalised existing archive files so contractual archive fields are present and valid on every archived task:

- `archival_reason` must be populated.
- `archival_refs` must be present and valid for the populated reason.

This is a rollout gate, not a full archive rewrite. Brief C need only backfill contract-critical archive metadata; archive body text and legacy vendor fields do not need canonical normalisation. Automatic `completed` defaults are allowed only where archive provenance is explicit and deterministic; ambiguous archives require triage before the redesigned surface is enabled.

---

## §4 — Acceptance Criteria → Brief B Engine Behavior

(AC21 removed per D4 / Brief A Revision List #1.)

| AC | Test | Engine API element |
|---|---|---|
| AC1 | `show_task(<archived_id>)` returns `TaskFull` with archived fields populated | `Engine.show_task` reads archived identically; projection includes `archival_reason`, `archival_refs` |
| AC2 | `list_tasks(status="archived")` returns archived only | `Engine.list_tasks` query branch on `status=="archived"` |
| AC3 | `list_tasks(ids=[active, archived, missing])` returns 2 + `missing_ids=[missing]` | `Engine.list_tasks` honors `ids` (includes archived), populates `missing_ids` |
| AC4 | `move_task(id, "archived")` without `archival_reason` → ToolError | `ValidationError(ERR_ARCHIVAL_REASON_REQUIRED)` per D37 |
| AC5 | `move_task(id, "archived", "completed")` from non-`done` → ToolError | `ValidationError(ERR_COMPLETED_REQUIRES_DONE)` per D37 |
| AC6 | `edit_task(<archived>, archival_reason="completed")` → ToolError | `ValidationError(ERR_COMPLETED_REQUIRES_DONE)` (archived ≠ done) per D37 |
| AC7 | `move_task(id, "archived", "deprecated")` empty refs → ToolError | `ValidationError(ERR_ARCHIVAL_REFS_REQUIRED)` per D37 |
| AC8 | `move_task(id, "archived", "dropped", refs=[42])` → ToolError | `ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN)` per D37 |
| AC9 | Invalid `archival_reason` enum → ToolError on every write site | `ValidationError(ERR_ARCHIVAL_REASON_INVALID)` per D37 + D57 |
| AC10 | `show_task(id, section="audit")` returns body containing matching heading content (case-insensitive) | `Engine.show_task` filters parsed `list[Section]` by case-insensitive heading match per D56 |
| AC11 | `show_task(id, section="missing")` → `body=null`, `missing_sections=["missing"]` | Engine behavior per D56 |
| AC12 | Multiple matches → `guidance` includes occurrence count | Engine emits guidance per D39+D54 |
| AC13 | `edit_task(id, status="todo")` → ToolError | **Adapter-layer rejection at BOTH consumer boundaries (MCP and Cockpit).** The engine `edit_task` signature does not accept `status`. The MCP tool's Pydantic schema rejects the call before the engine sees it; the Cockpit `/edit` request-body schema applies the symmetric rejection (per brief §4.2 #1). **Brief B engine API has no responsibility for AC13** — this is a Brief A surface contract enforced at both adapters. Documented here for completeness; not a Brief B engine element. |
| AC14 | `edit_task(id, body, append_body)` both set → ToolError | `ValidationError(ERR_BODY_EXCLUSIVE)` per D57 |
| AC15 | `list_tasks(ids=[1], status="todo")` → ToolError | `ValidationError(ERR_IDS_EXCLUSIVE)` per D57 |
| AC16 | No projection includes `file` field | `TaskSummary` / `TaskFull` Pydantic models do not declare `file` |
| AC17 | No `claimed_by` field; `claimed_at`+`claimed` present | Per D11. Models declare `claimed_at`, `claimed` (computed), no `claimed_by` |
| AC18 (revised per D52) | `end_work(id, "success")` from any non-archive status auto-advances one step; from `done` archives `completed`/`[]`; clears claim. Each transition fires destination predicate per D15+D41. | `Engine.end_work(outcome="success")` per D52+D51+D41 |
| AC19 | `end_work(id, "reject", move_to="archived", reason, note)` archives + appends + clears in one call | `Engine.end_work(outcome="reject")` per D52; full D37 archival validation matrix |
| AC20 | `end_work(id, "release")` clears claim, no status change | `Engine.end_work(outcome="release")` per D52; idempotent on unclaimed per D55 |
| ~~AC21~~ | ~~Non-claimant `end_work` → ToolError~~ | **Removed per D4 (D11 invariant).** Brief A Revision List #1. |
| AC22 | `pick_tasks()` returns ≤3 waves; no intra-wave dep edges; no claimed; no archived; no `dep_status="blocked"`; no `blocked==true` (per D58) | `AgentView.pick_tasks` per D42+D58 |
| AC23 | Each `DispatchEntry` includes computed `agent` | Engine sets per `BoardConfig.agent_map` per D24 |
| AC24 | `create_task(..., depends_on=[99999])` → ToolError | `ValidationError(ERR_DEP_NOT_FOUND)` per §3.4 |
| AC25 | `edit_task(id, add_dep=[99999])` → ToolError | `ValidationError(ERR_DEP_NOT_FOUND)` per §3.4 |
| AC26 | `move_task(..., archival_refs=[99999])` → ToolError | `ValidationError(ERR_ARCHIVAL_REF_MISSING)` per D37 |
| AC27 | Task X with dep on `wontfix`-archived Y → `dep_status="blocked"`, excluded from `pick_tasks` | Per D38 + D42 dispatcher filter |
| AC28 | Task X with dep on `deprecated`-archived Y → `dep_status="redirect"` | Per D38 |
| AC29 | `created`, `updated`, `claimed_at` carry explicit `±HH:MM` or `Z` | Per D14 |
| AC30 | `edit_task(append_body=..., timestamp=true)` prepends ISO timestamp with offset | Per D20+D14 |

**New ACs introduced by Brief B** (with AC-NEW-1..4 mirrored into Brief A §8 per Brief A Revision List #9):

| AC (proposed) | Test | Engine API element |
|---|---|---|
| AC-NEW-1 | `end_work(id, "block")` without `block_reason` → ToolError | `ValidationError(ERR_BLOCK_REASON_REQUIRED)` per D52 |
| AC-NEW-2 | `end_work(id, "block", block_reason="<r>")` sets `blocked=true`, `block_reason=<r>`, clears claim | Per D52 |
| AC-NEW-3 | `end_work(id, "block", block_reason="<r>", move_to="<s>")` additionally moves status to `<s>` (predicate fires per D15+D41) | Per D52 |
| AC-NEW-4 | `end_work(id, "block", ...)` response `guidance` includes Action-Request / Decision-Request suggestion | Per D54 |
| AC-NEW-5 | `move_task` or `end_work(reject, move_to=...)` skipping >1 status position emits skip-warning in `guidance` | Per D54 |
| AC-NEW-6 | `end_work(id, "<invalid>")` → ToolError | `ValidationError(ERR_INVALID_OUTCOME)` per D52 |
| AC-NEW-7 | `end_work(id, "release")` on unclaimed task succeeds as pure no-op: `updated` NOT advanced, `note` NOT appended, task file not touched | Per D55 |
| AC-NEW-8 | `end_work(id, "success"/"reject"/"block")` on unclaimed task → ToolError | `ValidationError(ERR_NOT_CLAIMED)` per D55 |
| AC-NEW-9 | `end_work(id, "success", archival_reason="completed")` (or `archival_refs=`, or `block_reason=`, or `move_to=`) → ToolError | `ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS)` / `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK` / `ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS` per D51+D52+D57; deterministic precedence per §1.8 forbidden-parameter matrix |
| AC-NEW-10 | `end_work(id, "reject")` without `move_to` → ToolError | `ValidationError(ERR_REJECT_REQUIRES_MOVE_TO)` per D52+D57 |
| AC-NEW-11 | `end_work(id, "reject"/"release"/"success", block_reason="x")` → ToolError | `ValidationError(ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK)` per D52+D57 |
| AC-NEW-12 | `end_work(id, "success")` from non-terminal status with predicate that fails on next status → ToolError; claim NOT cleared, status NOT advanced (atomic per D41) | `ValidationError(ERR_PREDICATE_FAILED)` per D15+D41 |
| AC-NEW-13 | `end_work(id, "block", block_reason="x", move_to="y")` where predicate on `y` fails → ToolError; claim NOT cleared, `blocked` NOT set, `block_reason` NOT set, status unchanged (atomic per D41) | `ValidationError(ERR_PREDICATE_FAILED)` per D15+D41+D52 |
| AC-NEW-14 | Engine init with `BoardConfig.entry_status` not in `BoardConfig.statuses` → ConfigError | `ConfigError(ERR_ENTRY_STATUS_INVALID)` per D50+D57 |
| AC-NEW-15 | `edit_task(id, parent=99999)` → ToolError | `ValidationError(ERR_PARENT_NOT_FOUND)` per §3.4+D57 |
| AC-NEW-16 | `edit_task` / `move_task` / `start_work` / `end_work` / `release_task` on missing `id` → ToolError | `NotFoundError(ERR_NOT_FOUND)` per D57; one AC parameterised across the five write sites |
| AC-NEW-17 | `end_work(id, "reject", move_to="archived")` without `archival_reason` → ToolError | `ValidationError(ERR_ARCHIVAL_REASON_REQUIRED)` per D37+D51 |
| AC-NEW-18 | `end_work(id, "release", move_to="<s>")` → ToolError | `ValidationError(ERR_MOVE_TO_FORBIDDEN_ON_RELEASE)` per D52+D57 |
| AC-NEW-19 | `end_work(id, "release", archival_reason=...)` or `archival_refs=...` → ToolError | `ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)` per D51 |
| AC-NEW-20 | `end_work(id, "block", block_reason="x", archival_reason=...)` or `archival_refs=...` → ToolError | `ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)` per D51 |
| AC-NEW-21 | `release_task(<unclaimed_id>)` succeeds idempotently (no-op for claim, `updated` NOT advanced when state unchanged); response is `SingleTaskResponse` | Per D55-style idempotency extended to admin-release; engine returns current `TaskFull` |
| AC-NEW-22 | `sweep()` returns list of released task IDs (may be empty); idempotent (second call with no expired claims returns `[]`) | Per D18+D36 compare-and-clear semantics |
| AC-NEW-23 | Engine init with `BoardConfig.terminal_status` not in `statuses`, OR not equal to `statuses[-1]` → ConfigError | `ConfigError(ERR_TERMINAL_STATUS_INVALID)` per D65+D57 |
| AC-NEW-24 | `POST /api/tasks/{id}/edit` with `status` in request body → HTTP 422 at the Cockpit boundary (request never reaches the engine) | Cockpit Pydantic request schema mirrors the engine view: no `status` field accepted. Symmetric to AC13 on the MCP side. |

---

## §5 — Cockpit Engine Surface (per D9, D21, D43)

Cockpit consumes `CockpitView` exclusively (per D9). Mutation routes rewire (per D21). `CockpitView` exposes:

| `CockpitView` method | Purpose | Notes |
|---|---|---|
| `list_tasks(...)` | Read board, identical signature to AgentView | No OCC; reads do not mutate `updated`. |
| `show_task(id, section=...)` | Read single task | No OCC. |
| `list_activity(...)` | Filtered raw activity events for cockpit/admin history views | Reads the board-level `activity.jsonl` stream defined in §3.8. Supports cockpit/admin filtering by task_id, action, source, and time window; not exposed on AgentView. `ActivityEvent.source` values: `"agent"` (AgentView mutations, including dispatcher `pick_tasks`), `"cockpit"` (CockpitView mutations), `"engine"` (auto-operations: auto-archive on `end_work(success)` from terminal status, sweep claim releases, repair AR creation). Engine populates `source` automatically based on the role view or internal operation; no caller parameter needed. |
| `list_sessions(filter="active")` | Derived work-session view for cockpit/admin use | Returns `list[SessionRecord]`. Derived from the board-level activity stream by pairing `start_work` events with their corresponding close events per task_id. `SessionRecord` fields: `task_id`, `task_status_at_start` (from event detail), `state` (`"running"` / `"stuck"` / `"completed"` / `"blocked"` / `"rejected"` / `"released"` / `"expired"`), `started_at`, `ended_at` (None while still claimed), `outcome` (`"success"` / `"block"` / `"reject"` / `"release"` / `"expired"` / None), `duration_s` (None when active). Filter values per D31: `"active"` (`state in {"running", "stuck"}`), `"all"`, `"blocked-or-rejected"`, `"released"`. `state` is for cockpit/history classification and does not replace task-level claimed state. |
| `edit_task(..., expected_updated: str)` | OCC required per D22+D46; `expected_updated` mandatory; routed through `storage.write_task_if_unchanged` (Brief C §3.2) | Mismatch → `ConcurrencyError(ERR_STALE)`. Cross-process safe via per-task flock. |
| `move_task(..., expected_updated: str)` | OCC required per D22+D46; routed through `storage.write_task_if_unchanged` | Same. |
| `release_task(id)` | Admin force-release (Cockpit-only) | Clears `claimed_at` unconditionally on a claimed task. **Idempotent on already-unclaimed:** succeeds as no-op, `updated` NOT advanced (state unchanged per D14 contract). Missing `id` → `NotFoundError(ERR_NOT_FOUND)` per D57. No OCC (admin override). Returns `SingleTaskResponse` (current `TaskFull` post-release). Per Brief A "Declined entirely": `release_task` is dropped from MCP but kept in GUI; this is the Brief B engine method that backs the GUI. |
| `sweep()` | Force claim sweep only; releases all claims where `claimed_at + claim_timeout <= now()` per D18+D36. | Returns `list[int]` of released task IDs (empty list if no expired claims). Idempotent. Per-task release routes through `storage.write_task_if_unchanged` (compare-and-clear is implemented as the CAS primitive's compare-step). On `ERR_STALE` for any task, that task is skipped this cycle (a concurrent writer already touched it). `updated` advanced on each released task per D14. Cockpit calls on init per D18. No quarantine, no AR creation, no corruption repair. |
| `scan_corruption()` | Read-only corruption scan for cockpit/admin health surfaces. | Calls `storage.detect_corruption(path, config)` for every file in `tasks/` and `archive/`; aggregates and returns `list[CorruptionError]`. Makes **no writes**. Polling cadence, presentation, and operator affordances are product concerns outside Brief B. |
| `repair_storage()` | User-triggered two-phase repair. **Phase 1:** calls `storage.scan_and_fix(kanban_dir, config)` (detection + auto-fix + quarantine, no AR creation). **Phase 2:** for each `action="quarantined"` outcome, calls the underlying engine `create_task` path to create the Action Request. Returns merged `list[RepairOutcome]`. | Never called implicitly at startup. The two-phase split is required: `storage.scan_and_fix` cannot import engine (circular); AR creation is always an engine responsibility. |
| `compact_activity()` | User-triggered activity-stream compaction. Calls `storage.compact_activity_log(kanban_dir)` and returns the resulting `ActivityCompactionResult`. | Cockpit/backend method available for later operator surfaces or direct invocation. Engine *also* runs opportunistic compaction at `__init__` when `activity.jsonl` exceeds 1 MB (best-effort, failures logged not raised). |

The maintenance rows above are part of the served cockpit backend/API interface for Brief B implementation. Approval of Brief B means engine capability plus cockpit backend/API exposure are in scope now. It does **not**, by itself, commit cockpit UI/product decisions such as polling cadence, confirmations, layouts, or operator affordances; those stay with task 1042 or a later cockpit brief.

Two role views (per D9): **`AgentView`**, **`CockpitView`**. (`OrchestratorView` retired per D59-revised — `pick_tasks` lives on `AgentView`; D61 vacated.)

**Method exposure summary:**

| Method | AgentView | CockpitView |
|---|---|---|
| `list_tasks` | ✓ | ✓ |
| `show_task` | ✓ | ✓ |
| `list_activity` | — | ✓ |
| `list_sessions` | — | ✓ |
| `pick_tasks` | ✓ | — |
| `create_task` | ✓ | — |
| `edit_task` | ✓ (no OCC) | ✓ (OCC required) |
| `move_task` | ✓ (no OCC) | ✓ (OCC required) |
| `start_work` | ✓ | — |
| `end_work` | ✓ | — |
| `release_task` | — | ✓ |
| `sweep` | — | ✓ |
| `scan_corruption` | — | ✓ |
| `repair_storage` | — | ✓ |
| `compact_activity` | — | ✓ |

---

## §6 — Decisions Not Surfaced in Brief A (Brief B-internal)

These decisions affect engine API but have no Brief A counterpart; collected here for completeness:

- **D11** — no claim identity. Affects `start_work` / `end_work` validation; surfaces as AC21 removal.
- **D13** — locking. Atomic ID allocation + OCC on edit. Affects `create_task`, `edit_task`, `move_task`.
- **D15** (reversed) + **D49** — write-time predicates on transitions; any-to-any transitions allowed.
- **D17** — archive atomicity. Engine invariant: archival clears claim atomically.
- **D18** — sweep on init. Cockpit-side fix; engine offers `sweep()`.
- **D19** — duplicate frontmatter IDs. Engine raises `CorruptionError` at read time.
- **D24** — agent_map fail-fast. Engine `__init__` validates `BoardConfig.agent_map` covers `BoardConfig.statuses`.
- **D29** — claim_timeout format. Pydantic validator on `BoardConfig.claim_timeout` accepts `Ns/Nm/Nh/Nd`.
- **D33** — no `agent_name` on constructor. `KanbanEngine.__init__` signature change.
- **D36** — sweep compare-and-clear. Engine invariant on claim-only `sweep()`; corruption repair lives on `repair_storage()`.
- **D43** — board-level activity stream. Engine/admin writes and reads `activity.jsonl` as first-class runtime history.
- **D44** — no AST scanner. Role views are documentation/labeling only.
- **D50** — `BoardConfig.entry_status` (new field).
- **D52** + **D53** + **D54** — `end_work` 4-outcome enum; `edit_task(block_reason=...)` retained; engine guidance on block + skip-transition.
- **D55** — `end_work(release)` idempotent on unclaimed.
- **D65** — terminal-status configurability: `BoardConfig.terminal_status: str = "done"`, init-validated to be in `statuses` and equal `statuses[-1]`. Engine `__init__` raises `ConfigError(ERR_TERMINAL_STATUS_INVALID)` else. Anchors the completed-requires-terminal gate (§2/§3, AC5/AC6) and disambiguates D52's `success` semantics on the terminal status.

---

## §7 — Brief C Handoff Notes

The paper-integration locks every Brief B engine surface contract. The following items pass to Brief C planning as natural extensions — not as Brief B open items:

1. **Predicate DSL extensions.** D64 locks the Brief B subset (`required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag` + `non_impl_tags`). Brief C planning may add operators (regex matchers, frontmatter requirements, etc.) as discrete decomposition tasks.
2. **Storage primitives.** Atomic ID allocation (D13), file or DB locking, frontmatter format, body markdown round-trip (D40) are entirely Brief C scope.
3. **Performance characteristics.** Bulk index/snapshot strategies for `list_tasks` and `pick_tasks` (per O1) are Brief C scope.
4. **Migration of existing task files.** Format changes (e.g., dropping `claimed_by` per D11; switching to UTC per D14 if not already there) are Brief C scope and may require a one-shot migration script.
