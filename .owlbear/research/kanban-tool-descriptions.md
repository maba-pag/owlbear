# Enrich KanbanToolset Tool Descriptions

> **Owning task:** #773 — Enrich KanbanToolset tool descriptions with valid statuses/priorities
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

KanbanToolset registers 7 tools with terse descriptions (e.g., "Create a new
kanban task"). Models using these tools must guess valid statuses and priorities,
leading to errors (e.g., `kanban_move 42 wip` instead of `in-progress`). Parent
research (#718, `docs/research/cheat-sheet-tool.md`) recommended enriching inline
descriptions as the KISS option (~50 LOC of string edits, 0 new deps).

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | .75 — `add_function(description=)` is the API |
| 2 | PydanticAI Tools docs | <https://ai.pydantic.dev/tools/> | .70 — Schema extraction from docstrings |
| 3 | OwlBear `browser_snapshot` | `src/owlbear/tools/browser/toolset.py` L178-186 | .95 — Internal precedent for enriched description |
| 4 | OwlBear `KnowledgeSourceToolset` | `src/owlbear/tools/knowledge_source.py` L74-97 | .90 — Internal precedent listing valid enum values |
| 5 | OwlBear `kanban/config.yml` | `kanban/config.yml` | 1.0 — Authoritative source of valid values |

## 3. Analysis

### 3.1 What Needs Enrichment

| Tool | Current description | Gap | Proposed addition |
|------|--------------------|----|-------------------|
| `kanban_create` | "Create a new kanban task." | No valid priorities | Add: priorities list, default status |
| `kanban_move` | "Move a kanban task to a new status." | No valid statuses | Add: full status pipeline |
| `kanban_edit` | "Edit a kanban task's properties." | No field summary | Add: editable fields list |
| `kanban_list` | "List kanban tasks with optional filters." | No filter hint | Add: mention status/tag/priority/blocked filters |
| `kanban_pick` | "Pick the next task from the board." | No claim/move hint | Add: mention --claim and --move options |

### 3.2 Token Cost Estimate

Current total: ~50 tokens across 7 descriptions.
Proposed total: ~150 tokens (+100 tokens, ~2% of a typical tool list).
This matches the `browser_snapshot` pattern which uses ~60 tokens alone.

### 3.3 Approach: Static Strings vs Dynamic (PreparedToolset)

| Criterion | Static strings (.90) | PreparedToolset (.55) |
|-----------|----------------------|----------------------|
| LOC changed | ~30 (string edits only) | ~80 (new wrapper class) |
| Runtime cost | Zero | Per-step function call |
| Config drift risk | Low (values change rarely) | Zero (reads config) |
| KISS | Best | Over-engineering |
| Testability | Assert on description string | Need fixture for toolset prep |

**Static strings win.** The valid statuses/priorities are defined in
`kanban/config.yml` and have been stable since project inception. If they ever
change, the same commit updates the description strings — a 1-line diff.

## 4. Recommendation (.90 confidence)

Enrich 5 of the 7 `add_function` description strings in
`KanbanToolset._register_tools()` with valid values from `kanban/config.yml`.
Leave `kanban_show` and `kanban_context` as-is (no enum parameters).

Pattern to follow: `browser_snapshot` multi-line description (toolset.py L178-186).

**Scope:** ~30 LOC of string changes in `src/owlbear/tools/kanban.py`.
No new files, no new deps, no interface changes.

## 5. Follow-up Tasks

Task #773 itself is the implementation task. No additional follow-up tasks
needed — the work is a single atomic change to description strings.

**AC for builder:**

- `kanban_create` description includes valid priorities (someday, nice-to-have,
  important, needed, critical) and default status (ideation)
- `kanban_move` description includes valid statuses (ideation, backlog, todo,
  in-progress, review, docs, done)
- `kanban_edit` description lists editable fields (body, block/unblock, tags,
  priority, append_body)
- `kanban_list` description mentions available filters
- `kanban_pick` description mentions --claim and --move semantics
- Existing tests still pass (no behavioral change)
