# Kanban MCP Tool Surface v2 — Agent-Centric Redesign

## Summary

Brief A is a complete redesign of the kanban MCP tool surface — every tool re-shaped, three standalone tools folded into other operations, and `pick_tasks` substantially restructured. The redesign is motivated by archive-read pain (the original trigger) but the audit surfaced equally costly issues across the surface: N+1 read patterns, vestigial trap parameters, duplicated single-field tools, leaked storage details, missing structured fields for archival reason and dep status, ambiguous claim identity, and no batch-id lookup. The brief specifies only the contract that calling agents see and use; engine implementation is Brief B; persistence is Brief C.

## Problem Statement

The kanban MCP surface today predates several years of pipeline experience. The original 8-tool surface was shaped by an early-pipeline view where archival was rare, batch operations were unimagined, and parameter validation was lenient. Five classes of pain have accumulated:

1. **Archive blindness.** `show_task` errors on archived IDs. No structured `archival_reason` exists. Agents resolving deps or tracing history hit walls.
2. **N+1 reads.** Architects fetch full bodies per dep just to read one status field. Memory-curators and reviewers fetch full bodies to grep one section. Orchestrators re-derive wave composition every dispatch cycle.
3. **Trap parameters.** `edit_task` accepts `status`, `depends_on`, `tags` as no-op or sometimes-broken legacy params. `archived: bool` on `list_tasks` has ambiguous semantics.
4. **Duplicated single-field tools.** `block_task`, `unblock_task`, `release_task` each set or clear one field already covered by `edit_task` or `end_work`.
5. **Identity & leakage.** `claimed_by` random names produce no actionable identity but consume bytes. `file` field on every projection leaks storage layout into caller code.

## Outcomes

1. **The MCP surface optimizes for the calling agent's call-count and context budget.** Every common workflow — dependency resolution, history tracing, dispatch, claim/release, archive — fits in fewer tool calls than today, with smaller responses.
2. **Archived tasks are first-class.** Readable transparently, carrying structured reason and successor/target links.
3. **The surface is internally consistent.** No trap parameters, no duplicated tools, no silent-ignore behaviors, no leaked storage details, predictable validation rules across every tool.
4. **Engine and storage stay swappable.** Surface specifies wire shapes only; how the engine fulfills the contract is Brief B's freedom; how it persists is Brief C's.

## Scope

**In scope (Brief A):**

- Tool list: names, parameter shapes, validation rules, response envelopes
- Output projection schemas: `TaskSummary`, `TaskFull`, `Wave`, `DispatchEntry`
- Cross-cutting field contracts: `archival_reason` enum, `archival_refs`, `dep_status`, `claimed_at`, timestamp wire format
- Folding/dropping tools where semantics fully overlap with another tool
- No-silent-ignore policy across all tools

**Out of scope (Brief A) — explicitly delegated:**

- **Engine API design** → Brief B. How tools obtain data (engine method names, signatures, internal projections, batching/caching strategies, TZ resolution, wave-composition policy).
- **Storage / persistence** → Brief C. File layout, archive directory structure, indexes, migration of legacy archived tasks (including back-fill of `archival_reason`), DB vs files vs hybrid.
- **Cockpit GUI surface** → Brief B. Admin/force-release, stuck-session inspection, claim sweeping. These exist for human operators, not MCP-calling agents.
- **Backwards compatibility** → none. No legacy MCP clients to preserve.

**Constraint inherited by Brief B:** the engine API must be capable of fulfilling every contract in this brief.

**Constraint inherited by Brief C:** the storage layer must support the read/write semantics implied here, including write-time existence validation for `depends_on` / `parent` / `archival_refs` and migration of archives without `archival_reason` to a valid state before this surface goes live.

## Tool Surface — Final Spec

### 5.1 `list_tasks`

**Purpose:** List or look up tasks with filters.

**Signature:**

```text
list_tasks(
  status: str | None = None,               # accepts "archived" as a value
  priority: str | None = None,
  tag: str | None = None,
  archival_reason: str | None = None,
  ids: list[int] | None = None,
  unclaimed: bool = False,
  blocked: bool | None = None,
  parent: int | None = None,
  search: str | None = None,
  sort: str | None = None,
  reverse: bool = False,
  limit: int = 0
) -> ListTasksResponse
```

**Validation:**

- `ids` combined with any other filter param → `ToolError("ids is exclusive with other filters")`
- Invalid `status`, `priority`, or `archival_reason` enum value → `ToolError`

**Behavior:**

- Returns `{tasks: list[TaskSummary], missing_ids: list[int] | None, guidance: list[str]}`. `missing_ids` present only when `ids` was used.
- By default excludes archived tasks; pass `status="archived"` or use `ids` to surface them.

### 5.2 `show_task`

**Purpose:** Read a single task by ID, including archived. Optionally project a single body section.

**Signature:**

```text
show_task(
  id: int,
  section: str | None = None
) -> ShowTaskResponse
```

**Validation:**

- `id` not found → `ToolError("task {id} not found")`
- `section` set but param value is empty string → `ToolError`

**Behavior:**

- When `id` references an archived task, returns the full task object with `status: "archived"` and `archival_reason` / `archival_refs` populated. No special handling required by the caller.
- When `section` is set, returns body containing only matching heading content (case-insensitive AND whitespace-stripped match on both heading and parameter, regardless of heading level; all matches concatenated in document order). When the heading isn't found, `body: null` and the response includes `missing_sections: ["<section>"]`. When found multiple times, `guidance` includes occurrence count.
- When `section` is unset, returns full body.

### 5.3 `pick_tasks`

**Purpose:** Return the next dispatchable wave(s) of work. This is the dispatcher's primary tool — used by the orchestrator agent. The engine does not enforce caller identity; role isolation is documentary.

**Signature:**

```text
pick_tasks(
  wave_size: int | None = None,   # falls back to engine config default
  max_waves: int = 3
) -> PickTasksResponse
```

**Validation:**

- `wave_size < 1` or `max_waves < 1` → `ToolError`

**Behavior:**

- Returns `{waves: list[Wave], guidance: list[str]}` where `Wave = {index: int, tasks: list[DispatchEntry]}`.
- Engine guarantees: no two tasks within a wave have a `depends_on` edge between them; no empty waves; **claimed tasks excluded; archived tasks excluded; tasks blocked by `dep_status: "blocked"` excluded; tasks with `blocked == true` excluded** (per Brief B D58 — dispatcher will not hand out a task that `start_work` would reject).
- `DispatchEntry` includes computed `agent: str` (engine maps status→agent).

### 5.4 `create_task`

**Purpose:** Create a single task.

**Signature:**

```text
create_task(
  title: str,
  body: str = "",
  priority: str = "needed",
  tags: list[str] | None = None,
  parent: int | None = None,
  depends_on: list[int] | None = None
) -> SingleTaskResponse
```

**Validation:**

- `parent` references non-existent ID → `ToolError`
- Any element of `depends_on` references non-existent ID → `ToolError`
- Invalid `priority` enum value → `ToolError`

**Behavior:**

- Tasks are created at the engine-configured entry status (typically `"research"`); callers cannot choose status at creation. Status changes go through `move_task`.

### 5.5 `edit_task`

**Purpose:** Modify an existing task. Absorbs former `block_task` / `unblock_task`.

**Signature:**

```text
edit_task(
  id: int,
  body: str | None = None,
  append_body: str | None = None,
  timestamp: bool = False,
  priority: str | None = None,
  parent: int | None = None,
  add_dep: list[int] | None = None,
  remove_dep: list[int] | None = None,
  add_tag: list[str] | None = None,
  remove_tag: list[str] | None = None,
  block_reason: str | None = None,         # set non-empty to block; "" or null to unblock
  archival_reason: str | None = None,      # only on archived tasks
  archival_refs: list[int] | None = None   # only on archived tasks
) -> SingleTaskResponse
```

**Validation:**

- `body` and `append_body` both set → `ToolError`
- `add_dep` references non-existent ID → `ToolError`
- `archival_reason` or `archival_refs` set on a non-archived task → `ToolError`
- Setting `archival_reason="completed"` requires task is currently in `done` status → `ToolError` otherwise *(S4 gate at write site; effectively impossible for an archived task)*
- `archival_refs` rules per `archival_reason` enforced (see §7)
- No-op call (no field would change) → `ToolError`

### 5.6 `move_task`

**Purpose:** Change status (the only path to `archived`).

**Signature:**

```text
move_task(
  id: int,
  status: str,
  archival_reason: str | None = None,
  archival_refs: list[int] | None = None
) -> SingleTaskResponse
```

**Validation:**

- `status="archived"` without `archival_reason` → `ToolError`
- `archival_reason` set when `status != "archived"` → `ToolError`
- `archival_reason="completed"` requires current status is `done` *(S4 gate)*
- `archival_refs` rules per `archival_reason` (see §7)
- Invalid `status` enum value → `ToolError`. Any two valid statuses are a valid transition at the enum level; the engine does not reject on "unsupportedness." The destination status's write-time predicate (configured via `BoardConfig.status_predicates`) fires atomically — predicate failure → `ToolError` and no state change.

### 5.7 `start_work`

**Purpose:** Claim a task for work.

**Signature:**

```text
start_work(id: int) -> SingleTaskResponse
```

**Validation:**

- Task already claimed → `ToolError("already claimed at <claimed_at>")`
- Task is archived → `ToolError`
- Task is blocked → `ToolError`

**Behavior:**

- Sets `claimed_at` to current time. No claimant identity recorded.

### 5.8 `end_work`

**Purpose:** End an active work session, optionally moving or blocking the task. Absorbs former `release_task` for self-release.

**Signature:**

```text
end_work(
  id: int,
  outcome: str,                              # "success" | "reject" | "release" | "block"
  move_to: str | None = None,                # required for "reject"; optional for "block"; forbidden for "success"/"release"
  note: str | None = None,                   # appended to body if set (with timestamp prefix)
  archival_reason: str | None = None,        # required when reject + move_to="archived"; forbidden on success/release/block
  archival_refs: list[int] | None = None,    # paired with archival_reason
  block_reason: str | None = None            # required (non-empty) for "block"; forbidden on other outcomes
) -> SingleTaskResponse
```

**Validation:**

- Task is unclaimed and `outcome ∈ {"success", "reject", "block"}` → `ToolError`. (`outcome="release"` on an unclaimed task is idempotent — succeeds as a no-op.)
- `outcome="reject"` without `move_to` → `ToolError`
- `outcome="block"` without non-empty `block_reason` → `ToolError`
- `outcome ∈ {"success", "release", "reject"}` with `block_reason` set → `ToolError`
- `outcome ∈ {"success", "release", "block"}` with `archival_reason` or `archival_refs` set → `ToolError`
- `outcome="success"` with `move_to` set → `ToolError` (success follows the configured status sequence; callers cannot override)
- `outcome="release"` with `move_to` set → `ToolError`
- `move_to="archived"` (under `outcome="reject"`) without `archival_reason` → `ToolError`
- Invalid `outcome` enum value → `ToolError`

**Behavior:**

- `outcome="success"` from any non-archive status: auto-advances one step in the engine-configured status sequence; from the terminal status (`done`): auto-archives with `archival_reason="completed"` and `archival_refs=[]`. Each transition fires the destination status's write-time predicate; predicate failure leaves the task unchanged (atomic). Clears claim. Note appended if set.
- `outcome="reject"`: appends note (if set), moves status per `move_to` (any-to-any allowed), archives with provided reason if `move_to="archived"`. Clears claim. Predicate on destination fires atomically.
- `outcome="release"`: clears claim, no status change. Note appended if set when a claim is actually released; if already unclaimed, the call is a pure no-op.
- `outcome="block"`: sets `blocked=true` and `block_reason=<value>`. If `move_to` is set, also moves status (forward or backward; predicate fires atomically). Clears claim. Note appended if set. Engine response `guidance` includes a hint about creating an Action-Request or Decision-Request follow-up task

## Projection Schemas

```text
TaskSummary {
  id:               int
  title:            string
  status:           string            # includes "archived"
  priority:         string
  tags:             string[]
  parent:           int | null
  depends_on:       int[]
  blocked:          bool
  block_reason:     string | null
  claimed_at:       string | null     # ISO 8601 with offset; null when unclaimed
  claimed:          bool              # convenience: claimed_at is not null
  archival_reason:  string | null     # enum or null
  archival_refs:    int[]             # empty when not applicable
  dep_status:       string | null     # "ok" | "redirect" | "blocked" | null (no deps)
}

TaskFull extends TaskSummary {
  created:          string            # ISO 8601 with offset
  updated:          string            # ISO 8601 with offset
  body:             string | null     # null when section requested but not found
}

DispatchEntry {
  id:               int
  status:           string
  priority:         string
  title:            string
  tags:             string[]
  agent:            string            # engine-computed assignee (e.g. "builder")
}

Wave {
  index:            int               # 0-based ordinal within the response
  tasks:            DispatchEntry[]   # 1..wave_size
}
```

**Response envelopes:**

```text
ListTasksResponse  { tasks: TaskSummary[], missing_ids: int[] | null, guidance: string[] }
ShowTaskResponse   = TaskFull merged with { missing_sections: string[] | null, guidance: string[] }
PickTasksResponse  { waves: Wave[], guidance: string[] }
SingleTaskResponse = TaskFull merged with { guidance: string[] }   # create/edit/move/start/end
```

## Cross-Cutting Contracts

**`archival_reason` enum.** Five values: `completed | deprecated | dropped | duplicate | wontfix`. Validated at every MCP write site that accepts the field. Invalid value → `ToolError`. The value `completed` is the auditor-confidence signal: any write that sets `archival_reason="completed"` (whether via `move_task`, `edit_task`, or `end_work` auto-archive) requires the task is currently in `done` status.

**`archival_refs` rules.** Always a list of `int`. For `deprecated` / `duplicate` reasons: non-empty required. For `completed` / `dropped` / `wontfix`: must be empty. Each ID validated to exist at write time. Self-reference forbidden. Cyclic archival chains forbidden. The contract makes no promise about transitive following — a caller chasing a chain of `deprecated → deprecated → completed` walks each hop themselves.

**`dep_status` semantics.** When a task has at least one entry in `depends_on`, the engine computes `dep_status` based on the archival state of those dependencies:

- All deps active or `completed`-archived → `ok`
- Any dep archived as `deprecated` or `duplicate` → `redirect` (caller follows `archival_refs` on the archived dep)
- Any dep archived as `dropped` or `wontfix` → `blocked` (task is un-dispatchable)

When a task has no `depends_on` entries, `dep_status` is `null`. `pick_tasks` excludes tasks with `dep_status: "blocked"` from waves.

**Cross-reference validation.** Write-time existence checks apply to every reference field: `parent`, `depends_on` (all elements), `add_dep` (all elements), `archival_refs` (all elements). Dangling reference → `ToolError`.

**Timestamp wire format.** All timestamps in projections (`created`, `updated`, `claimed_at`) and in `edit_task(append_body=..., timestamp=true)` prepends are ISO 8601 with explicit timezone offset — `±HH:MM` or `Z`. How the engine determines its offset is Brief B.

**No-silent-ignore.** Every tool raises `ToolError` on any inapplicable parameter combination. There is no warning mode, no "best effort," no silent drop. A successful response means every input parameter was applied.

**`guidance` field.** Every response carries `guidance: string[]` — engine-generated hints, warnings, occurrence counts, or active-correction messages. This is the surface's primary channel for steering agents toward correct workflow.

**Cross-cutting contracts.** Every MCP-facing `ToolError` raised by these tools carries the human-readable `user_message` only. Canonical machine-readable error codes (e.g. `ERR_NOT_FOUND`, `ERR_INVALID_STATUS`, `ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_BLOCK_REASON_REQUIRED`, `ERR_PREDICATE_FAILED`) are owned by the engine contract in Brief B `decisions.md` (D57) and may be preserved in adapter logs, but they are not part of the MCP wire error shape.

## Acceptance Criteria

**Archive readability:**

- AC1. `show_task(<archived_id>)` returns `TaskFull` with `status="archived"`, valid `archival_reason`, valid `archival_refs`. No error.
- AC2. `list_tasks(status="archived")` returns archived tasks only.
- AC3. `list_tasks(ids=[<active>, <archived>, <missing>])` returns 2 tasks; `missing_ids=[<missing>]`.

**Reason field:**

- AC4. `move_task(id, "archived")` without `archival_reason` → `ToolError`.
- AC5. `move_task(id, "archived", "completed")` from a status other than `done` → `ToolError`.
- AC6. `edit_task(<archived>, archival_reason="completed")` always → `ToolError` (an archived task is not in `done`).
- AC7. `move_task(id, "archived", "deprecated")` with empty `archival_refs` → `ToolError`.
- AC8. `move_task(id, "archived", "dropped", archival_refs=[42])` → `ToolError`.
- AC9. Each tool that accepts `archival_reason` rejects values outside the 5-value enum.

**Section projection:**

- AC10. `show_task(id, section="audit")` returns body containing only `## Audit` content (case-insensitive).
- AC11. `show_task(id, section="missing")` returns `body=null` and `missing_sections=["missing"]`.
- AC12. Multiple `## Audit` blocks in the body are all returned, with `guidance` reporting occurrence count.
- AC13. `edit_task(id, status="todo")` → `ToolError`.
- AC14. `edit_task(id, body="...", append_body="...")` → `ToolError`.
- AC15. `list_tasks(ids=[1], status="todo")` → `ToolError`.
- AC16. No projection includes a `file` field.
- AC17. No projection includes `claimed_by`; `claimed_at` and derived `claimed` are the only claim-state outputs.

**Lifecycle:**

- AC18. `end_work(id, "success")` from any non-archive status auto-advances one step in the engine-configured status sequence; from the terminal status (`done`) auto-archives with `archival_reason="completed"` and `archival_refs=[]`. In all cases the claim is cleared. Each transition fires the destination's write-time predicate atomically (predicate failure → no state change at all).
- AC19. `end_work(id, "reject", move_to="archived", archival_reason="wontfix", note="...")` archives, appends note, clears claim, in one call.
- AC20. `end_work(id, "release")` clears the claim without status change; idempotent on already-unclaimed.
- AC-NEW-1. `end_work(id, "block", block_reason="<reason>")` sets `blocked=true`, `block_reason=<reason>`, clears the claim, leaves status unchanged. Optional `move_to` moves status (forward or backward) atomically.
- AC-NEW-2. `end_work(id, "block")` without non-empty `block_reason` → `ToolError`.
- AC-NEW-3. `end_work(id, "success" | "release" | "reject", block_reason="x")` → `ToolError`.
- AC-NEW-4. `end_work(id, "block", ...)` response `guidance` includes a hint about creating an Action-Request or Decision-Request follow-up task.

**Waves:**

- AC22. `pick_tasks()` returns ≤3 waves; no two tasks within the same wave have a dep edge between them; **no claimed tasks; no archived tasks; no `dep_status="blocked"` tasks; no `blocked==true` tasks**.
- AC23. Each `DispatchEntry` includes computed `agent`.

**Cross-ref validation:**

- AC24. `create_task(..., depends_on=[99999])` → `ToolError`.
- AC25. `edit_task(id, add_dep=[99999])` → `ToolError`.
- AC26. `move_task(id, "archived", "duplicate", archival_refs=[99999])` → `ToolError`.

**Dep semantics:**

- AC27. Task X with `depends_on=[Y]` where Y archived as `wontfix` → X has `dep_status="blocked"` and is excluded from `pick_tasks` waves.
- AC28. Task X with `depends_on=[Y]` where Y archived as `deprecated` → X has `dep_status="redirect"`; caller can follow `Y.archival_refs`.

**Timestamps:**

- AC29. `created`, `updated`, `claimed_at` all carry explicit `±HH:MM` or `Z` offset.
- AC30. `edit_task(append_body="...", timestamp=true)` prepends ISO timestamp with offset.

## Out of Scope / Follow-ups

**Deferred to Brief B (engine surface):**

- Engine API: method names, signatures, internal projections, batching, caching
- Wave-composition policy (which agents pair, fairness, priority weighting)
- Status→agent mapping that produces `DispatchEntry.agent`
- Timezone offset resolution (system tz, config, etc.)
- Cockpit GUI surface including admin force-release and stuck-session inspection
- Claim staleness recovery (timeouts, sweeps)

**Deferred to Brief C (storage):**

- File layout, archive directory structure, indexes
- Migration of legacy archived tasks to populate `archival_reason` and `archival_refs`
- Storage backend choice (files / DB / hybrid)

**Declined entirely:**

- `list_sessions` MCP tool — no MCP-caller need
- `release_task` MCP tool — admin release belongs in GUI (Brief B)
- `create_tasks` batch tool — sequential `create_task` is optimal for chain-shaped planner workload
- Plural `sections: list[str]` — V1 gap accepted
- `claimed_by` random-name generation — theater, no consumer

**Open follow-up tasks (post Brief A):**

- Re-evaluate plural `sections` if multi-section reads prove painful in practice
- Consider `last_section_match` projection if memory-curator's pattern dominates context budget

## Open Questions

None at brief approval. All Critic-surfaced critical issues addressed. Three were resolved in the walkthrough (S4 gate at write sites, legacy null deferred to Brief C, dep-status semantics specified). One was resolved by re-scoping (`release_task` dropped from MCP, GUI handles admin release).

## Handoff Notes

**For Brief B (engine surface):**

- Engine must expose enough to fulfill every tool contract in §5 with a single round trip per tool call (no internal N+1).
- Engine must compute `dep_status` per §7 semantics; consumed by both `list_tasks` and `pick_tasks`.
- Engine wave-composition must respect: no intra-wave dep edges, no empty waves, and exclusion of claimed tasks, archived tasks, `dep_status="blocked"` tasks, and `blocked==true` tasks. Default `wave_size` is config-sourced.
- Engine TZ resolution policy defines what `+HH:MM` value appears in projections — must be consistent within a single call.
- Cockpit GUI design picks up `list_sessions`-equivalent and admin release.

**For Brief C (storage):**

- Storage must enforce or support write-time existence checks for `parent`, `depends_on`, `archival_refs`.
- Migration plan must populate `archival_reason` (and `archival_refs` where applicable) on every existing archived task before this surface ships. A bulk default to `completed` is acceptable for tasks that reached archival via the standard pipeline path; everything else needs human triage.
- Section-as-schema (the heading-based extraction in `show_task(section=...)`) is implemented against body text — storage does not need a separate sections index unless performance demands it.
