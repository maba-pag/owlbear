# Content Safety Wrapping — Implementation Status

> **Owning task:** #769 — P1-16: Impl — Content safety wrapping
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #769 is a GREEN-phase task for content safety wrapping with three objectives:
1. Content safety predicate inverted to wrap-by-default
2. AUTHENTICATED_WEB content wrapped automatically
3. IDPI scan integration point

**Core question:** Is there any remaining work for this task, given that the #751 builder already implemented the wrapping features?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `content_safety.py` | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | .95 — `should_wrap()` deny-list predicate + `wrap_untrusted_content()` fully implemented |
| `ingest.py` | `serve/knowledge/src/owlbear_knowledge/ingest.py:188-195` | .95 — wrapping integration uses `should_wrap()`, old `_is_url` removed |
| #751 builder notes | Parent task body — commit `2dfae28b` | .90 — confirms wrapping predicate change shipped |
| #768 research doc | `.owlbear/research/768-content-safety-idpi-wrapping.md` | .90 — AC1+AC2 declared redundant, IDPI carved to #833/#834 |
| Test suites (3 files) | `test_content_safety_735.py`, `test_content_safety_inversion_775.py`, `test_authenticated_content_pipeline_751.py` | .90 — 27+42 existing tests, all passing |
| Task #786 | Kanban — "Content safety predicate inversion" | .85 — describes identical work to what's already done |

## 3. Analysis

### 3a. Implementation State Assessment

| #769 Objective | Code Evidence | Test Coverage | Status |
|----------------|--------------|---------------|--------|
| Predicate inverted (wrap-by-default) | `content_safety.py:23` — `_TRUSTED_SOURCE_TYPES = frozenset({"file", "file_glob", "text"})`, `should_wrap()` returns True for all others | 11 tests in `test_content_safety_inversion_775.py` — all pass | **DONE** |
| AUTHENTICATED_WEB wrapped | `ingest.py:188` — `_should_wrap = should_wrap(...)` covers all untrusted types | 7 tests in `test_authenticated_content_pipeline_751.py` | **DONE** |
| IDPI scan integration | No `content_guard.py` exists anywhere | 0 tests | **NOT DONE — carved to #833/#834** |

### 3b. Duplicate Task Detection

| Task | Describes | Covered By | Recommendation |
|------|-----------|------------|----------------|
| #769 (this task) | Predicate inversion + AUTHENTICATED_WEB wrapping + IDPI | #751 builder (wrapping), #833/#834 (IDPI) | **Advance as-is** — no new work needed |
| #786 | `content_safety.py` predicate from `== "url"` to `not in (...)` | Already done in `content_safety.py` | **Redundant — recommend archive** |
| #768 | RED tests for AC1 (wrapping) + AC2 (predicate) + AC3 (IDPI) | AC1+AC2 redundant per its own research; AC3 carved to #833 | **Recommend archive** — fully superseded |

### 3c. Dependency Orphan

Task #786 depends on #781, which no longer exists on the board (deleted or archived). This is a stale dependency on a redundant task.

## 4. Recommendation (.90 confidence)

**#769 has no remaining implementation work.** All three wrapping objectives are either already implemented (predicate inversion, AUTHENTICATED_WEB) or properly carved out (IDPI → #833/#834). Advance directly.

**Two redundant tasks should be flagged for cleanup:**
- **#786** — exact duplicate of implemented predicate inversion, stale dep on deleted #781
- **#768** — fully superseded by its own research + follow-up tasks #833/#834

Challenge: FALLBACK — challenger subagent not available

## 5. Follow-up Tasks

- **#835** — Cleanup: archive redundant content safety tasks (#768, #786)
