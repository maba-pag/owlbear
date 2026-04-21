# Decisions — Brief A: MCP Tool Surface

All decisions made through walkthrough of synthesis with the Mediator. Engine-agnostic scope: Brief B will design engine API; Brief C will design storage.

## Archived-task read behavior

- **S1.** `show_task` on archived tasks returns a normal task object with `status: "archived"` and `archival_reason` populated. No special parameter, no header-only mode.
- **S2.** `archival_reason` enum: `completed | deprecated | dropped | duplicate | wontfix`. Validated at MCP surface; ToolError on invalid value.
- **S3.** `archival_refs: list[int]` (always a list).
  - `deprecated` / `duplicate` → non-empty required (ToolError if empty).
  - `completed` / `dropped` / `wontfix` → must be empty (ToolError if non-empty).
  - Each ID validated to exist at write time.
  - Self-reference forbidden. Cyclic archival chains forbidden. No transitive following promised by the contract — callers follow at most one hop unless they choose to walk further.
- **S4.** Setting `archival_reason = "completed"` (via `move_task` OR `edit_task`) requires the task is currently in `done` status. ToolError otherwise. Applies at every write site, not just `move_task`.
- **S5.** `archival_reason` required on every `move_task` archive op. No reason-less archival.
- **S12.** `end_work(outcome="success")` from `done` status auto-archives with `archival_reason="completed"`. No extra param.
- **R4.** `end_work(outcome="reject", move_to="archived", ...)` accepts `archival_reason` and `archival_refs`. Single atomic call replaces append + release + archive.
- **R5.** `edit_task` allows full edit access on archived tasks, **subject to S4** (cannot retro-claim `completed`). Other reason changes (e.g. `wontfix` → `dropped`, typo correction on `archival_refs`) are free.
- **C2 (legacy).** Out of scope for Brief A. Brief assumes all archived tasks have `archival_reason` populated; pre-contract migration is Brief C work.

## Read efficiency

- **S6.** `show_task` gains `section: str` (singular) param. When set, response `body` contains only matching heading content (case-insensitive, regardless of heading level). Missing → `body: null` plus `missing_sections: ["requested_name"]`. Multiple matches → all returned, with occurrence count in `guidance`.
- **S7.** `list_tasks` gains `ids: list[int]` param. Exclusive with all other filters (ToolError on combine). Returns summaries for requested IDs including archived. Missing IDs reported in `missing_ids: list[int]` field on the response (mirror of `missing_sections`).
- **S8.** **Dropped.** No `create_tasks` batch tool. Sequential `create_task` is already optimal for the planner's chain-shaped workload (caller knows each ID immediately and can wire `parent`/`depends_on` on the next call).
- **S9.** `pick_tasks` returns waves instead of a flat list:
  - Signature: `pick_tasks(wave_size: int | None = None, max_waves: int = 3)` (`None` falls back to the engine-configured default).
  - Returns `PickTasksResponse {waves: list[Wave], guidance: list[str]}` where `Wave = {index: int, tasks: list[DispatchEntry]}`.
  - `DispatchEntry` includes `agent: str` (engine-computed assignee).
  - Engine guarantees: no intra-wave dep edges; no empty waves; claimed tasks, archived tasks, `dep_status="blocked"` tasks, and `blocked==true` tasks excluded.

## Surface cleanup

- **S10.** Drop `file` field from all output projections. Prevents storage leak into caller code.
- **S11.** `edit_task` drops `status`, `depends_on`, `tags` (vestigial trap params). Use `move_task` for status; `add_dep`/`remove_dep` for deps; `add_tag`/`remove_tag` for tags.
- **F2.** Fold `block_task`, `unblock_task`, `release_task` into `edit_task` (block_reason set/clear) and `end_work` (`outcome="release"`). Reduces tool count to **8**.
- **`list_sessions` not added.** No unique MCP consumer need remains; orchestrator doesn't need it, and cockpit/session history is handled on the Brief B cockpit/admin surface rather than the MCP tool surface.
- **`claimed_by` field dropped** from all projections and from `start_work` (no name param, no name generation). Random-name generation is theater. `claimed_at: timestamp | null` is single source of truth; `claimed: bool` derives from `claimed_at is not None`.

## Validation

- **S14.** No-silent-ignore: ToolError on any inapplicable parameter combination. Examples: `archival_refs` on `completed` reason; `ids` combined with other filters on `list_tasks`; `body` + `append_body` together on `edit_task`.
- **F1.** Write-time existence validation for `depends_on`, `parent`, AND `archival_refs`. Dangling refs ToolError at write.

## Dependency semantics on archived deps (C3)

When task X has `depends_on: [Y]` and Y is archived:

| Y archived as | Effect on X |
|---|---|
| `completed` | satisfies the dep — X is dispatchable |
| `deprecated` | redirect — caller follows `Y.archival_refs` (the successor); X is dispatchable (`dep_status: redirect`); redirect-chain resolution is agent responsibility at pickup |
| `duplicate` | redirect — same rule as deprecated; targets are merge destinations; X is dispatchable |
| `dropped` | blocks — X stays un-dispatchable; `dep_status: blocked` |
| `wontfix` | blocks — X stays un-dispatchable; `dep_status: blocked` |

Projection: `TaskSummary` and `TaskFull` gain `dep_status: "ok" | "redirect" | "blocked" | null` (null when task has no `depends_on`). `pick_tasks` honors this when composing waves.

## Projection schemas

- **S13.** `archival_reason`, `archival_refs`, and `dep_status` appear on both `TaskSummary` and `TaskFull`. `null` / `[]` / `null` respectively when not applicable.
- **`claimed_at: timestamp | null`** appears explicitly on both `TaskSummary` and `TaskFull`. `claimed: bool` derives from `claimed_at is not None` (engine convenience field).
- **Naming.** `KanbanTask` renamed to `TaskFull`. Self-documenting pair with `TaskSummary`.

## Timestamps (wire format only)

- **B1.** Projection `created` / `updated` / `claimed_at` timestamps are ISO 8601 with explicit timezone offset (e.g. `2026-04-19T14:30:00-08:00` or `2026-04-19T22:30:00Z`). How the engine determines its offset is Brief B.
- **B2.** `edit_task(append_body=..., timestamp=true)` prepends the same ISO format with offset, matching B1.

## Other

- **F3.** Keep `guidance: list[str]` on every tool response. Active correction channel for agents.

## Final tool list (8)

1. `list_tasks` — extended (`ids` exclusive, drop `archived: bool`, archival fields + `dep_status` on output, `missing_ids` on response)
2. `show_task` — transparent archived reads + `section` param + `missing_sections` on response
3. `pick_tasks` — returns waves with computed `agent` field; honors `dep_status` when composing
4. `create_task` — caller no longer chooses status; engine uses the configured entry status; cross-ref validation strengthened (S3 + F1)
5. `edit_task` — drops trap params; absorbs block/unblock; archival metadata edits allowed on archived (subject to S4 gate at write site)
6. `move_task` — required `archival_reason`, validated `archival_refs`, `completed` gated to `done`
7. `start_work` — `claimed_by` dropped
8. `end_work` — auto-archive on success; reject path accepts archival params; absorbs `release_task` via `outcome="release"` (self-claim only)

## Out-of-scope (deferred)

- `list_sessions` — declined entirely; no MCP-caller consumer
- `release_task` — dropped from MCP; admin/force release is Brief B engine surface (Cockpit GUI consumer); claim staleness recovery is engine policy (Brief B)
- `create_tasks` batch tool — declined; sequential optimal for chain-shaped planner workload
- Multi-section projection (`sections: list[str]`) — V1 gap accepted
- Legacy archived task migration (no `archival_reason`) — Brief C
- Engine API design — Brief B
- Storage / persistence — Brief C
