# Landscape: Kanban Engine API & MCP Implementation (Brief B)

**Audit Date:** 2026-04-20
**Scope:** Engine surface, MCP adapter, Cockpit consumer
**Method:** Full code read of 8 engine files, MCP server, Cockpit main/adapter/routes, boundary tests

---

## Bucket 1: Engine Surface as it Exists Today

### Public Methods & Contracts

#### `__init__(kanban_dir, agent_name=None, activity_log=None)`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L220-L237](serve/kanban/src/owlbear_kanban/engine.py#L220-L237)

- Constructs engine with filesystem root
- Generates `agent_name` as `{adjective}-{noun}` if omitted (agent_names.py pool)
- Loads BoardConfig via `config_loader.load_config()`
- Stores `_activity_log_path` conditional on config `activity_log` field
- Initializes three caches: `_task_cache`, `_archive_cache`, `_id_to_filename`

#### `list_tasks(**filters) → list[TaskSummary]`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L318-L389](serve/kanban/src/owlbear_kanban/engine.py#L318-L389)

Signature: `list_tasks(status="", tag="", priority="", search="", sort="", unclaimed=False, archived=False, limit=0, reverse=False, blocked=None)`

- Scans tasks_dir (or archive_dir if `archived=True`) via `os.scandir()`
- Caches tasks keyed by filename with mtime (cache miss on file change)
- Rebuilds `_id_to_filename` index on non-archived calls
- Applies filters sequentially: status, tag, priority, blocked, unclaimed, search
- Sorts by configurable field or by PRIORITY_RANK/STATUS_RANK
- Returns TaskSummary projections

**Silent ignores:** Empty string filters are no-ops (no validation error)
**N+1 risk:** None — single directory scan
**Brief A gap:** No `ids` parameter for batch lookup; no `archival_reason` filter; no `parent` filter

#### `show_task(task_id: str) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L391-L416](serve/kanban/src/owlbear_kanban/engine.py#L391-L416)

- Accepts numeric task ID as string
- Uses `_id_to_filename` cache first, falls back to glob search
- Returns full Task object including body
- **Does NOT support section projection**
- Raises `FileNotFoundError` if not found (no archived handling)

#### `create_task(...) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L501-L557](serve/kanban/src/owlbear_kanban/engine.py#L501-L557)

- **Exclusive file lock** on `.next_id.lock` protects next_id allocation
- Lock implementation: fcntl.flock on Unix, msvcrt.locking on Windows
- Validates status/priority against config
- Returns created Task object
- Timestamps stored as UTC ISO with offset

#### `edit_task(...) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L559-L659](serve/kanban/src/owlbear_kanban/engine.py#L559-L659)

- In-place edit; filename never changes
- Validates status/priority
- Supports tag/dependency list diffs (add/remove, not full replacement)
- Block/unblock support
- Append body with optional timestamp prefix
- Updates `updated` timestamp on every call (UTC ISO)
- Activity log: separate "block"/"unblock" entries from "edit"
- **Silent ignores:** No-op fields silently applied (no "no-op detected" error)

#### `move_task(task_id, status) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L661-L682](serve/kanban/src/owlbear_kanban/engine.py#L661-L682)

- Special case `status="archived"` moves file to archive_dir
- Uses `_move_file()` for git-aware move
- **Does NOT accept archival_reason or archival_refs**

#### `claim_task(task_id, now=None) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L684-L710](serve/kanban/src/owlbear_kanban/engine.py#L684-L710)

- Sets `claimed_by = self._agent_name`, `claimed_at = now.isoformat()`
- Rejects blocked tasks
- Rejects claims if rival agent's claim has NOT expired
- Allows re-claim by same agent
- Claim timeout via `_parse_claim_timeout()` — only "h" and "m" suffix supported

#### `release_task(task_id) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L712-L726](serve/kanban/src/owlbear_kanban/engine.py#L712-L726)

- Unconditionally clears `claimed_by` and `claimed_at`
- No-op if already unclaimed

#### `start_work(task_id, now=None) → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L728-L741](serve/kanban/src/owlbear_kanban/engine.py#L728-L741)

- Delegates entirely to `claim_task()`
- Docstring says "compound" but currently just wraps claim

#### `end_work(task_id, note, outcome="success", block_reason="", move_to="research") → Task`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L869-L962](serve/kanban/src/owlbear_kanban/engine.py#L869-L962)

- Outcomes: "success", "fail", "block", "reject"
- Success: auto-advances status to next in config sequence
- Block: sets `blocked=True` with reason
- Reject: moves to `move_to` status
- Appends timestamped note to body
- Clears claim unconditionally
- Single read→mutate→write atomic cycle
- **Gap:** No `archival_reason` parameter; no auto-archive on success-from-done

#### `sweep() → dict`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L964-L1017](serve/kanban/src/owlbear_kanban/engine.py#L964-L1017)

- Moves orphaned archived tasks to archive_dir
- Releases expired claims using claim_timeout
- Returns count dict
- **Called by MCP server on lifespan** [server.py#L111]
- **NOT called by Cockpit on init** [main.py#L37]

#### `list_sessions(filter="active") → list[WorkSession]`
**File:** [serve/kanban/src/owlbear_kanban/engine.py#L1019-L1046](serve/kanban/src/owlbear_kanban/engine.py#L1019-L1046)

- Requires activity.jsonl (returns [] if missing or disabled)
- Parses activity log, derives sessions per task_id
- Classifies open claims as "running" or "stuck" by claim_timeout age
- Filters: "active", "all", "failed-or-rejected", "released"

### Dispatch Surface

**File:** [serve/kanban/src/owlbear_kanban/dispatch.py](serve/kanban/src/owlbear_kanban/dispatch.py)

#### `pick_dispatchable(engine, limit=25, tag="") → list[Task]`

Gate sequence [lines 162-206]:
1. Terminal status exclusion: skip "archived"
2. Blocked exclusion: skip blocked=True
3. Dependency gate: skip if any depends_on ID still active
4. Claimed exclusion: skip if claimed_by non-None AND claim not expired
5. Tag filter
6. TDD gate (in-progress only): contains literal `"## Test-Writer Notes"` OR any tag in `_NON_IMPL_TAGS`
7. Clarity gate (active statuses): regex `^\s*(-\s|\d+\.\s)` matches anywhere in body

`_NON_IMPL_TAGS = {"research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality", "type:user-action"}` [lines 58-65]

Sort: `(PRIORITY_RANK, STATUS_RANK)` ascending, both hardcoded constants.

**Gap:** No waves returned; flat list, no agent assignment.

### Data Models

**File:** [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py)

#### `Task` [lines 35-53]
- `id, title, status, priority, created, updated, body, tags, parent, depends_on, blocked, block_reason, claimed_by, claimed_at`
- **Missing (Brief A requires):** `archival_reason, archival_refs, dep_status, guidance, revision`, structured body sections
- Timestamps as plain ISO strings
- `extra="allow"` preserves unknown fields

#### `TaskSummary` [lines 131-155]
- Drops body, claimed_by→bool `claimed`, drops created/updated
- Dict-style access for MCP

#### `BoardConfig` [lines 17-32]
- `version, board, tasks_dir, archive_dir, statuses, priorities, defaults, next_id, claim_timeout, activity_log`
- Timestamps NOT parsed (preserved as strings)
- **No `agent_map`, no `wave_size`**

---

## Bucket 2: MCP Adapter as it Exists Today

**File:** [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py)

### Lifespan & Context [lines 106-112]
- Single KanbanEngine instance
- **Calls `engine.sweep()` on startup** [line 111]

### MCP Tool Mappings

#### `list_tasks(...)` [lines 141-155]
- Direct delegation to `engine.list_tasks(**kwargs)`
- **Gap:** No `archival_reason` filter; no `ids` batch param

#### `show_task(task_id)` [lines 178-182]
- Calls `engine.show_task(task_id)`, converts to KanbanTask
- **Gap:** No section projection

#### `create_task(...)` [lines 184-206]
- Parses comma-separated `depends_on`, `tags` strings to lists
- Error: ValueError → ToolError

#### `move_task(task_id, status)` [lines 208-225]
- Pre-fetches task for guidance generation
- Error: FileNotFoundError, ValueError → ToolError

#### `edit_task(...)` [lines 227-290]
- **Rejects `depends_on` param** with error message [L230-L231]
- **Rejects `tags` param** with error message [L232-L233]
- Translates MCP params to engine kwargs
- **Auto-strips `"block:user"` tag** on agent block/unblock

#### `start_work(task_id)` [lines 292-299]
- Calls `engine.start_work(task_id)`
- Error: ValueError, FileNotFoundError → ToolError

#### `end_work(task_id, note, outcome, block_reason, move_to)` [lines 301-327]
- Validates outcome (in code, not via fastmcp schema)
- **Auto-strips `"block:user"` tag** when outcome="block"

#### `pick_tasks(limit=25, tag="")` [lines 383-390]
- Returns dict: `{"dispatch": [{"task_id": int, "status": str}, ...]}`
- **Gap:** No wave grouping; flat list

### Error Mapping
**Pattern:** `except (FileNotFoundError, ValueError) as exc: raise ToolError(str(exc))`
**Gap:** No structured error taxonomy; exception messages leak implementation detail.

---

## Bucket 3: Cockpit Consumer Reality

### Engine Construction
**File:** [serve/cockpit/src/owlbear_cockpit/main.py#L37-L38](serve/cockpit/src/owlbear_cockpit/main.py#L37)

```python
engine = KanbanEngine(kanban_dir, agent_name="cockpit")
app.state.engine = engine
```

- `agent_name="cockpit"` hardcoded
- **`sweep()` is NOT called** on Cockpit startup

### Adapter Surface
**File:** [serve/cockpit/src/owlbear_cockpit/adapter.py](serve/cockpit/src/owlbear_cockpit/adapter.py)

Allowed: `list_tasks, show_task, board_config, valid_transitions, list_sessions`
Boundary-enforced denial: `claim_task, start_work, end_work, pick_dispatchable` [tests/test_cockpit_boundary.py#L30-L31]

But mutation routes ALSO call `engine.move_task`, `engine.edit_task`, `engine.release_task` directly (not via adapter facade) — boundary test does not catch these because they're allowed.

### Read Routes [serve/cockpit/src/owlbear_cockpit/routes/read.py]

- `GET /api/board` — board_config + valid_transitions
- `GET /api/tasks` — MtimeScanCache-backed list
- `GET /api/tasks/{id}` — show_task; 404 on FileNotFoundError
- `GET /api/sessions` — list_sessions(filter)

### Mutation Routes [serve/cockpit/src/owlbear_cockpit/routes/mutation.py]

- `POST /api/tasks/{id}/move` — validates transition; **409** if invalid
- `POST /api/tasks/{id}/edit` — **optimistic lock** on `updated`; **409** if stale; **422** if no fields
- `POST /api/tasks/{id}/release` — 404 if not claimed; 409 if already unclaimed

### Cache
**File:** [serve/cockpit/src/owlbear_cockpit/cache.py](serve/cockpit/src/owlbear_cockpit/cache.py)

MtimeScanCache uses max mtime_ns across tasks_dir for change detection.

---

## Bucket 4: Re-litigate the 7 Conflicts with Code Citations

### 1. Claim Identity (`claimed_by`)

| Aspect | Location | Finding |
|--------|----------|---------|
| Field exists | [models.py#L44](serve/kanban/src/owlbear_kanban/models.py#L44) | `claimed_by: str \| None = None` |
| Written | [engine.py#L701](serve/kanban/src/owlbear_kanban/engine.py#L701) | `record.claimed_by = self._agent_name` |
| Read | [engine.py#L699-L705](serve/kanban/src/owlbear_kanban/engine.py#L699-L705) | Used to detect rival claims for timeout gating |
| Coerced to bool | [models.py#L144-L147](serve/kanban/src/owlbear_kanban/models.py#L144-L147) | TaskSummary.claimed |
| Value semantics | [agent_names.py](serve/kanban/src/owlbear_kanban/agent_names.py) | Adjective-noun pool for MCP; "cockpit" hardcoded for Cockpit |

**Disposition:** Theater identity (not actionable). Brief B should keep the field (rival-claim timeout requires presence/absence) but document it as a sentinel. May rename to `claim_owner_token` and explicitly document non-identity semantics.

### 2. Wave Composition

| Aspect | Location | Finding |
|--------|----------|---------|
| Engine support | [dispatch.py#L162-L206](serve/kanban/src/owlbear_kanban/dispatch.py#L162-L206) | Flat Task[] with 7 gates |
| Agent assignment | dispatch.py | None |
| MCP response | [server.py#L383-L390](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L383-L390) | `{"dispatch": [{"task_id", "status"}]}` |
| Hardcoded ranks | [dispatch.py#L28-L43](serve/kanban/src/owlbear_kanban/dispatch.py#L28-L43) | PRIORITY_RANK, STATUS_RANK constants |

**Disposition:** Per B1 decision — engine owns waves + agent_map. Implement `pick_waves(wave_size, max_waves) → list[Wave]` with intra-wave dep guarantee.

### 3. Locking

| Primitive | Location | Used For |
|-----------|----------|----------|
| Exclusive file lock | [engine.py#L195-L220](serve/kanban/src/owlbear_kanban/engine.py#L195-L220) | Next-ID allocation in create_task |
| Optimistic lock | [routes/mutation.py#L150-L153](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L150-L153) | Edit conflict (409 if stale) |
| Token | [models.py#L39](serve/kanban/src/owlbear_kanban/models.py#L39) | `updated` timestamp string |

**Disposition:** Document as operation-level guarantees per O5. Next-ID atomic; edit operations support optimistic concurrency via `updated` token. Storage backend may implement differently (Brief C).

### 4. Timezone Policy

| Site | Behavior |
|------|----------|
| All write sites | `datetime.now(tz=UTC).isoformat()` |
| Activity log | UTC ISO |
| Claim expiration calc | `(now - ref_dt).total_seconds()` with tz-naive→UTC normalization |

**Disposition:** Brief B aligns to existing reality. All engine timestamps UTC, ISO 8601 with offset on the wire. No per-engine TZ config. No migration cost.

### 5. TDD/Clarity Gates

| Gate | Status | Predicate |
|------|--------|-----------|
| TDD | dispatch-time | Contains `"## Test-Writer Notes"` OR tag in 9-tag set |
| Clarity | dispatch-time | Regex `^\s*(-\s\|\d+\.\s)` matches anywhere |

**Disposition:** Brief B documents existing dispatch-time gates with current loose predicates. Move-to-write-time was aspirational; not pursued. May tighten predicates (e.g., require `## AC` section), but that requires migrating existing tasks — explicit cost call-out needed.

### 6. `agent_map`

Currently absent. Brief B introduces `agent_map: dict[str, str]` field on BoardConfig (status → agent name). Engine reads to populate `DispatchEntry.agent`.

### 7. Activity Log Consumers

| Consumer | Location | Behavior |
|----------|----------|----------|
| Engine writes | engine.py L553, L656, L706, L726, L823, L986, L995, L1011 | All mutations |
| Engine reads | engine.py L1019-L1054 | `list_sessions()` only |
| Cockpit | routes/read.py L101-L116 | GET /api/sessions |
| MCP | none | No tool today |

**Disposition (per D2):** Activity log demoted to audit-only artifact, outside engine semantics. `list_sessions()` reduces to "tasks currently claimed" derived from `claimed_at`/`claim_timeout`. Closed-session history is Brief C concern (or dropped entirely).

---

## Bucket 5: New Conflicts from Architectural Choices

### A2: Body as `list[Section]`

- Today body is `str`. No section extraction code exists.
- Brief A `show_task(section=...)` is unimplemented.
- Migration: parse markdown headings at read-time into `list[Section]`. Wire format may stay markdown for backward Cockpit display, but engine model is structured.

### B1: Engine Owns Waves + agent_map

- Need `agent_map` config schema (status → agent + rank)
- Need `pick_waves()` method
- Orchestrator wave logic (if any) retires; **audit revealed no orchestrator-side wave code currently in active use** — `pick_dispatchable` is the only dispatch path
- MCP `pick_tasks` rewires to call new method

### C2: Role Views

- Cockpit-allowed methods: `list_tasks, show_task, board_config, valid_transitions, list_sessions, move_task, edit_task, release_task`
- Agent-allowed methods: above + `claim_task, start_work, end_work, pick_waves, create_task`
- Shared read methods accessible from both views
- Pattern: `engine.agent_view() → AgentEngineView`, `engine.cockpit_view() → CockpitEngineView`

### D2: No Activity Log in Engine Semantics

- `list_sessions()` returns active claims only, derived from task state
- Cockpit `/api/sessions` semantics narrow to "stuck/running"; closed-session listing dropped
- `activity.jsonl` becomes optional audit; engine may continue writing or stop entirely (Brief C decides)

---

## Bucket 6: Brief A Coverage Gaps (AC1–AC30)

| AC# | Brief A Statement | Verdict | Gap |
|-----|-------------------|---------|-----|
| AC1 | `show_task(<archived_id>)` returns archived task | CANNOT | No archived support; FileNotFoundError |
| AC2 | `list_tasks(status="archived")` | PARTIAL | Use `archived=True` boolean instead |
| AC3 | `list_tasks(ids=[...])` returns + missing_ids | CANNOT | No `ids` param |
| AC4 | move_task to archived without reason → ToolError | CANNOT | No reason param |
| AC5 | move_task archived completed from non-done → ToolError | CANNOT | No reason concept |
| AC6 | edit_task archival_reason="completed" → ToolError | CANNOT | No archival fields |
| AC7 | move_task archived deprecated empty refs → ToolError | CANNOT | No refs |
| AC8 | move_task archived dropped with refs → ToolError | CANNOT | No refs |
| AC9 | archival_reason enum validation | CANNOT | No field |
| AC10 | show_task section returns ##Heading content | CANNOT | No section projection |
| AC11 | show_task missing section returns null + missing_sections | CANNOT | No section logic |
| AC12 | Multiple ##Heading concatenated, occurrence count in guidance | CANNOT | No section logic |
| AC13 | edit_task(status=...) → ToolError (param removed) | PARTIAL | MCP doesn't reject; engine accepts |
| AC14 | edit_task body+append_body both → ToolError | UNKNOWN | Need to test; engine likely accepts both |
| AC15 | list_tasks ids+other filter → ToolError | CANNOT | No ids param |
| AC16 | No `file` field in projections | CAN | TaskSummary doesn't have file |
| AC17 | No `claimed_by` field; only `claimed_at`+`claimed` | PARTIAL | claimed_by exists in Task; TaskSummary already drops it |
| AC18 | end_work(success) from done auto-archives + clears claim | PARTIAL | end_work clears claim; doesn't archive |
| AC19 | end_work(reject, move_to=archived, reason, note) one call | CANNOT | No reason arg |
| AC20 | end_work(release) clears claim, no status change | PARTIAL | No "release" outcome — would map to existing release_task |
| AC21 | (DROPPED by user) | N/A | N/A |
| AC22 | pick_tasks ≤3 waves; no intra-wave dep edges; no claimed/blocked | CANNOT | Flat dispatch only |
| AC23 | DispatchEntry includes computed agent | CANNOT | No agent field |
| AC24 | create_task non-existent dep → ToolError | UNKNOWN | Need to verify validation |
| AC25 | edit_task add_dep non-existent → ToolError | UNKNOWN | Engine may not validate |
| AC26 | move_task archived duplicate non-existent ref → ToolError | CANNOT | No refs |
| AC27 | depends_on Y archived wontfix → dep_status=blocked, excluded from waves | CANNOT | No dep_status |
| AC28 | depends_on Y archived deprecated → dep_status=redirect | CANNOT | No dep_status |
| AC29 | Timestamps carry ±HH:MM or Z | CAN | UTC ISO with +00:00 offset |
| AC30 | append_body timestamp prepends ISO with offset | PARTIAL | Current format is `[[YYYY-MM-DD]]` (date only) |

**Critical gaps preventing Brief A fulfillment:**
1. archival_reason / archival_refs fields missing
2. Wave composition not in engine
3. dep_status computation missing
4. Section projection missing
5. agent_map config missing
6. Batch ID lookup (ids) missing
7. guidance field not on Task model
8. Error taxonomy loose
9. AC30 timestamp format weaker than spec (date-only vs full ISO)

---

## Surprises & Red Flags

### 1. Cockpit Does NOT Call sweep() on Startup

MCP server calls `engine.sweep()` on lifespan [server.py#L111]; Cockpit does not [main.py#L37]. Cockpit instances accumulate stale state across restarts.

**Brief B action:** Document that all engine consumers must call `sweep()` on init.

### 2. MCP Edit Rejects `tags`/`depends_on` But Create Accepts Them

Inconsistent: `edit_task` rejects full-replacement params for tags/deps but `create_task` accepts comma-separated. Justifiable (new vs existing task) but should be documented in Brief A revision.

### 3. Activity Log Parsing Silently Drops Malformed Lines

[engine.py#L1050-L1061] catches JSONDecodeError/ValueError, continues. No telemetry on data loss.

### 4. Claim Timeout Parsing Loose

[engine.py#L1125-L1133] only "h" and "m" suffix. No validation at config load. Delayed failure on first claim.

### 5. TDD Gate Has No Explicit Waiver Tag

9-tag escape but no `exempt:tdd` waiver. Brief B may or may not address.

### 6. Optimistic Lock is Coarse-Grained (Whole Task)

Cockpit edit conflicts on any prior mutation. Acceptable for single-user laptop scenario.

### 7. MCP ToolError Messages Leak Internal Exceptions

`raise ToolError(str(exc))` exposes file paths, config detail. Brief B's error taxonomy fixes this.

### 8. Board Config Reload Clears All Caches

[engine.py#L273-L283] `refresh_config()` invalidates all caches. Heavy operation; document as "init only".

### 9. Brief A `pick_tasks` Wave Default Not Wired

`wave_size` config field doesn't exist. Brief B must add to BoardConfig defaults.

### 10. `start_work` Does Not Auto-Release Prior Claim

Same-agent re-claim is allowed (idempotent). Cross-agent re-claim is rejected until timeout. No auto-release of prior agent's claim.

### 11. AC30 Timestamp Prepend Weaker Than Spec

Current `append_body(timestamp=True)` prepends `[[YYYY-MM-DD]]` (date only). Brief A wants full ISO with offset. Behavior change with downstream impact (existing tasks have date-only prefixes).

### 12. Cockpit Mutation Routes Bypass Adapter

Mutation routes call `engine.move_task` / `engine.edit_task` / `engine.release_task` directly, not via adapter.py. Boundary test only checks denied methods, not enforced channeling. C2 (role views) closes this.

---

## Conclusion

The engine is functionally complete for current MCP-driven pipeline use. Gaps are primarily **architectural (waves, agent assignment) and data model (archival, dep_status, sections)** rather than implementation defects.

The MCP server is mostly a clean translator with two leaks: tag-stripping side effects on block/end_work, and `ToolError(str(exc))` exception leakage.

Cockpit is a thin consumer with strong boundary tests on denied methods but no positive constraint on allowed-method channeling. C2 role views fix this.

**Brief B's primary job:** close the 7 conflicts (all documented above with citations) and bridge the Brief A contract gaps (archival, waves, agents, sections, dep_status). Foundation is solid; gaps are specification alignment, not code quality.
