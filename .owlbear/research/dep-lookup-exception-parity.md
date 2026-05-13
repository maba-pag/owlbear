# Dep-Lookup Exception Tuple Parity — Consolidation Test

> **Owning task:** #1530 — P3-01: consolidation test — dep-lookup exception tuple parity (AC5)
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

`agent_view.py` has two dep-iteration loops — one in `show_task()` (L248–251) and one in `start_work()` (L993–997). Both silently catch the same exception tuple to skip unresolvable dependencies. No shared constant exists, so the tuples can drift independently. The task asks: can we write a consolidation test that prevents this drift via AST inspection?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/agent_view.py` L248–251 | Codebase | 1.0 — show_task dep-iteration site |
| 2 | `serve/kanban/src/owlbear_kanban/agent_view.py` L993–997 | Codebase | 1.0 — start_work dep-iteration site |
| 3 | `tests/test_consolidate_helpers.py` | Codebase | 0.9 — established pattern for AST-based consolidation tests |
| 4 | Python `ast` module (stdlib) | Documentation | 0.8 — ExceptHandler node structure |

## 3. Analysis

### Current State

Both sites use identical tuples:

```python
except (FileNotFoundError, CorruptionError, ValueError, KeyError):
    continue
```

A third site in `engine.py` L2321 (`_is_stale_session`) uses the same tuple but is out of scope — it's a different domain concern (session cleanup vs dep resolution).

### AST Extraction Approach

The `test_consolidate_helpers.py` pattern parses source with `ast.parse()` and walks the tree. For exception tuple parity, the test would:

1. Parse `agent_view.py` source
2. Locate `AgentView.show_task()` and `AgentView.start_work()` method nodes
3. Within each, find `ExceptHandler` nodes whose exception names include `CorruptionError` (discriminator — only the dep-iteration handler catches this)
4. Extract the set of exception names from each handler's tuple
5. Assert the two sets are equal

**Discriminator rationale:** `show_task()` has a second try/except (`except FileNotFoundError as exc`) for the main task lookup. Filtering for handlers that include `CorruptionError` isolates the dep-iteration handler.

### Alternative: Source Text Regex

Simpler but brittle — regex over `inspect.getsource()` would break on reformatting. AST approach is more robust and consistent with the established pattern. No real trade-off here.

## 4. Recommendation (confidence: 0.92)

Use the AST-inspection approach following the `test_consolidate_helpers.py` pattern. Place the test in `serve/kanban/tests/` as a consolidation test file. The test is ~30 LOC, no design decisions required.

**Challenge:** SKIPPED — trivial research, no contested recommendation (single viable approach).

### Tier Classification

| Finding | Tier | Action |
|---------|------|--------|
| AST parity test is feasible and follows existing patterns | T1 — Autonomous | Task #1530 already exists; advance to backlog |

## 5. Follow-up Tasks

No new tasks needed. Task #1530 itself is the actionable follow-up — advancing it to backlog enables test-writer pickup.
