# Wire Guidance into `end_work` + Remove `block:user` on MCP Block

> **Owning task:** #989 — Wire guidance into `end_work` + remove `block:user` on MCP block
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #989 is a subtask of #973 (Block-Time Guidance from owlbear-kanban MCP). All decisions locked in Brief (D1–D9) via 3-round architect debate. This research validates the implementation path for wiring `collect_guidance` into the MCP `end_work` tool and removing `block:user` tags on block outcomes.

Questions: (1) Can `block:user` tag removal be done within `end_work`? (2) What is the correct call sequence given engine constraints? (3) Which outcomes produce guidance?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L302–333 | Codebase | .95 — `end_work` handler, engine call, return pattern |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` L871–940 | Codebase | .95 — engine `end_work` signature: no `remove_tags` param |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L575–620 | Codebase | .90 — engine `edit_task` accepts `remove_tags`, no claim required |
| S4 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/decisions.md` D2, D3 | Codebase | .95 — locked decisions for block guidance + `block:user` lifecycle |
| S5 | Parent #973 body — architect review, C1 rebuttal | Codebase | .90 — sequential calls confirmed, non-atomicity accepted |
| S6 | `.owlbear/research/edit-task-guidance-985.md` | Codebase | .85 — sibling task established guidance wiring pattern |

## 3. Analysis

### 3.1 Non-Atomic Tag Removal (S2, S3, S5)

Engine `end_work` does NOT accept `remove_tags` — its params are `task_id, note, outcome, block_reason, move_to`. Engine `edit_task` DOES accept `remove_tags` and does NOT require a claim. After `engine.end_work()` releases the claim, `engine.edit_task(task_id, remove_tags=["block:user"])` is a valid sequential call (architect rebuttal C1, S5).

Sequence for `outcome == "block"`:

```
record = engine.end_work(task_id, note=note, outcome="block", block_reason=block_reason)
record = engine.edit_task(task_id, remove_tags=["block:user"])  # idempotent if tag absent
task = _record_to_task(record)
task.guidance = collect_guidance("end_work", before=None, after=task, outcome="block")
```

Engine `remove_tags` filters silently when tag absent (S3 L642–645). No conditional check needed.

Both engine calls must use `asyncio.to_thread` — they are sync methods called from an async handler.

### 3.2 Guidance per Outcome

| Outcome | `collect_guidance` call | Expected guidance | Tag action | Source |
|---------|------------------------|-------------------|------------|--------|
| `block` | `("end_work", None, task, outcome="block")` | DR-required message | Remove `block:user` | D2, D3 |
| `success` | `("end_work", None, task, outcome="success")` | Commit-pushed reminder | None | D2 |
| `fail` | `("end_work", None, task, outcome="fail")` | Empty `[]` | None | AC |
| `reject` | `("end_work", None, task, outcome="reject")` | Empty `[]` | None | AC |

The guidance module (#987) determines which operations produce messages. The `end_work` handler passes `outcome` as a kwarg to `collect_guidance`.

### 3.3 Guidance Attachment Pattern (S6)

Same pattern as sibling #985:

1. After engine call, convert to `KanbanTask` via `_record_to_task(record)`.
2. Call `collect_guidance("end_work", before=None, after=task, outcome=outcome)`.
3. Assign to `task.guidance`.
4. Wrap guidance call in try/except per architect note #5 — guidance failures must not break operations.

`before=None` because `end_work` modifies the task in-place; there is no meaningful "before" state to compare.

### 3.4 Difference from `edit_task` (#985)

| Aspect | `edit_task` (#985) | `end_work` (#989) |
|--------|-------------------|-------------------|
| Tag removal | Atomic — single `engine.edit_task()` call | Sequential — `engine.end_work()` then `engine.edit_task()` |
| Claim state | Task stays claimed | Claim released by `end_work` |
| `asyncio.to_thread` | One call | Two calls (block path) |
| Outcomes | Block/unblock only | 4 outcomes, only block needs tag removal |

### 3.5 Dependency Status

| Dep | Task | Status | Required by #989 |
|-----|------|--------|-----------------|
| #986 | `KanbanTask.guidance` field | research (claimed) | Yes — field must exist for `task.guidance = ...` |
| #987 | `guidance.py` module | research (claimed) | Yes — `collect_guidance` must exist for import |

Both are claimed and in research. `depends_on` must be wired to [986, 987] before #989 enters in-progress.

### 3.6 Test Strategy

Integration tests per outcome using engine fixture pattern from `test_tool_annotations_494.py`:

1. `test_end_work_block_returns_dr_guidance` — block outcome produces DR message
2. `test_end_work_block_removes_block_user_tag` — block on tagged task removes `block:user`
3. `test_end_work_success_returns_commit_guidance` — success produces commit reminder
4. `test_end_work_fail_returns_empty_guidance` — fail produces empty list
5. `test_end_work_reject_returns_empty_guidance` — reject produces empty list

### 3.7 Confidence Assessment

| Aspect | Confidence | Note |
|--------|-----------|------|
| Sequential tag removal | .90 | Architect C1 rebuttal confirmed; non-atomicity accepted |
| Guidance attachment | .95 | Identical pattern to #985, established in codebase |
| Outcome routing | .95 | Four cases clearly defined in AC and guidance module spec |
| Test strategy | .90 | Engine fixture pattern proven in existing tests |
| Overall | .90 | |

## 4. Recommendation

Proceed with implementation per Brief Path A1 and locked decisions D2, D3. Implementation is ~20 lines of changes to `end_work` handler (import, tag removal branch, guidance attachment with try/except). Wire `depends_on` to [986, 987] before advancing.

Confidence: .90

Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions.

## 5. Follow-up Tasks

No new follow-up tasks — #989 is already atomic with clear AC. Dependencies #986 and #987 exist. Wiring `depends_on` during this research.
