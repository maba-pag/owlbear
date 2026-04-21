# Brief B — Kanban Engine API + MCP Adapter Mapping + Cockpit Engine Surface

**Status:** Draft (M5 — pending Critic + user approval)
**Tier:** Studio
**Aperture:** Wide (no backwards compat; quality > everything)
**Predecessor:** Brief A (`kanban-mcp-surface-v2`) — MCP tool surface contract
**Successor:** Brief C — Storage layer (out of scope here)

---

## §1 — Problem & Outcome

**Problem.** The kanban engine, MCP server, and Cockpit backend currently share business logic across three layers without a single contract. The MCP server contains validation that should live in the engine; the Cockpit backend bypasses the engine for some writes and contains its own optimistic-concurrency logic; `pick_tasks` is flat and human-orchestrator-driven; claim identity is theatrical (`claimed_by` exists but is not enforced); status transitions and quality gates are scattered between dispatch-time and write-time. Any change ripples through three codebases.

**Outcome.** Brief B locks the **engine API** as the implementation of the lifecycle that **MCP** and **Cockpit** require. The MCP tool surface (Brief A) and the Cockpit GUI's read/admin/write paths are the consumers; the engine delivers the methods, validation rules, and response envelopes those consumers need. Storage is held opaque (Brief C). After Brief B, every Brief A acceptance criterion is fulfilled either by a documented engine call sequence (the engine-owned ACs) or by an explicit adapter-layer contract (currently one: AC13 — see §5); every reality conflict between prior decisions and current code has a recorded disposition; and the engine surface is ready for Brief C to implement underneath without further negotiation.

---

## §2 — Scope

### In scope (Brief B owns)
1. **Engine API contract.** Public method signatures, parameter semantics, validation rules, response envelopes, error taxonomy.
2. **Role views.** `AgentEngineView`, `CockpitEngineView` — type-level capability subsets of `KanbanEngine` (D9; D59 retired in M5 cleanup, see decisions).
3. **Projection schemas.** `TaskSummary`, `TaskFull`, `DispatchEntry`, `Wave`, response envelopes — engine-side definitions.
4. **Structured task-body contract.** Brief B intentionally changes the engine's internal body model to `list[Section]`; parser/render behavior and predicate migration are first-class scope, not incidental storage cleanup.
5. **Cross-cutting contracts.** `dep_status` semantics; `archival_reason` + `archival_refs` rules; cross-reference validation; timestamp wire format; no-silent-ignore principle; `guidance` envelope field.
6. **MCP adapter mapping.** For each Brief A tool, the engine call(s) and view that fulfill it. Adapter is mechanical translator.
7. **Cockpit engine and backend/API surface.** Methods exposed via `CockpitEngineView` and the cockpit backend/API contract that serves them. Includes `release_task`, claim-only `sweep`, read-only `scan_corruption`, user-triggered two-phase `repair_storage`, and OCC-required mutations. Brief B owns the service-side interface end to end: engine capability, cockpit adapter/backend rewiring, and backend exposure of the locked admin/history methods. The cockpit *product/UI* decisions for how these capabilities are consumed (polling cadence, repair confirmations, history layouts, operator affordances) remain **out of scope** and live in a separate ideation task (§7).
8. **Brief A revisions.** Surface contract issues found during paper integration are recorded as edits to Brief A (11 items, see §8).
9. **Reality-conflict dispositions.** Every conflict between prior decision and current code has a recorded outcome with rationale (decisions D11–D48 trace the M3/M4 dispositions). Code citations were collected during M3 (`landscape.md`) and inform but are not duplicated into individual decision entries.

### Out of scope (other briefs)
- **Storage layer** — files vs DB, locking primitives, JSONL activity log, frontmatter rules. Brief C.
- **Cockpit GUI** — React components, layouts, interaction patterns. Separate brief.
- **MCP wire transport** — JSON-RPC framing, transport selection. Locked by MCP standard.
- **Body markdown round-trip semantics** — byte-exact vs normalized. Brief C (D40).
- **Orchestrator agent logic** — Brief B locks the engine surface (`pick_tasks`); how the orchestrator agent uses it is the orchestrator's concern.

### Aperture
**Wide.** No backwards compatibility with current MCP wire shape; no preservation of legacy claim identity; no tolerance for "best-effort" behaviors. Every contract is hard-edged. Where Brief A is wrong, Brief A changes (11 revisions in §8). Where current code is wrong, current code changes.

---

## §3 — Engine Surface (authoritative summary)

### 3.1 Public types

- **`KanbanEngine`** — full surface. Constructor: `KanbanEngine(kanban_dir: Path, board_config: BoardConfig | None = None)`. Single board per construction. **No `agent_name` parameter** (D33+D43). Engine init validates config and startup gates: invalid `entry_status` / `claim_timeout` raise `ConfigError(ERR_ENTRY_STATUS_INVALID | ERR_INVALID_CLAIM_TIMEOUT)`, and unmigrated active `claimed_by` fields raise `MigrationRequiredError(ERR_MIGRATION_REQUIRED)` (D50+D57 + Brief C C11/AM-12/AM-15). **Engine init also performs opportunistic activity-log compaction:** if `activity.jsonl` exceeds 1 MB, `__init__` calls `storage.compact_activity_log(kanban_dir)` once. Failures are logged but never raise (compaction is best-effort housekeeping; the cockpit method is the explicit fallback).

- **`AgentEngineView`** — agent-facing facade. Constructed via `engine.agent_view()`. Methods: `list_tasks`, `show_task`, `pick_tasks`, `create_task`, `edit_task`, `move_task`, `start_work`, `end_work`. **No OCC** parameter on writes (D46). MCP server dispatches every agent-facing tool through this view. `pick_tasks` is on the agent view (per D59-revised): role isolation is documented in skill / tool docstring, not in the type system.

- **`CockpitEngineView`** — Cockpit-facing facade. Constructed via `engine.cockpit_view()`. Methods: `list_tasks`, `show_task`, `list_activity`, `list_sessions`, `edit_task` (OCC required), `move_task` (OCC required), `release_task`, `sweep`, `scan_corruption`, `repair_storage`, `compact_activity`. **No `create_task`** (task creation is an agent action via MCP). **No `start_work` / `end_work`** (humans don't claim via Cockpit). Cockpit's unclaim path is `release_task` (admin force-release). The maintenance surface (`scan_corruption`, `repair_storage`, plus the activity/session reads) is engine-side; **Brief B does not commit cockpit *product* scope to consume them.** A separate ideation task (created at handoff, blocked by user DR) carries the question of how/whether the cockpit grows operator-console UI for these capabilities. Treat the engine surface as ready, the cockpit consumption as TBD.

**Response / session types:**

- **`SessionRecord`** — one claim period for a task, derived from the board-level activity stream:
  ```python
  class SessionRecord(BaseModel):
      task_id: int
      task_status_at_start: str   # task status when start_work fired; stored in event detail
      state: str                  # "running" | "stuck" | "completed" | "blocked" | "rejected" | "released" | "expired"
      started_at: str             # ISO-8601 UTC timestamp of start_work event
      ended_at: str | None        # ISO-8601 UTC of close event; None = session still claimed
      outcome: str | None         # "success" | "block" | "reject" | "release" | "expired" | None
      duration_s: int | None      # seconds; None when still active
  ```
  `list_sessions(filter)` return type: `list[SessionRecord]`. Filter values per D31: `"active"` (`state in {"running", "stuck"}`), `"all"`, `"blocked-or-rejected"`, `"released"`. Engine derives sessions by pairing `start_work` events with their corresponding close events per task_id from the activity stream. `task_status_at_start` is stored in the `start_work` event's `detail` field by the engine at write time (e.g., `"status=in-progress"`), so derivation does not re-read task files. `state` is a session-level classifier for cockpit/history use; task claimed state remains on task projections (`claimed_at` / derived `claimed`), not here.

### 3.2 Method exposure matrix

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

### 3.3 Configuration

`BoardConfig` (Pydantic):
- `statuses: list[str]` — ordered status enum (e.g., `["research", "backlog", "todo", "in-progress", "review", "docs", "done"]`).
- `terminal_status: str = "done"` — the unique pre-archive terminal status. MUST equal `statuses[-1]` (D65); else `ConfigError(ERR_TERMINAL_STATUS_INVALID)`. Default preserves OwlBear convention; consumers can rename without engine code changes.
- `entry_status: str = "research"` — status assigned by `create_task`. Must be in `statuses` (D50).
- `priorities: list[str]` — priority enum.
- `archival_reasons: list[str] = ["completed", "deprecated", "dropped", "duplicate", "wontfix"]` — frozen literal (D37).
- `agent_map: dict[str, str]` — status → agent name. Engine validates coverage at init: every status maps to an agent, else `ConfigError` (D24).
- `agent_types: dict[str, str]` — agent name → bucket name (per D62). Buckets: `"auditor"`, `"builder"`, `"light-flex"`, `"heavy-flex"`. Engine validates at init that every value is a key in `agent_compatibility`, else `ConfigError`.
- `agent_compatibility: dict[str, list[str]]` — bucket → compatible bucket list (per D63). Symmetry validated at init. Default value codifies the current orchestrator skill's wave-assembly matrix.
- `wave_size: int = 4` — default `pick_tasks` wave size (D42).

These four dispatch fields are a deliberate persistent contract, not incidental tuning knobs. Under Brief B, the board config becomes the source of truth for status→agent mapping and wave compatibility policy; the orchestrator skill consumes that policy and no longer defines a second competing matrix.
- `claim_timeout: str = "30m"` — `Ns/Nm/Nh/Nd` format (D29).
- `non_impl_tags: list[str]` — tag whitelist consumed by predicate DSL `test_section_or_non_impl_tag` per D64. Default per D15 sketch: `["research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality", "type:user-action"]`.
- `status_predicates: dict[str, PredicateConfig] = {}` — write-time gate per status (D15 with predicates moved to write-time). DSL keys locked by D64: `required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`. Brief C planning may add new keys as discrete tasks; no Brief B contract drift.

### 3.4 Error taxonomy

`KanbanError` subclasses with named codes (D27 + D48 + D57):

- **`ValidationError`** — caller violated the contract. MCP maps to `ToolError`. Cockpit maps to HTTP **422** per D27.
- **`NotFoundError`** — referenced entity missing. MCP maps to `ToolError`. Cockpit maps to HTTP **404** per D27.
- **`ConcurrencyError`** — claim or OCC conflict. MCP maps to `ToolError`. Cockpit maps to HTTP **409** per D27.
- **`ConfigError`** — engine/config init failure (e.g., invalid `BoardConfig.entry_status` or malformed `claim_timeout`). Raised by `KanbanEngine.__init__`. Not a request-time error.
- **`CorruptionError`** — data integrity violation discovered at read time (e.g., duplicate frontmatter IDs per D19). Cockpit maps to HTTP **500** per D27. Surface treatment is otherwise Brief C's choice.
- **`MigrationRequiredError`** — engine-startup migration gate for unmigrated active task files (`claimed_by` still present). Raised by `KanbanEngine.__init__`. Not a request-time error.

Canonical error code list: see `decisions.md` §D57. Every code referenced in `paper-integration.md` §1/§3 is in D57; every D57 code is referenced from at least one engine surface element.

### 3.5 Cross-cutting contracts

Authoritative definitions in `paper-integration.md` §3. Summary:

1. **`archival_reason` enum** — 5 values; engine validates at every write site that accepts the field; `completed` requires current status equal to `BoardConfig.terminal_status` (the gate where archived-completion is only valid out of the terminal status).
2. **`archival_refs` rules** — D37 matrix: required for `deprecated`/`duplicate`, forbidden for `completed`/`dropped`/`wontfix`, all IDs must exist, no self-ref, no cycle.
3. **`dep_status` semantics** — D38: pure function of dep states; computed every read; precedence `blocked > redirect > ok`.
4. **Cross-reference validation** — every write that sets/mutates `parent`, `depends_on`, `add_dep`, `archival_refs` validates existence at the engine layer.
5. **Timestamp wire format** — D14: UTC, ISO 8601 with explicit offset (`+00:00` or `Z`).
6. **No silent ignore** — D27+D57: every contract violation raises a `KanbanError` with a code and `user_message`. No best-effort, no warning mode, no silent drop.
7. **`guidance` envelope field** — D39: engine emits soft warnings/hints on response envelopes only. Never on `Task` model. Never persisted. Sources: section multi-match, body size warning, dispatch hints, skip-transition warning (D54), block-outcome Action-Request / Decision-Request suggestion (D54).
8. **Archived-task rollout gate** — Brief A's archived-task guarantees are enabled only after Brief C has metadata-normalised existing archive files so contractual archive fields (`archival_reason`, `archival_refs`) are present and valid. This gate does not require full archive body or vendor-field normalisation.
9. **Board-level activity stream** — cockpit/admin history is a first-class engine capability, backed by a single gitignored board-level `activity.jsonl` runtime file owned by Brief C. `list_activity` exposes raw filtered events; `list_sessions` is a derived read model over the same stream. This does not reintroduce `claimed_by` as task state.

### 3.6 Per-method contracts

The argument-level contract for each engine method is **`paper-integration.md` §1.1–§1.8 and §5**. That document is normative for Brief B. This brief summarises the surface; the paper specifies the cells.

Highlights:

- **`create_task`** — no `status` parameter (D50). Tasks land at `BoardConfig.entry_status`. If a predicate is configured for that status, it fires on create.
- **`edit_task`** — retains `block_reason=` for state-assertion writes (D53). No OCC on AgentView; OCC required on CockpitView.
- **`move_task`** — any-to-any transitions allowed (D49); destination predicate fires per D15+D41 atomicity.
- **`start_work`** — sets `claimed_at` only. No `claimed_by` (D11). No identity check.
- **`end_work`** — 4 outcomes (D52): `success` (any-status auto-advance + terminal-step auto-archive), `reject` (requires `move_to`; archives if `move_to="archived"`), `release` (idempotent on unclaimed per D55), `block` (requires `block_reason`; optional `move_to`). Forbidden-parameter matrix is deterministic per `paper-integration.md` §1.8.
- **`release_task`** (Cockpit-only) — admin force-release; idempotent on already-unclaimed; `updated` advances only when state changes.
- **`sweep`** (Cockpit-only) — startup-safe claim maintenance only: releases all expired claims (D18+D36 compare-and-clear); returns `list[int]` of released IDs. No quarantine, no AR creation, no corruption repair.
- **`scan_corruption`** (Cockpit-only) — read-only corruption scan. Calls `storage.detect_corruption(path, config)` for every file in `tasks/` and `archive/`; aggregates and returns `list[CorruptionError]`. Makes no writes. Intended for Cockpit health-check polling: the Cockpit calls this on a timer and surfaces a badge/count when issues are found. Never triggers repair.
- **`repair_storage`** (Cockpit-only) — user-triggered two-phase repair. **Phase 1:** calls `storage.scan_and_fix(kanban_dir, config)` which handles detection, auto-fix (writes), and quarantine (file moves); returns a list of `RepairOutcome` objects where `action="quarantined"` items need an AR task. **Phase 2:** for each `action="quarantined"` outcome, engine calls `self.create_task(...)` to create the Action Request (respecting entry_status predicate, ID allocation, etc.) and records the AR id in the outcome detail. Returns the final merged `list[RepairOutcome]`. Never called implicitly at startup. The clean two-phase split is required to avoid a circular import: `storage.scan_and_fix` cannot call back into the engine (engine imports storage); AR creation is always an engine responsibility.

### 3.7 Atomicity invariant (D41)

Every engine write either succeeds completely or fails completely. There is no partial application. Specifically:

- **Predicate failure on `move_task` / `end_work(reject, move_to=…)` / `end_work(success)` / `end_work(block, move_to=…)`** → status NOT changed, claim NOT cleared, note NOT appended, blocked flag NOT set, `block_reason` NOT set.
- **Forbidden-parameter failure on `end_work`** → engine validates BEFORE any state mutation; on failure, no part of the call applies.
- **OCC failure on Cockpit writes** → no state mutation.
- **Cross-reference failure (parent/dep/archival_ref missing)** → no state mutation.

Concretely: tests must verify that a failed `end_work(success)` with a malformed predicate result leaves `claimed_at` set, `status` unchanged, and `updated` unchanged.

---

## §4 — Adapter Mapping

### 4.1 MCP adapter

The MCP server is a **mechanical translator** (per O1+O6). Its responsibilities are exhausted by:

1. **Schema validation.** Pydantic-level rejection of malformed input before reaching the engine. Example: `edit_task(status=…)` is rejected at the MCP Pydantic schema; the engine's `edit_task` does not accept `status` either. The Cockpit adapter's Pydantic request schema applies the symmetric rejection (§4.2 #1) so AC13 holds at both consumer boundaries. Schema validation is the only "logic" in the adapter — and it is structural, not semantic.
2. **View selection.** `list_tasks`, `show_task`, `pick_tasks`, `create_task`, `edit_task`, `move_task`, `start_work`, `end_work` → `AgentEngineView`. `release_task` is **dropped from MCP entirely** (Cockpit-only per Brief A "Declined entirely" + §3.2).
3. **Error wrapping.** `KanbanError(code, user_message)` → `ToolError(user_message)`. The `code` is preserved in the adapter logs; the user-facing surface gets `user_message`.
4. **Response envelope construction.** The engine returns the typed envelope (`ListTasksResponse`, `ShowTaskResponse`, `PickTasksResponse`, `SingleTaskResponse`); the adapter serialises to MCP wire format.

No business logic. No fallback handling. No "best effort." If the adapter contains an `if`/`else` branch beyond view selection or schema mapping, that is a bug.

### 4.2 Cockpit adapter

The Cockpit FastAPI backend (`serve/cockpit/src/owlbear_cockpit/`) constructs `KanbanEngine` and uses `engine.cockpit_view()` exclusively for mutations (D9+D21). Its responsibilities:

1. **HTTP route → view method.** Each served cockpit backend route maps to one `CockpitEngineView` method. Brief B scope includes not only the existing `/tasks/{id}/move`, `/edit`, and `/release` mutations, but also backend exposure of the new admin/history methods (`list_activity`, `list_sessions`, `scan_corruption`, `repair_storage`, `compact_activity`) so later cockpit work can consume a finished service-side interface. Request-body Pydantic schemas mirror the engine view's parameter set; in particular the `/edit` request schema MUST NOT accept `status` (AC13 symmetric rejection at the Cockpit boundary). If the Cockpit GUI ever needs to change a task's status, it MUST call the `/move` route, not `/edit`.
2. **OCC token plumbing.** `expected_updated` from request body → view method parameter (D22+D46). Mismatch → `ConcurrencyError(ERR_STALE)` → HTTP 409.
3. **Error → HTTP status mapping** (per D27). `ValidationError` → 422, `NotFoundError` → 404, `ConcurrencyError` → 409, `CorruptionError` → 500. `code` and `user_message` returned in response body.
4. **Read caching.** `MtimeScanCache` (existing) — engine reload skipped when task-dir mtime is unchanged. Brief B does not specify caching policy; the engine itself does no caching.
5. **Init-time `sweep()`.** Cockpit calls `engine.cockpit_view().sweep()` on startup (D18 — fixes existing Cockpit bug where stale claims persist across restarts). Because `sweep()` is claim-only, this startup hook remains safe and predictable.

No business logic. The current Cockpit OCC logic that lives in the backend retires; OCC moves into the engine view.

---

## §5 — Acceptance Criteria

The full AC table is `paper-integration.md` §4. This brief locks the AC contract at that table.

**AC inventory (post-Brief A revisions per §8):**
- 29 retained Brief A ACs (AC1–AC30 minus AC21, which is removed; AC18 reworded for any-status `success` per D52).
- Of those, **AC13** is an **adapter-layer** rejection (Pydantic-level `edit_task(status=...)` rejection at the MCP and Cockpit boundaries). The engine `edit_task` signature does not accept `status`; the engine therefore has no AC13 element. AC13 is documented in the paper for completeness and is the only Brief A AC that is not an engine contract.
- **23 new Brief B ACs (AC-NEW-1 through AC-NEW-23)** covering: `block` outcome validation, `release` idempotency, `success`/`reject`/`block` on unclaimed, invalid outcome, skip-transition guidance (1–8); deterministic `end_work` forbidden-parameter combinations + atomic-rollback (9–13); `BoardConfig.entry_status` config validation (14); `edit_task(parent=...)` (15); parametric missing-id across writes (16); `end_work(reject, archived)` without reason / `end_work(release, move_to)` / `end_work(release, archival_*)` / `end_work(block, archival_*)` (17–20); `release_task` idempotency / `sweep` return contract (21–22); `BoardConfig.terminal_status` init-time validation (in `statuses` and equal `statuses[-1]`) per D65 (23).
- **AC-NEW-24** covers the Cockpit-side AC13 mirror: `POST /api/tasks/{id}/edit` with `status` in body → HTTP 422 (Pydantic request schema rejects before reaching the engine).

**Auditability claim (narrowed).** Every AC row in `paper-integration.md` §4 maps to one or more engine method invocations described in `paper-integration.md` §1 (or, in the singular case of AC13, to an adapter-layer rejection). The reverse direction is **not** strictly enforced: some engine validation rows (e.g., enum validations on read tools, empty-string section, `start_work` on archived/blocked) are not mirrored 1:1 by an AC row, because they are either trivial enum/Pydantic checks or covered indirectly. Brief B does not promise exhaustive bidirectional coverage; Brief C planning may add ACs as decomposition tasks where useful.

---

## §6 — Brief C Handoff Notes

No Brief B contract decisions are deferred. The five items previously listed as M5-open are all locked:

One rollout precondition is explicit: first-class archived reads in Brief A are enabled only after Brief C has backfilled contractual archive metadata on existing archive files. This is metadata-only normalisation; archive body and vendor-field cleanup remain out of scope.

One new storage dependency is also explicit: cockpit/admin history is no longer "out of scope." Brief C must own a single gitignored board-level `activity.jsonl` runtime file, the query substrate behind `list_activity`, and the semantic compaction policy that keeps that file bounded without silently deleting open-session or recent history.

1. **`pick_tasks` ordering algorithm** — locked by D60: greedy, sorted by `(priority_rank ASC, age DESC, id ASC)`.
2. **`pick_tasks` view placement** — on `AgentEngineView`. (`OrchestratorView` retired per D59-revised; D61 vacated. Role isolation is documentary, not type-enforced.)
3. **`BoardConfig.agent_types` shape** — locked by D62: `dict[str, str]` over the four-bucket label set.
4. **`BoardConfig.agent_compatibility` shape** — locked by D63: `dict[str, list[str]]`, symmetric, with default value codifying the current orchestrator skill matrix.
5. **Predicate config DSL** — locked by D64 to the three keys + `non_impl_tags` from D15's sketch. Brief C planning may add new keys as discrete decomposition tasks.

**Items that pass to Brief C planning as natural extensions** (not Brief B contract drift, not Brief B blockers):

- Storage primitives (atomic ID allocation, locking strategy, frontmatter format, body markdown round-trip per D40).
- Performance characteristics for bulk reads (`list_tasks`, `pick_tasks`).
- Migration script for active tasks plus metadata-only archive backfill needed to satisfy Brief A's archived-task contract. Archive bodies and vendor fields need not be rewritten. Automatic `completed` defaults are allowed only where archive provenance is explicit and deterministic; ambiguous archives require triage before rollout.
- Predicate DSL operator extensions beyond D64.

## §7 — Downstream Rollout Matrix

This matrix is intentionally **interface-adjacent**: it names only the downstream artifacts that sit directly on the Brief A ↔ Brief B ↔ Brief C contract boundaries, so the planner sees practical rollout scope instead of only prose.

| Interface boundary | Downstream artifact(s) | Why it moves | Required follow-on |
|---|---|---|---|
| Brief A ↔ Brief B MCP surface | `share/skills/h-mcp-kanban/SKILL.md`, `serve/mcp-kanban/README.md` | Tool semantics changed (`pick_tasks`, archived-task contract, claim model, admin-only surfaces). | Update handbook + README to the new wire contract before implementation is called complete. |
| Brief B dispatcher ↔ orchestration workflow | `share/skills/w-orchestration/SKILL.md` | Dispatcher assumptions changed from flat `pick_tasks(limit, tag)` results to the redesigned engine-owned dispatch model, and ownership of compatibility policy moves from the skill into BoardConfig. | Rewrite orchestration guidance so it consumes engine-returned waves as-is and no longer carries its own status→agent or compatibility matrix. |
| Brief B cockpit/admin surface ↔ cockpit backend/API and later cockpit product | `serve/cockpit/src/owlbear_cockpit/**`, existing task 1042 | Engine grows `list_activity`, `list_sessions`, `scan_corruption`, `repair_storage`, claim-only `sweep`, and `compact_activity`. Brief B now commits the served cockpit backend/API interface for these capabilities so later cockpit work can build against a finished surface; cockpit product/UI scope is still a separate decision. | Implement the cockpit backend/API exposure now as part of Brief B. Keep task 1042 as the follow-on ideation gate for cockpit UI/product decisions; do not infer frontend/operator-console tasks from Brief B alone. |
| Brief B/C contracts ↔ test suite | `tests/test_cockpit_read_api.py`, `tests/test_cockpit_mutation_api.py`, `serve/kanban/tests/test_list_sessions.py` | Tests still lock `claimed_by`, legacy activity assumptions, and old sweep/repair coupling. | Add explicit test-migration tasks covering task detail shape, activity stream semantics, session derivation, and split maintenance surfaces. |
| Brief B/C ↔ implementation handoff artifacts | Brief C kickoff prompt, planner decomposition inputs, implementation checklists | The planner can otherwise under-scope the real downstream work. | Treat every touched row above as part of implementation scope, not optional documentation cleanup. |

Planner rule: any implementation plan derived from Brief B or Brief C must include the relevant rollout rows above whenever it changes the interface named in that row.

Cutover note: in the dev/main dual-checkout flow, Brief C migration is rehearsed by lane rather than treated as a single opaque event. Rehearse the config lane first, surface unresolved manual follow-up as visible `type:user-action` tasks, and migrate active tasks last at merge/cutover.

---

## §8 — Brief A Revision List

The following edits to `kanban-mcp-surface-v2/brief.md` are part of Brief B finalisation (M6). Applied as a single follow-up commit to the Brief A file:

1. **Remove AC21** ("non-claimant `end_work` → ToolError") — D11 invariant.
2. **§5.4 `create_task` signature:** drop `status` parameter — D50.
3. **§5.6 `move_task`:** re-word "unsupported transition" → "invalid status enum" — D49.
4. **§5.8 `end_work` signature:** add `block` outcome + `block_reason` parameter — D52.
5. **§5.8 `end_work` validation:** revise `success` semantics from `done`-only to any-status auto-advance — D52; update AC18 wording.
6. **§5.8 `end_work` validation:** add validation rules for `block` outcome — D52, D54.
7. **§5.2 `show_task` wording:** "matching `##` heading" → "matching heading (regardless of level)" — D56.
8. **§7 "Cross-cutting contracts":** confirm error-code names match D57.
9. **AC list:** add ACs for `block` outcome (validation, claim release, optional move_to, guidance emission); revise AC18 wording for any-status `success`.
10. **§5.3 `pick_tasks` and §8 AC22:** add `blocked==true` to dispatchability exclusions — D58 (resolves dispatcher ↔ `start_work` contradiction).
11. **§7 decisions C3 redirect semantics:** remove the deferred transitive redirect-completeness clause. `dep_status="redirect"` tasks remain dispatchable; redirect-chain resolution is agent responsibility at pickup.
12. **§5.3 `pick_tasks`:** note in the tool description that this is the dispatcher's primary tool (used by the orchestrator agent); no engine-side enforcement of caller identity (per D59 retired).
13. **§5.6 `move_task`:** note that "any two valid statuses are a valid transition" remains true at the **enum** level, but the destination's write-time predicate (configured via `BoardConfig.status_predicates` per D15) fires atomically; predicate failure → `ToolError` and no state change.
14. **§5.2 `show_task` `section`:** clarify match is case-insensitive AND whitespace-stripped on both heading and parameter (per D56), not case-insensitive only.

---

## §9 — Reference index

Brief B is composed of three documents in `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/`:

- **`brief.md`** (this file) — narrative + scope + AC summary + Brief A revisions.
- **`decisions.md`** — D1–D65 (locked decisions) + Brief A Revision List + canonical error code list (D57).
- **`paper-integration.md`** — argument-level mapping of every Brief A surface element to its Brief B engine API element. **This is the normative contract.** Where this brief and the paper disagree, the paper wins.

Supporting (M1–M3 artefacts, not normative):

- **`context.md`** — M1/M2 problem framing + outcomes.
- **`landscape.md`** — M3 code audit findings.
- **`synthesis.md`** — pragmatist synthesis of panelist stances.
- **`stances/`** — individual panelist stances.

---

## §10 — Handoff

On approval of Brief B, the following pipeline tasks are created. **The normative contract source for all downstream work is `paper-integration.md`** (per §9); this brief is the human-readable wrapper.

1. **Brief A sync status.** The §8 revision set is already applied in `.owlbear/briefs/kanban-mcp-surface-v2/brief.md`; downstream work should treat that brief as updated, not as a pending follow-up.
2. **Brief C status.** The storage-layer companion brief already exists at `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/`; its storage constraints inherit this engine contract and should be treated as the active downstream storage brief, not a future kickoff.
3. **Engine implementation tasks.** Decomposed by `planner` subagent **from `paper-integration.md`** (the normative contract), with this brief as scope/context. Bottom-up: BoardConfig + types → engine core → AgentEngineView/CockpitEngineView → MCP adapter → cockpit backend/API contract and adapter rewire. Each engine method gets a TDD-RED + TDD-GREEN pair. Brief B-derived implementation includes backend exposure of the new cockpit admin/history methods; cockpit UI/product tasks remain gated by task 1042 or a later cockpit brief. The planner does NOT author contract decisions; all surface choices are locked by D1–D65 + `paper-integration.md`.

