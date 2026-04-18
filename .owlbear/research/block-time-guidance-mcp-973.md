# Block-Time Guidance from owlbear-kanban MCP

> **Owning task:** #973 — Block-Time Guidance from owlbear-kanban MCP
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Agents block tasks without creating Decision Requests despite multiple instruction-file updates. The approved Brief proposes adding a `guidance` field to MCP tool responses that surfaces action-required messages at the point of the blocking operation. This research validates feasibility, identifies implementation touchpoints, and decomposes into atomic tasks.

The Brief and 9 locked decisions (D1–D9) were produced via a 3-round architect–critic debate. No new recommendation needed — this research validates the locked approach against current codebase state.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | .95 — `KanbanTask` model, target for `guidance` field |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | .95 — `edit_task`, `end_work`, `move_task`, `_record_to_task`, `_show_validated` |
| S3 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Codebase | .90 — `edit_task` route, `_build_edit_kwargs`, tag-diff logic |
| S4 | `serve/kanban/src/owlbear_kanban/engine.py` | Codebase | .85 — `board_config()`, `_status_rank`, `edit_task` kwargs |
| S5 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/` | Codebase | .95 — Brief, decisions D1–D9, architect debate |
| S6 | `.owlbear/research/gate-blocked-task-remediation.md` | Codebase | .70 — prior art on gate-warning field pattern |

## 3. Analysis

### 3.1 Feasibility Validation

| Touchpoint | Current State | Change Required | Risk |
|------------|---------------|-----------------|------|
| `KanbanTask` model | 14 fields, no `guidance` | Add `guidance: list[str] = []` as first field | None — Pydantic v2 default + declaration-order serialization |
| `_record_to_task` | `model_validate(record.model_dump())` | No change — engine `Task` lacks `guidance`, Pydantic uses default `[]` | None |
| `_show_validated` | Returns `KanbanTask` from engine read | No change — used as-is for `move_task` pre-read | None |
| `edit_task` (MCP) | Block branch sets `blocked`+`block_reason` | Attach guidance post-engine-call; remove `block:user` tag | Low — append to existing kwargs |
| `end_work` (MCP) | Returns `KanbanTask` after engine call | Attach guidance for block + success outcomes | Low |
| `move_task` (MCP) | Delegates directly to engine | Pre-read via `_show_validated`; attach guidance for forward-skip | Low — 1 extra FS read |
| Cockpit `edit_task` | `_build_edit_kwargs` + set-diff tags | Inject `block:user` add/remove in route handler, after kwargs built | Low — avoids tag-diff conflict |
| `board_config()` | Public method, returns `BoardConfig` | Used for status ordering; `statuses` is `list[dict]` with `name` key | None — already public |
| `_STATUSES` (server.py) | Hardcoded `list[str]` for enum validation | Not used for guidance — `board_config().statuses` is canonical | None |

### 3.2 Tag-Diff Conflict Resolution (D3, architect debate R1.1)

The cockpit `_build_edit_kwargs` uses full-replacement set-diff for tags. Injecting `block:user` inside the helper would conflict with explicit tag sets sent by the frontend. Solution (locked): inject in the route handler by appending to the computed `add_tags`/`remove_tags` kwargs after `_build_edit_kwargs` returns.

```
kwargs = _build_edit_kwargs(req, task)
if blocking:  kwargs.setdefault("add_tags", []).append("block:user")
if unblocking: kwargs.setdefault("remove_tags", []).append("block:user")
```

### 3.3 Forward-Skip Detection (D6)

`board_config().statuses` returns `list[dict[str, Any]]` — extract ordered names: `[s["name"] for s in config.statuses]`. Compare old rank vs new rank. Skip > 1 slot (excluding `archived`) triggers guidance. `_show_validated` already exists for the pre-read.

### 3.4 Confidence Assessment

| Aspect | Confidence | Note |
|--------|-----------|------|
| Model field addition | .95 | Trivial Pydantic change |
| Guidance module (3 rules) | .90 | Pure function, well-specified |
| MCP tool integration | .85 | Straightforward post-processing; `move_task` pre-read adds ~1ms |
| Cockpit tag lifecycle | .85 | Tag-diff conflict resolved; route-handler injection is clean |
| Overall | .88 | |

Challenge: SKIPPED — approach locked via 3-round architect debate with 9 decisions. No new recommendation.

## 4. Recommendation

Proceed with implementation per Brief Path A1 and decisions D1–D9. All touchpoints exist and are accessible. No engine changes needed. No blockers found.

Confidence: .88

## 5. Follow-up Tasks

See task body for created task IDs.
