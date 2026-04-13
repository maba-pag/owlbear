# Add board_config() — Implementation Research (#806)

> **Owning task:** #806 — Add board_config()
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #806 requires the `board_config()` method on `KanbanEngine` to return a **defensive copy** of the cached `BoardConfig`. The method already exists at `engine.py` L92-98 and returns `self._config.model_copy()` (shallow). The question: does the current implementation satisfy the AC, and if not, what is the minimal fix?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | Pydantic v2 docs — Models: `model_copy()` | 1.0 | "returns a copy (by default, shallow copy)" — confirms default is shallow |
| 2 | `.owlbear/research/board-config-tests-805.md` | 1.0 | Empirical verification: `copy.statuses is original.statuses` → `True` with shallow copy |
| 3 | `models.py` L39-57 — `BoardConfig` schema | 1.0 | `statuses: list[dict[str, Any]]`, `priorities: list[str]` — nested mutable types |
| 4 | `engine.py` L92-98 — current implementation | 1.0 | Returns `self._config.model_copy()` without `deep=True` |
| 5 | `test_config_staleness_fix_828.py` — existing integration | 0.9 | Confirms `board_config()` is already exercised; fixture pattern available |

## 3. Analysis

### Current state vs AC

| AC | Current behavior | Meets AC? |
|----|-----------------|:-:|
| `board_config()` method on `KanbanEngine` | Exists at L92 | YES |
| Returns `model_copy()` of cached config | Returns `self._config.model_copy()` | YES |
| Returned object is defensive copy — mutation doesn't affect engine | Shallow copy: nested lists share refs → mutation leaks | **NO** |
| #805 tests pass GREEN | Tests not yet written (#805 at `todo`) | BLOCKED |
| Existing MCP tests pass | No behavioral change expected | YES (expected) |

### Fix options

| Option | Change | Pros | Cons | Confidence |
|--------|--------|------|------|:----------:|
| A: `model_copy(deep=True)` | Add `deep=True` param at L98 | One-line fix; Pydantic-native; fully isolates nested types | Marginally slower (deep copy) — negligible for config-sized objects | **.95** |
| B: Manual deepcopy | `import copy; copy.deepcopy(self._config)` | Works without Pydantic | Bypasses Pydantic internals; not idiomatic | .60 |
| C: Reconstruct from dump | `BoardConfig.model_validate(self._config.model_dump())` | Re-validates | Wasteful round-trip; slower than deep copy | .50 |

**Recommendation: Option A** — `model_copy(deep=True)`. KISS, idiomatic Pydantic, minimal diff.

### Implementation

```python
# engine.py L98 — change:
return self._config.model_copy()
# to:
return self._config.model_copy(deep=True)
```

No new imports. No new methods. No interface changes. The docstring already promises defensive copy semantics — the fix makes the implementation match the contract.

## 4. Recommendation

**Option A: `model_copy(deep=True)`** — confidence: **0.95**

T1 — Autonomous. Bug fix: shallow copy → deep copy. No new capability, no architecture change, no security implications.

Challenge: FALLBACK — trivial T1 fix with empirical verification from #805 research; challenger not invoked.

## 5. Follow-up Tasks

None needed. The task chain is already defined:
- #805 (RED tests) → currently at `todo`
- #806 (GREEN implementation) → this task
