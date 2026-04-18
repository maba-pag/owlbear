# Wire Guidance into `edit_task` + Remove `block:user` on MCP Block

> **Owning task:** #985 — Wire guidance into `edit_task` + remove `block:user` on MCP block
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #985 is a subtask of #973 (Block-Time Guidance from owlbear-kanban MCP). The parent Brief (Path A1) and 9 locked decisions (D1–D9) were approved via a 3-round architect debate. This research validates the implementation path for wiring `collect_guidance` into the MCP `edit_task` tool and adding `block:user` tag removal on block/unblock operations.

Questions: (1) Can `block:user` tag removal be atomic with the block operation? (2) What is the correct guidance attachment pattern? (3) What are the dependency requirements?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L230–289 | Codebase | .95 — `edit_task` function, kwargs building, engine call |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` L575–700 | Codebase | .90 — `edit_task` supports `remove_tags` in same call |
| S3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | .85 — `KanbanTask` model, `_record_to_task` pattern |
| S4 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/decisions.md` D2, D3 | Codebase | .95 — locked decisions for block guidance + `block:user` lifecycle |
| S5 | Parent #973 body — architect review + C1/C3 rebuttals | Codebase | .90 — atomic call confirmed, non-atomicity acceptable |
| S6 | `.owlbear/research/block-time-guidance-mcp-973.md` §3.1 | Codebase | .85 — feasibility validation of all touchpoints |

## 3. Analysis

### 3.1 Atomic Tag Removal (S2, S5)

Engine `edit_task` accepts `blocked`, `block_reason`, and `remove_tags` in a single call. All mutations happen in one read-mutate-write cycle (S2 L642–647). The block branch in server.py can include `remove_tags=["block:user"]` in the same kwargs dict:

```
if block:
    kwargs["blocked"] = True
    kwargs["block_reason"] = block
    kwargs.setdefault("remove_tags", []).append("block:user")
```

`setdefault` handles the case where `remove_tag` param also populates `kwargs["remove_tags"]`. Confirmed by architect rebuttal C3 (S5).

### 3.2 Guidance Attachment Pattern

After the engine call returns, convert to `KanbanTask` via `_record_to_task`, then call `collect_guidance("edit_task", before=None, after=task)` and assign to `task.guidance`. Wrap in try/except per architect guidance note #5 — guidance failures must not break the operation.

| Operation | Guidance Expected | Source |
|-----------|------------------|--------|
| `edit_task(block="reason")` | DR-required message | D2 |
| `edit_task(block="reason")` on task with `block:user` | DR-required message + tag removed | D3 |
| `edit_task(unblock=True)` | Empty (no block guidance) | D2 |
| `edit_task(unblock=True)` on task with `block:user` | Empty + tag removed | D3 |
| `edit_task(title="new")` | Empty | D2 — only block triggers guidance |

### 3.3 Unblock Branch Tag Removal

The AC requires unblock to also remove `block:user`. Same `setdefault` pattern:

```
elif unblock:
    kwargs["blocked"] = False
    kwargs.setdefault("remove_tags", []).append("block:user")
```

### 3.4 Dependency Status

| Dep | Task | Status | Blocks #985? |
|-----|------|--------|-------------|
| #986 | `KanbanTask.guidance` field | research | Yes — field must exist for assignment |
| #987 | `guidance.py` module | research | Yes — `collect_guidance` must exist for import |

Both are in `research` status. Task #985 `depends_on` should be wired to [986, 987] per architect implementation guidance. The task cannot enter `in-progress` until both deps are done.

### 3.5 Confidence Assessment

| Aspect | Confidence | Note |
|--------|-----------|------|
| Atomic tag removal | .95 | Confirmed by engine code and architect rebuttal |
| Guidance attachment | .90 | Standard post-processing; try/except for safety |
| Unblock tag removal | .90 | Same engine pattern |
| Test strategy | .90 | Engine fixture pattern from `test_tool_annotations_494.py` |
| Overall | .90 | |

## 4. Recommendation

Proceed with implementation. No ambiguity — all decisions locked (D2, D3), engine supports atomic operations, and the implementation is ~15 lines of changes to `edit_task` plus a new import. Wire `depends_on` to [986, 987] before advancing.

Confidence: .90

Challenge: SKIPPED — approach locked via parent Brief, no new recommendation needed.

## 5. Follow-up Tasks

No new follow-up tasks needed — #985 is already an atomic implementation task with clear AC. Dependencies #986 and #987 exist. Wired `depends_on` field during this research.
