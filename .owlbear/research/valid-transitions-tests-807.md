# Tests — valid_transitions

> **Owning task:** #807 — Tests — valid_transitions
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #807 is the RED-phase test task for `valid_transitions(status)` on `KanbanEngine`.
Paired with #808 (GREEN implementation). Both are Phase 1, parent #798.

**Key finding:** The implementation already exists in `serve/kanban/src/owlbear_kanban/engine.py` (L113–L129).
Tests will pass GREEN immediately — the RED phase cannot be achieved. The test-writer
should write tests that *would* fail without the implementation, then document the
GREEN-on-arrival situation.

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L113–129 | 1.0 | Implementation: returns `{all} - {status}`, raises `ValueError` for invalid |
| 2 | `serve/kanban/src/owlbear_kanban/models.py` L43–54 | 0.9 | `BoardConfig.statuses` is `list[dict[str, Any]]`; names via `s["name"]` |
| 3 | `tests/test_refresh_config_803.py` | 0.9 | Fixture patterns: `_BASE_CONFIG_YAML`, `kanban_dir`, `engine` fixtures |
| 4 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` L40 | 0.8 | Design: "Returns all configured statuses except current" |

## 3. Analysis

### AC-to-Test Mapping

| AC | Test cases | Notes |
|----|-----------|-------|
| AC1: returns set of all statuses except given | Test first status ("research") returns 6 others; test last status ("done") returns 6 others; test middle status ("in-progress"); verify return type is `set` | Use default 7-status config from existing fixture pattern |
| AC2: invalid status raises ValueError | Unknown string ("nonexistent"); empty string ("") | Both should raise `ValueError` with descriptive message |
| AC3: transitions match config-defined statuses | Result is always subset of configured statuses; test with custom config (fewer statuses) to verify dynamic behavior | Ensures no hardcoding — transitions derive from config |
| AC4: tests fail RED | Implementation already exists — tests will be GREEN on arrival | Document in test file header; not a blocker |

### Edge Cases

| Case | Expected | Priority |
|------|----------|----------|
| Hyphenated status ("in-progress") | Works — string matching, no special handling | Include |
| All 7 statuses individually | Each returns exactly 6 others | Good parametric test |
| Custom config with 2 statuses | Returns exactly 1 other | Proves config-driven behavior |

### Testing Strategy

- **File:** `tests/test_valid_transitions_807.py`
- **Fixtures:** Reuse `_BASE_CONFIG_YAML` pattern from `test_refresh_config_803.py` (local to file, not shared)
- **Structure:** Single `TestFromAC_ValidTransitions` class, parametrized where appropriate
- **Pattern:** `pytest.raises(ValueError, match=...)` for error cases
- **Parametrize:** All 7 statuses for AC1 coverage; invalid inputs for AC2

### Implementation Timing Concern

The `valid_transitions()` method already exists. Standard TDD RED requires tests to fail
before implementation. Two options:

| Option | Trade-off |
|--------|-----------|
| A: Write tests, accept GREEN-on-arrival | Pragmatic — tests still verify correctness. Note in test header. |
| B: Temporarily remove implementation, verify RED, restore | Artificial — adds git noise, no real value |

**Recommendation:** Option A (confidence: 0.90). The tests verify the correct behavior
regardless of arrival order. Note the situation in the test file docstring.

Challenge: FALLBACK — trivial T1 test task, no architectural trade-offs to challenge.

## 4. Recommendation

Write `tests/test_valid_transitions_807.py` following existing fixture patterns from
`test_refresh_config_803.py`. Use parametrized tests for all 7 statuses (AC1/AC3) and
error cases (AC2). Accept GREEN-on-arrival and document it.

Confidence: 0.90.

## 5. Follow-up Tasks

- Task #808 already exists (GREEN implementation) — depends on #807, no new task needed.
- No decision requests required (T1 — standard test task).
