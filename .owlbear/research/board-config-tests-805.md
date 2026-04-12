# Tests — board_config (#805)

> **Owning task:** #805 — Tests — board_config
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #805 requires tests for `KanbanEngine.board_config()` covering three behaviors: statuses content/order, priorities content/order, and defensive copy isolation. The method already exists at [engine.py](serve/kanban/src/owlbear_kanban/engine.py#L92) and returns `self._config.model_copy()`.

**Key question:** Will these tests be RED (failing) per the AC, given the implementation exists?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `engine.py` L92-98 — `board_config()` implementation | 1.0 | Returns `self._config.model_copy()` (no `deep=True`) |
| 2 | `models.py` L39-57 — `BoardConfig` schema | 1.0 | `statuses: list[dict[str, Any]]`, `priorities: list[str]`, `extra='allow'` |
| 3 | Pydantic v2 `model_copy()` behavior (verified empirically) | 1.0 | Shallow copy: nested lists/dicts share references with original |
| 4 | `test_config_staleness_fix_828.py` — existing tests | 0.9 | Fixture pattern: `_BASE_CONFIG_YAML`, `kanban_dir`, `engine` fixtures |
| 5 | Brief: `draft-kanban-web-gui-prep/voices/architect.md` L91 | 0.8 | Design intent: "defensive copy preventing consumers from mutating engine state" |

## 3. Analysis

### Empirical verification of `model_copy()`

Ran verification in the workspace. Results:

| Operation | `model_copy()` | `model_copy(deep=True)` |
|-----------|:-:|:-:|
| `copy.statuses is original.statuses` | `True` (shared) | `False` (isolated) |
| `copy.priorities is original.priorities` | `True` (shared) | `False` (isolated) |
| `copy.statuses[0] is original.statuses[0]` | `True` (shared) | `False` (isolated) |
| Append to copy's `priorities` leaks to original | **Yes** | No |

### AC-to-test mapping and RED/GREEN prediction

| AC | Test approach | Predicted outcome |
|----|---------------|:-:|
| AC1 — statuses content and order | Assert `board_config().statuses` matches YAML-defined list | GREEN (works) |
| AC2 — priorities content and order | Assert `board_config().priorities` matches YAML-defined list | GREEN (works) |
| AC3 — defensive copy isolation | Mutate returned config, assert engine state unchanged | **RED** (shallow copy leaks) |

### Test design

Reuse fixture pattern from `test_config_staleness_fix_828.py`: standalone `_BASE_CONFIG_YAML`, `kanban_dir` fixture, `engine` fixture.

Recommended test cases:

1. `test_board_config_returns_all_statuses_in_display_order` — compare returned statuses list element-by-element against YAML definition.
2. `test_board_config_returns_all_priorities_in_display_order` — compare returned priorities list against YAML definition.
3. `test_board_config_mutation_does_not_affect_engine_statuses` — append to returned `statuses`, verify engine's config unchanged.
4. `test_board_config_mutation_does_not_affect_engine_priorities` — append to returned `priorities`, verify engine's config unchanged.
5. `test_board_config_nested_dict_mutation_does_not_affect_engine` — mutate a `statuses[0]` dict, verify engine's config unchanged.

Tests 3-5 will fail RED until the implementation is fixed to use `model_copy(deep=True)`.

## 4. Recommendation

**T1 — Autonomous.** Straightforward test writing with a known fix path.

The test-writer should write all 5 tests. Tests 1-2 pass immediately (GREEN). Tests 3-5 fail (RED) and expose the shallow-copy defect. The implementation fix is a one-character change: `model_copy()` → `model_copy(deep=True)` in `engine.py` L98.

**Confidence: 0.95** — empirically verified, no ambiguity in behavior.

Challenge: FALLBACK — trivial T1 finding with empirical verification; challenger not invoked.

## 5. Follow-up Tasks

- Test-writer task for `test_board_config_805.py` covering all 5 test cases (AC1-AC3).
- Implementation task: fix `board_config()` to use `model_copy(deep=True)`.
