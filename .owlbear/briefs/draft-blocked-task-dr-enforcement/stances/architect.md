# Architect Stance — Blocked Task DR Enforcement (MCP Guidance Pattern)

## Architectural Stance

### Q1: Where does guidance text live in the response?

**`guidance: list[str] = Field(default_factory=list)` as the FIRST declared field on `KanbanTask`.**

Add the field to [models.py](serve/mcp-kanban/src/owlbear_mcp_kanban/models.py#L9) before the `id` field. Pydantic v2 serializes in declaration order, so `guidance` appears first in every JSON response — the strongest salience guarantee available within locked constraints (no elicitation, no prompts, no sampling, no `ctx.info/warn`).

This is a deliberate schema change across all six task-returning tools. The `outputSchema` patch at [server.py:349–353](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L349) auto-propagates because it calls `KanbanTask.model_json_schema()`. Zero manual schema work. Existing Pydantic consumers with `extra="ignore"` or `extra="allow"` are unaffected. Agents reading raw JSON will see the new field — that is intentional and is how they discover the guidance channel.

Empty `[]` on non-target tools costs ~15 bytes per response. Schema consistency (always present, never null) beats null-check complexity.

**Rejected alternatives:**
- **(b) Envelope `ToolResult[KanbanTask]`:** Breaks every existing consumer's expected schema and requires forking the schema patch per-tool.
- **(c) Per-tool envelope:** Same breakage for three tools; inconsistent return types across the tool set.
- **(a) `guidance: str | None`:** Single string limits composability when multiple rules fire on one call.

### Q2: The single-place mechanism — guidance registry

**New module `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` with a flat rule list.**

```python
def collect_guidance(
    action: str,                    # Tool name: "edit_task", "end_work", "move_task"
    *,
    task: KanbanTask,               # Result task object (post-mutation)
    outcome: str = "",              # For end_work: "success", "block", etc.
    old_status: str = "",           # For move_task: status before the move
    status_names: list[str] = (),   # Ordered config statuses for skip detection
) -> list[str]:
```

Three `GuidanceRule` named tuples for V1, defined as a module-level list:

1. **Block → DR mandate:** Fires on `edit_task` when `task.blocked is True`, or `end_work` when `outcome == "block"`. Message: `"⚠️ ACTION REQUIRED: Create a Decision Request for this block. See scribe conventions."` (exact wording TBD in implementation).
2. **Forward-skip warning:** Fires on `move_task` when `new_rank - old_rank > 1` (ranks from `status_names` config order). Excludes `status == "archived"`. Message: `"⚠️ Forward-skip detected (skipped N statuses). Confirm this is intentional."`
3. **Commit-pushed reminder:** Fires on `end_work` when `outcome == "success"`. Message: `"Reminder: ensure your commit has been pushed before proceeding."`

Only `edit_task`, `end_work`, and `move_task` call `collect_guidance()`. Other tools return the default empty list. Rule list iteration order = message order. At most one rule fires per call in V1.

No class hierarchy, no decorator dispatch, no registry pattern. YAGNI — three rules, a flat list, one function. Adding a fourth rule: append one tuple.

### Q3: Trigger detection for `move_task` forward-skip

**Pre-read via `_show_validated()` in the MCP tool layer. Public `engine.board_config().statuses` for the ordered status list.**

The MCP `move_task` tool at [server.py:209](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L209) calls `_show_validated()` before `engine.move_task()` to capture old status. Same pre-read pattern as Cockpit's `move_task` route at [mutation.py:83](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L83).

Status ordering uses `engine.board_config().statuses` — a **public** method at [engine.py:303](serve/kanban/src/owlbear_kanban/engine.py#L303) returning a defensive copy. Each entry is `{"name": str, ...}`. Index position = pipeline rank. This is the canonical ordering. (`dispatch.py`'s `STATUS_RANK` is a separate concern for dispatch priority.)

**Forward-skip formula:** `new_rank - old_rank > 1` where ranks are index positions in the config statuses list. **"archived" is excluded** — it is not in the config statuses list and represents a terminal action, not a pipeline skip. The predicate returns no guidance when `status == "archived"`.

**TOCTOU race:** The old-status pre-read and `move_task` call are non-atomic. Worst case: a spurious or missed advisory. Acceptable for soft guidance that doesn't gate the operation.

### Q4: Cockpit `block:user` auto-tag

**Inject in the `edit_task` route handler at [mutation.py:163](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L163), AFTER `_build_edit_kwargs()` returns, BEFORE `engine.edit_task()`.**

Tag semantics: `block:user` means "this block was set via the Cockpit transport path" — a best-effort proxy for "user-initiated." No auth layer exists; this is the user's locked design choice ("classification, not enforcement").

**Complete tag lifecycle (all paths):**

| Path | Action | `block:user` effect |
|------|--------|-------------------|
| Cockpit block | `edit_task` route, `kwargs["blocked"] = True` | **Add** `block:user` to `add_tags` |
| Cockpit unblock | `edit_task` route, `kwargs["blocked"] = False` | **Remove** `block:user` via `remove_tags` |
| MCP block | `edit_task` tool, `block="reason"` | **Remove** `block:user` (clears stale Cockpit provenance) |
| MCP unblock | `edit_task` tool, `unblock=True` | **Remove** `block:user` via `remove_tags` |
| MCP `end_work(outcome="block")` | Agent-initiated block | No tag action (agent path, never carries `block:user`) |
| MCP `end_work(outcome=other)` | No block state change | No tag action |

**Cockpit route handler logic** (after `kwargs = _build_edit_kwargs(req, task)`):

```python
if kwargs.get("blocked") is True:
    if "remove_tags" in kwargs:
        kwargs["remove_tags"] = [t for t in kwargs["remove_tags"] if t != "block:user"]
    kwargs.setdefault("add_tags", []).append("block:user")
elif kwargs.get("blocked") is False:
    if "add_tags" in kwargs:
        kwargs["add_tags"] = [t for t in kwargs["add_tags"] if t != "block:user"]
    kwargs.setdefault("remove_tags", []).append("block:user")
```

**MCP `edit_task` tool** — block branch gains tag cleanup:

```python
if block:
    kwargs["blocked"] = True
    kwargs["block_reason"] = block
    kwargs.setdefault("remove_tags", []).append("block:user")  # clear stale provenance
elif unblock:
    kwargs["blocked"] = False
    kwargs.setdefault("remove_tags", []).append("block:user")
```

Engine tag handling is idempotent: `add_tags` deduplicates at [engine.py:642–644](serve/kanban/src/owlbear_kanban/engine.py#L642), `remove_tags` filters silently at [engine.py:645](serve/kanban/src/owlbear_kanban/engine.py#L645). No duplicate-tag risk.

**Inverse on unblock:** Yes, both Cockpit and MCP unblock paths remove `block:user`.

## Structural Reasoning

The design keeps guidance in the MCP boundary layer only. The engine (`serve/kanban/`) is unchanged. The guidance module is a pure function with no side effects — it receives post-mutation state and returns strings. This preserves the clean engine/MCP separation.

The `guidance` field lives on `KanbanTask` (the MCP boundary model), not on `Task` (the engine model). This is the right seam: guidance is a protocol concern, not a domain concern. `KanbanTask` already exists solely to reshape engine output for MCP consumption.

The `block:user` tag is the only cross-layer coordination point: Cockpit route → engine → MCP guidance. The tag is a data-plane marker, not a control-plane mechanism. Agents interpret it; nothing enforces it programmatically.

## Key Trade-offs

1. **`guidance` first in model** — Unconventional field ordering (identity fields usually lead). Justified: this is an MCP boundary model, not a domain model. Salience > convention for an advisory channel.
2. **Pre-read for `move_task`** — One extra file read per call. Sub-millisecond local FS. Same pattern as Cockpit.
3. **MCP `edit_task` block branch gains `remove_tags`** — Slight coupling between MCP tools and the Cockpit tagging convention. Acceptable: both layers are in the same repo, same release cycle.
4. **`end_work(outcome="success")` reminder on every success** — High-frequency guidance. User's explicit V1 choice. Monitor for noise fatigue; remove if it proves unhelpful.

## Warnings

1. **Salience is best-effort.** JSON field order controls token order for the LLM but does not control VS Code's MCP rendering. If future clients restructure tool responses, salience degrades. Hard-validation engine fallback is the documented escape hatch (Brief should note this).
2. **`block:user` is a heuristic, not an assertion.** No auth layer. Any HTTP caller to the Cockpit API gets the tag. The tag means "came through Cockpit," not "performed by a verified human." Document this honestly in skill files.
3. **Brief deliverables must include skill file updates.** At minimum: `h-mcp-kanban` (guidance field docs, `block:user` tag semantics), `r-pipeline-protocol` (updated blocking rules reflecting Cockpit-origin exemption), `w-decision-routing` (reference `block:user`). Without these, the tag is meaningless.
4. **Test case required:** Cockpit block → MCP unblock → MCP re-block → verify `block:user` is absent. This validates the complete provenance lifecycle.
5. **`guidance: []` noise.** The field appears (empty) on all six task-returning tools. `show_task` and `create_task` never populate it. Monitor whether agents surface this as confusing in practice.

## Confidence

**88%.** Strong on Q1–Q3. Q4 lifecycle is complete but depends on accurate skill-file updates and honest documentation of the heuristic's limitations.

Remaining 12%: (a) Salience depends on LLM attention to JSON field order — unverified at scale. (b) `block:user` provenance can still be wrong if a non-agent HTTP client calls the Cockpit API — accepted as a known limitation.
