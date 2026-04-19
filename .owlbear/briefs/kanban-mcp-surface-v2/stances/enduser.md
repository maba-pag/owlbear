# End-User Stance — Kanban MCP Tool Surface (Brief A)

**Panelist:** End User (UX practitioner — the calling pipeline agent)
**Scope:** MCP tool surface only. Engine-agnostic. No storage, no internal APIs, no file paths.
**Critic cycles:** 3 external + 1 internal hardening round.

---

## 1. Workflow → Tool-Call Analysis

### What agents DO with kanban today

| Agent Role | Primary Operations | Current Tools Used |
|---|---|---|
| **Orchestrator** | Scan board, dispatch work, check dependency statuses, manage stale tasks | `list_tasks`, `pick_tasks`, `show_task` ×N (deps), `move_task` |
| **Builder** | Read assigned task (AC, body), log work notes, release | `show_task`, `edit_task` (append_body), `end_work` |
| **Reviewer** | Read task for review, add evidence, detect review loops, release | `show_task`, `edit_task` (append_body), `end_work` |
| **Auditor** | Read task for audit, verify history, archive on success | `show_task`, `edit_task` (append_body), `end_work` |
| **Planner** | Survey board, batch-create tasks, set dependencies | `list_tasks`, `create_task` ×N, `edit_task` (add_dep) |
| **Architect** | Read task + all dependency statuses, append architecture review | `show_task`, `show_task` ×N (deps for status only), `edit_task` |
| **Test-Curator** | Find archived test tasks, read their content | `list_tasks` (archived), `show_task` ×N (BROKEN on archived) |
| **Memory-Curator** | Grep one section across recent tasks | `show_task` ×N (full body each time) |
| **Scribe (resolve)** | Append resolution note + unblock | `edit_task` ×2 (append + unblock) — but surface already supports both in one call; agent-skill bug |
| **Researcher** | Read task, log findings, release | `show_task`, `edit_task` (append_body), `end_work` |
| **Doc-Writer** | Read task for doc update, check section presence | `show_task` (full body to find one section) |

### What agents NEED (in fewest calls / least context)

1. **Batch status lookup by ID** — architect, orchestrator resolving `depends_on`. Need: `{id → status}` for N IDs in 1 call.
2. **Section-aware body projection** — every pipeline agent. Need: request specific `## Heading` sections, get only those back.
3. **Transparent archived reads** — auditor, test-curator, any agent following a `depends_on` to an archived task.
4. **Batch create** — planner. Need: create up to 20 tasks with intra-batch dependency graph in 1 call.
5. **Structured archival reason + successor ref** — any agent resolving "why is this task dead and what replaced it?"

---

## 2. Pain Points (ranked by frequency × cost)

| Rank | Pain Point | Affected Agents | Frequency | Cost per Hit | Fix |
|---|---|---|---|---|---|
| 1 | **Section-as-schema** — full body fetch to read one `## Heading` | ALL pipeline agents | Every task read | High (10KB+ body for 200B section) | `sections` param on `show_task` |
| 2 | **N+1 dependency resolution** — N `show_task` calls to check dep statuses | Architect, orchestrator, test-curator | Every task with deps | Medium (N round trips) | `ids` param on `list_tasks` |
| 3 | **Batch create** — 20 sequential `create_task` calls | Planner | Per decomposition cycle | Medium (20 round trips) | `create_tasks` tool |
| 4 | **Archived task reads broken** — `show_task` returns "not found" | Auditor, test-curator | Every archived lookup | Critical (total failure) | Transparent archived reads |
| 5 | **No archival reason** — "why is this dead?" unanswerable | Any dep-resolution agent | Every archived dep | Medium (forces body scan) | `archival_reason` + `archival_ref` fields |
| 6 | **Compound op non-atomicity** — scribe append+unblock in 2 calls | Scribe | Per resolution | Low | Already supported by `edit_task` — agent-skill fix, not surface fix |
| 7 | **Review loop detection** — count `## Review Evidence` repeats in body | Reviewer | Per review cycle | Low | Section projection helps; first-class counter is follow-up scope |

---

## 3. Proposed Surface (9 tools)

### 3.1 `list_tasks` — Filter and list (MODIFIED)

**Changes:** add `ids` param, add `archival_reason` filter, `status` accepts `"archived"`, DROP `archived: bool`.

| Param | Type | Default | Notes |
|---|---|---|---|
| `status` | `str` | `""` | Enum: `research\|backlog\|todo\|in-progress\|review\|docs\|done\|archived`. Empty = non-archived only. |
| `ids` | `str` | `""` | Comma-separated task IDs. Direct batch lookup. **FORBIDDEN to combine with any other filter param** (ToolError). Includes archived tasks transparently. Results in requested order; missing IDs absent; duplicates deduplicated. |
| `archival_reason` | `str` | `""` | Enum: `completed\|deprecated\|dropped\|duplicate\|wontfix`. **FORBIDDEN unless `status="archived"`** (ToolError). |
| `tag` | `str` | `""` | KEEP |
| `priority` | `str` | `""` | KEEP |
| `search` | `str` | `""` | KEEP |
| `sort` | `str` | `""` | KEEP |
| `unclaimed` | `bool` | `false` | KEEP |
| `limit` | `int` | `0` | KEEP |
| `reverse` | `bool` | `false` | KEEP |
| `blocked` | `bool\|null` | `null` | KEEP |

**Returns:** `TaskSummary[]`

**Interaction matrix:**

| `status` | `ids` | `archival_reason` | Result |
|---|---|---|---|
| `""` (default) | `""` | — | All non-archived tasks |
| `"todo"` | `""` | — | Only todo tasks |
| `"archived"` | `""` | `""` | All archived tasks |
| `"archived"` | `""` | `"completed"` | Only completed-archived tasks |
| any | set | — | Summaries for those IDs (including archived); other params forbidden |

**Drop rationale:** `archived: bool` is replaced by `status="archived"` (explicit filter) and `ids` (direct lookup including archived). No boolean flag needed. No overlapping modes.

### 3.2 `show_task` — Read one task (MODIFIED)

**Changes:** add `sections` param, transparent archived reads.

| Param | Type | Default | Notes |
|---|---|---|---|
| `task_id` | `str` | — | REQUIRED |
| `sections` | `str` | `""` | Comma-separated `## Heading` names (without `## ` prefix). Body projection. |

**Section projection contract:**
- **Matching:** Case-insensitive against `## Heading Name` in body. Agent says `"Architecture Review"`, not `"## Architecture Review"`.
- **Found sections:** Returned in original body order with `## ` headings preserved.
- **Missing sections:** `missing_sections: list[str]` on the response lists requested-but-not-found headings. Body contains only found sections. If ALL requested sections missing, body is empty string and `missing_sections` lists them all.
- **Duplicate headings:** All instances returned.
- **Default (empty):** Full body. `missing_sections` absent from response.
- **Archived tasks:** Section projection works identically on archived tasks.

**Returns:** `KanbanTask`

**Archived behavior:** TRANSPARENT. Returns a standard `KanbanTask` with `status: "archived"` and `archival_reason` set. No error, no special parameter, no header-only mode. Full body included. The agent calling `show_task("123")` doesn't need to know or care whether 123 is archived — it just gets data back.

### 3.3 `create_task` — Create one task (KEEP)

No changes to params or behavior.

### 3.4 `create_tasks` — Batch create (NEW)

| Param | Type | Default | Notes |
|---|---|---|---|
| `tasks` | `list[TaskSpec]` | — | REQUIRED. Array of task specifications. |

**TaskSpec shape:**
```
{
  title: str,                    // REQUIRED
  body?: str,
  depends_on?: str,              // Comma-separated EXISTING task IDs
  depends_on_batch?: list[int],  // 0-indexed positions within this batch (backward refs only)
  parent?: int,                  // EXISTING task ID only (not a batch position)
  priority?: str,
  status?: str,
  tags?: str
}
```

**Semantics:**
- All-or-nothing atomic. Either all tasks are created or none are.
- `depends_on_batch` indices must reference earlier items only (no forward refs, no cycles). Out-of-range or cycle = validation failure.
- `parent` is always an existing task ID. For intra-batch parent-child, set parent via follow-up `edit_task` after creation.

**Returns:** `KanbanTask[]` in batch order with assigned IDs.

**Failure:** ToolError with `{"failed_index": int, "reason": str}`. No tasks created.

**Rationale:** Planner creates up to 20 interdependent tasks per decomposition cycle. 20 `create_task` calls = 20 round trips + 20 full-task responses in context window. Batch = 1 call.

### 3.5 `edit_task` — Edit task fields (MODIFIED)

**Changes:** remove trap params, add archival metadata editing.

| Change | Detail |
|---|---|
| REMOVE `depends_on: str` | Currently always raises ToolError. Trap param is a UX failure — agents hit it, get an unhelpful error, have to figure out they need `add_dep`/`remove_dep` instead. |
| REMOVE `status: str` | Status changes go through `move_task`. Having `status` on both tools creates ambiguity about which to use. Single responsibility. |
| ADD `archival_reason: str = ""` | Enum-validated. **FORBIDDEN on non-archived tasks** (ToolError). Allows correction of archival reason after the fact. |
| ADD `archival_ref: str = ""` | Coerced to int. Must reference a valid existing task. **FORBIDDEN unless `archival_reason` is `deprecated` or `duplicate`** (ToolError). |

All other params KEEP as-is: `body`, `block`, `unblock`, `tags`, `add_tag`, `remove_tag`, `priority`, `append_body`, `timestamp`, `add_dep`, `remove_dep`, `parent`, `title`.

**Returns:** `KanbanTask`

### 3.6 `move_task` — Change status (MODIFIED)

**Changes:** `status` accepts `"archived"`, archival params added.

| Param | Type | Default | Notes |
|---|---|---|---|
| `task_id` | `str` | — | REQUIRED |
| `status` | `str` | — | REQUIRED. Now includes `"archived"`. |
| `archival_reason` | `str` | `""` | Enum-validated. **REQUIRED when `status="archived"`** (ToolError if omitted). **FORBIDDEN for non-archive moves** (ToolError if set). |
| `archival_ref` | `str` | `""` | Coerced to int. Must reference existing task. **REQUIRED when reason is `deprecated` or `duplicate`** (ToolError if missing). **FORBIDDEN otherwise** (ToolError if set). |

**`completed` gating:** `archival_reason="completed"` is only valid when the task is currently in `done` status. Archiving a non-done task as "completed" returns ToolError. This preserves the semantic contract: completed = went through the full pipeline.

**Returns:** `KanbanTask`

### 3.7 `start_work` — Claim task (KEEP)

No changes.

### 3.8 `end_work` — Release with outcome (MODIFIED)

**Changes:** archive paths set archival metadata automatically.

| Param | Type | Default | Notes |
|---|---|---|---|
| `task_id` | `str` | — | REQUIRED |
| `note` | `str` | — | REQUIRED |
| `outcome` | `str` | `"success"` | `success\|fail\|block\|reject` |
| `block_reason` | `str` | `""` | REQUIRED when outcome="block" |
| `move_to` | `str` | `"research"` | Target status for reject. Now accepts `"archived"`. |
| `archival_reason` | `str` | `""` | Enum-validated. **REQUIRED when `outcome="reject"` and `move_to="archived"`**. **FORBIDDEN for all other outcome/move combinations** (ToolError). |
| `archival_ref` | `str` | `""` | Same rules as `move_task`: required for deprecated/duplicate, forbidden otherwise. |

**Archive paths:**
- `outcome="success"` at terminal status → auto-archives with `archival_reason="completed"`, `archival_ref=null`. Always. No override.
- `outcome="reject"` with `move_to="archived"` → archives with caller-specified reason. Note appended, claim released, archived — one atomic call.

**Returns:** `KanbanTask`

**Rationale:** An agent that determines a claimed task is deprecated/duplicate/wontfix needs one call to: append its reasoning (note), release the claim, and archive with the correct reason. Without this, the agent needs 3 calls: `edit_task` (append), `end_work` (release), `move_task` (archive).

### 3.9 `pick_tasks` — Dispatch list (MODIFIED)

**Change:** aligned return shape with orchestration skill docs. Uses `id` consistently.

**Returns:**
```
{
  "dispatch": [
    {"id": int, "status": str, "priority": str, "title": str, "tags": list[str]}
  ]
}
```

---

## 4. Output Projection Shapes

### TaskSummary (list operations)

```
{
  id: int,
  title: str,
  status: str,                    // "research"|...|"done"|"archived"
  priority: str,
  tags: list[str],
  blocked: bool,
  block_reason: str | null,
  claimed: bool,
  parent: int | null,
  depends_on: list[int],
  archival_reason: str | null,    // NEW — enum or null
  archival_ref: int | null        // NEW — successor/target ID or null
}
```

### KanbanTask (full detail)

```
{
  guidance: list[str],
  id: int,
  title: str,
  status: str,                    // "research"|...|"done"|"archived"
  priority: str,
  created: str,                   // RFC3339
  updated: str,                   // RFC3339
  claimed: bool,
  tags: list[str],
  parent: int | null,
  depends_on: list[int],
  blocked: bool,
  block_reason: str | null,
  body: str | null,
  archival_reason: str | null,    // NEW — enum or null
  archival_ref: int | null,       // NEW — successor/target ID or null
  missing_sections: list[str] | null  // NEW — present only when sections param used
}
```

**Dropped:** `file: str | null` — leaks storage implementation. No pipeline agent uses file paths through MCP. If Cockpit needs it, that's the engine API (Brief B).

### Archival Reason Enum

`completed | deprecated | dropped | duplicate | wontfix`

Validated at MCP surface on every tool that accepts it. Invalid value → ToolError.

### Archival Ref Rules

| Reason | `archival_ref` |
|---|---|
| `completed` | null (always) |
| `deprecated` | REQUIRED — successor task ID |
| `dropped` | null (always) |
| `duplicate` | REQUIRED — target (kept) task ID |
| `wontfix` | null (always) |

### Presence Rules

| Task State | `archival_reason` | `archival_ref` |
|---|---|---|
| Active (non-archived) | `null` always | `null` always |
| Newly archived (via new surface) | Non-null (enforced by tool validation) | Non-null where required (deprecated/duplicate) |
| Legacy archived (pre-migration) | May be `null` — migration is Brief C | May be `null` |

---

## 5. Archived-Task Read Behavior

**Decision: Transparent full return.**

`show_task(task_id)` on an archived task returns a standard `KanbanTask` with `status: "archived"` and `archival_reason` set. Full body included. No special parameter.

### Why this design

The two primary consumers of archived reads are:
1. **Agents resolving `depends_on`** — need to see that the dep is done/dead and why. They need `status` + `archival_reason` + `archival_ref`. Body is optional but harmless.
2. **Auditor/reviewer tracing history** — need to read the full body (audit sections, review evidence, builder notes).

Transparent return serves both consumers in one call.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| "Task archived" error message | Forces error-handling branch for a normal lookup. Violates Outcome 2 ("no not-found surprises"). |
| "Use parameter XYZ to read archived" | Adds cognitive load. The agent must know about a special incantation for archived tasks. Violates Outcome 1 ("cost should not shift into figuring out which tool to call or how"). |
| YAML-header-only return | Auditor/reviewer need the body. Forces a second call to get it. Two calls worse than one slightly larger response. |
| Opt-in full read (default = header) | Penalizes the common case (agents that need the body) to save tokens for the uncommon case (agents that only need status). Wrong default. |

### Context-window cost

Archived task bodies can be large (accumulated notes from multiple pipeline stages). But:
- This cost is only paid when an agent explicitly fetches a specific archived task by ID. It's intentional.
- For list operations, `TaskSummary` already excludes the body. No inflation there.
- Section projection (`sections` param) gives agents surgical extraction even on archived tasks.

---

## 6. No-Silent-Ignore Policy

Every parameter that doesn't apply to the current operation is **FORBIDDEN** (ToolError), not silently ignored. This eliminates ambiguity about whether a param was honored:

| Tool | Forbidden combination | Error |
|---|---|---|
| `list_tasks` | `ids` set + any other filter param | "ids param is exclusive — cannot combine with other filters" |
| `list_tasks` | `archival_reason` set + `status` ≠ `"archived"` | "archival_reason only applies to archived status filter" |
| `move_task` | `archival_reason` set + `status` ≠ `"archived"` | "archival_reason only valid for archive moves" |
| `move_task` | `archival_ref` set + reason ∉ {deprecated, duplicate} | "archival_ref only valid for deprecated/duplicate" |
| `move_task` | `status="archived"` + reason = `"completed"` + current status ≠ `done` | "completed archival requires task in done status" |
| `edit_task` | `archival_reason` set + task not archived | "archival_reason only editable on archived tasks" |
| `end_work` | `archival_reason` set + not (reject + move_to=archived) | "archival_reason only valid for archive-reject path" |

---

## 7. Key Trade-offs

| # | Trade-off | Decision | Rationale |
|---|---|---|---|
| 1 | Section projection adds param complexity | **Add it** | Single biggest context-window sink. One optional param vs. 10KB body fetches for 200B sections. |
| 2 | `ids` on `list_tasks` overloads the tool | **Overload it** | Avoids a 10th tool. The `ids` mode is clearly delineated (exclusive — forbids other params). |
| 3 | `create_tasks` adds a new tool | **Add it** | Planner does 20 calls/cycle. Batch = 1 call. Simple all-or-nothing semantics. |
| 4 | Transparent archived reads cost more tokens | **Accept the cost** | One bigger response beats two smaller ones. Section projection mitigates when full body isn't needed. |
| 5 | Dropping `file` from MCP output | **Drop it** | Implementation leak. No agent uses it. Cockpit uses engine API. |
| 6 | `archival_reason` editable after archive | **Allow it** | One-call correction beats 2-call un-archive/re-archive. Audit trail is a storage concern (Brief C). |
| 7 | `archival_ref` as string param coerced to int | **Accept** | Avoids the `int = 0` sentinel ambiguity. Empty string = not provided. Follows existing `depends_on` pattern. |

---

## 8. Warnings

1. **Section projection depends on stable section naming.** If the pipeline protocol renames a section heading, agents requesting the old name get `missing_sections` back instead of data. The protocol must canonicalize section names.
2. **`archival_reason` required on archive-move will break current agents.** Agents that archive via `move_task` without specifying a reason will get ToolError. This is intentional — forces explicit reasons — but requires agent skill updates.
3. **`create_tasks` all-or-nothing** means one invalid spec kills the whole batch. Planner must validate inputs before calling.
4. **Legacy archived tasks** will have `archival_reason: null` until migration (Brief C). Consuming agents must handle null even though new archives are guaranteed non-null.
5. **Multi-task section projection is unsolved.** The N+1 pattern for memory-curator (grep one section across N tasks) is not addressed by single-task `sections` param. This is a follow-up design problem.

---

## 9. Out-of-Scope Follow-ups

These surface needs were identified during analysis but are outside Brief A's archive-focused scope:

| Need | Affected Agent | Brief A Assessment |
|---|---|---|
| Last-note / latest-section projection | Orchestrator (stale tasks) | Valuable but distinct design problem |
| First-class cycle/fail count | Reviewer (loop detection) | Could be a computed field on TaskSummary; needs analysis |
| `valid_transitions(task_id)` tool | All agents (avoid invalid moves) | Engine capability exists; MCP exposure is low effort |
| `list_sessions()` tool | Orchestrator | Engine capability exists; MCP exposure is low effort |
| Multi-task section projection | Memory-curator, reviewer | The biggest remaining N+1; deserves its own design |

---

## 10. Confidence

**0.82**

The surface design addresses all four locked outcomes:
1. ✅ Minimum tool calls / minimum context — batch ID lookup, section projection, batch create
2. ✅ Archived tasks first-class readable — transparent `show_task`, `status="archived"` in lists
3. ✅ Structured archival reason — enum field on all output shapes, validated on all mutation tools
4. ✅ Surface coherent after change — no vestigial params, no overlapping tools, no ambiguity

Remaining uncertainty:
- Multi-task section projection unsolved (follow-up)
- `archival_reason` mutability trade-off may need revisiting after Brief C (storage audit trail)
- Critic challenged the `completed` gating and `archival_ref` representation until the final round; these feel solid now but haven't been validated by the Architect panelist
