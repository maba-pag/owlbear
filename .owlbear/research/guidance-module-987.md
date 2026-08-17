# Create `guidance.py` Module with 3 V1 Rules

> **Owning task:** #987 — Create `guidance.py` module with 3 V1 rules
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Parent task #973 (Block-Time Guidance from owlbear-kanban MCP) was decomposed into atomic subtasks after a 3-round architect debate that locked 9 decisions (D1–D9). Task #987 implements the core guidance computation module: a flat rule registry with `collect_guidance()` function and 3 V1 rules.

Questions: (1) What pattern handles both static and dynamic messages in a flat tuple registry? (2) How does forward-skip detection work given `status_names` kwarg? (3) What edge cases need test coverage?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | .95 — `KanbanTask` fields: `blocked`, `tags`, `status` |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L360 | Codebase | .85 — `_STATUSES` list (7 statuses, no archived) |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L295–297 | Codebase | .90 — `_status_rank` pattern: `{s["name"]: i for i, s in enumerate(config.statuses)}` |
| S4 | `.owlbear/research/block-time-guidance-mcp-973.md` | Codebase | .95 — parent feasibility, all touchpoints validated |
| S5 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/` | Codebase | .95 — Brief decisions D2 (block DR), D5 (guidance module), D6 (forward-skip) |
| S6 | `.owlbear/research/edit-task-guidance-985.md` | Codebase | .85 — wiring pattern and `block:user` tag lifecycle |

## 3. Analysis

### 3.1 Rule Registry Pattern

The AC requires `(predicate, message_template)` tuples. Rules 1 and 3 have fixed messages; rule 2 needs a dynamic message (mentions old/new status). Two patterns compared:

| Pattern | Complexity | Extensibility | KISS |
|---------|-----------|---------------|------|
| A: `tuple[Callable→bool, str]` — static only | Low | Fails for dynamic messages | ✓ but incomplete |
| B: `tuple[Callable→bool, str \| Callable→str]` — mixed | Low | Handles both; `callable()` check in iterator | ✓ |
| C: `tuple[Callable→bool, Callable→str]` — all callable | Low | Uniform; lambdas for static messages | Slightly over-abstracted |

**Recommendation: Pattern B** (.85 confidence). The iterator checks `callable(msg)` — 1 line. Static messages stay as plain strings (readable). Dynamic messages are functions. Adding a fourth rule = appending one tuple regardless.

```python
_RULES: list[tuple[_Predicate, str | _MessageFn]] = [
    (_is_block_needing_dr, _BLOCK_DR_MSG),  # static str
    (_is_forward_skip, _forward_skip_message),  # callable
    (_is_success_outcome, _SUCCESS_COMMIT_MSG),  # static str
]
```

### 3.2 Forward-Skip Detection

The AC specifies `status_names: list[str]` from kwargs (caller extracts from `board_config().statuses`). The predicate:

1. Guard: `operation != "move"` or `before is None` → skip.
2. Extract `status_names` from kwargs. If missing → skip (defensive).
3. Look up `before.status` and `after.status` indices in `status_names`.
4. If either status not found → skip (unknown status, don't emit spurious guidance).
5. If `after_index - before_index > 1` → emit guidance.

Excludes archived by design: `status_names` from `board_config().statuses` never includes archived (archived is a separate dir, not a status column).

Edge case: backward moves (e.g. review → todo) should NOT trigger forward-skip. The predicate checks `after_index > before_index` AND `after_index - before_index > 1`.

Dynamic message: `"⚠️ Unusual status skip: {before.status} → {after.status} (skipped {N} columns). Verify this is intentional."`

### 3.3 Block DR Rule with `block:user` Exemption

Predicate: `after.blocked is True` AND `"block:user" not in after.tags`.

Key: the `block:user` tag check is on `after` (post-mutation state). When the Cockpit blocks a task, it adds `block:user` before the MCP call. When an agent blocks via `end_work(outcome="block")`, no `block:user` tag exists → guidance fires.

Note: the AC says `after.blocked is True` — use identity check (`is True`) not truthiness, since `blocked` is `bool` field.

### 3.4 Success/Commit Rule

Predicate: `operation == "end_work"` AND `kwargs.get("outcome") == "success"`.

Fixed message from AC: "Reminder: verify your changes are committed and pushed before this task advances."

### 3.5 Dependency Analysis

| Dependency | Status | Impact on #987 |
|------------|--------|----------------|
| #986 (add `guidance` field to `KanbanTask`) | todo | **None** — `collect_guidance()` returns `list[str]`; the caller assigns to `task.guidance`. Module only imports `KanbanTask` for type annotations. |

The module can be developed and tested independently of #986.

### 3.6 Test Strategy

Unit tests with constructed `KanbanTask` instances (no engine, no MCP server):

| Rule | Positive case | Negative case(s) |
|------|--------------|-------------------|
| Block DR | `blocked=True`, no `block:user` tag → message emitted | `blocked=False` → empty; `blocked=True` + `block:user` tag → empty |
| Forward-skip | `move` from `research` to `in-progress` (skip 2) → message | `move` from `todo` to `in-progress` (skip 0) → empty; non-move op → empty |
| Success/commit | `end_work` + `outcome="success"` → message | `end_work` + `outcome="fail"` → empty; `edit_task` + `outcome="success"` → empty |

Additional edge cases: `before=None` for forward-skip (should not crash), unknown status names.

## 4. Recommendation

Proceed with implementation per AC. Pattern B (mixed static/callable messages) is the simplest pattern that handles all 3 rules. No architectural decisions needed — all locked by parent Brief D5, D6.

Confidence: .90

Challenge: SKIPPED — approach locked via parent #973 architect debate (9 decisions). No new recommendation to challenge.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #987 itself moves to backlog for implementation. Sibling tasks (#985, #989, #991) handle wiring into server.py tools.
