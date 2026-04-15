# Archive Redundant Content Safety Tasks

> **Owning task:** #835 — Cleanup: archive redundant content safety tasks (#768, #786)
> **Date:** 2026-04-13 **Status:** Complete

## 1. Context and Question

Three content safety tasks in the #751 tree describe work already implemented and tested. Can they be safely archived without losing coverage?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| #768 task body | kanban (done) | .95 — full pipeline pass-through, AC1+AC2 redundant per own research |
| #786 task body | kanban (done) | .95 — predicate inversion already shipped |
| #781 task body | kanban (review, blocked) | .90 — same predicate inversion, stuck at review |
| `content_safety.py` | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | .95 — `_TRUSTED_SOURCE_TYPES`, `should_wrap()` |
| `content_guard.py` | `serve/knowledge/src/owlbear_knowledge/content_guard.py` | .90 — IDPI guard implemented |
| `ingest.py:207-235` | `serve/knowledge/src/owlbear_knowledge/ingest.py` | .90 — wrapping + guard integration |
| Git commit `2dfae28b` | `feat: authenticated content pipeline Phase 1` | .90 — ships wrapping + predicate |
| 6 test files | `tests/test_content_safety_*.py`, `test_authenticated_content_pipeline_*.py`, `test_content_guard_*.py` | .95 — 141 tests, all passing |
| #833, #834 task bodies | kanban (done) | .85 — IDPI guard follow-ups both completed |

## 3. Analysis

### Redundancy Verification

| Task | Status | Describes | Covered By | Evidence | Archive? |
|------|--------|-----------|------------|----------|----------|
| #768 | done | RED tests: AC1 wrapping, AC2 predicate, AC3 IDPI | AC1+AC2: 21 tests (751/775/786 files). AC3: #833+#834 (done) | Own research doc + pipeline pass-through | **Yes** |
| #786 | done | Predicate inversion (`== "url"` → `not in (...)`) | `content_safety.py:23` + 12 tests in `test_content_safety_inversion_775.py` | Commit `2dfae28b`, stale dep on #781 | **Yes** |
| #781 | review (blocked) | Tests for predicate inversion | Same 12 tests + 3 in `test_content_safety_inversion_786.py` | Blocked by QR env error; 141 tests pass now | **Yes** (new finding) |

### Test Coverage Confirmation

```
uv run pytest tests/test_content_safety_inversion_775.py
    tests/test_authenticated_content_pipeline_751.py
    tests/test_authenticated_content_pipeline_775.py
    tests/test_content_safety_inversion_786.py
    tests/test_content_guard_833.py tests/test_content_guard_834.py
→ 141 passed, 0 failed
```

All content safety behavior is verified by existing test suites independent of these three tasks.

### Stale Dependency Chain

#786 → depends_on #781 → blocked at review. Neither task delivers new value. The dependency was never enforced (#786 reached `done` regardless).

## 4. Recommendation (confidence: .95)

Archive all three tasks. No coverage loss — all described behavior is implemented, tested (141 passing tests), and shipped via commit `2dfae28b` + #833/#834.

- T1 (autonomous cleanup): no architectural, security, or behavioral changes.
- Challenge: N/A — trivial cleanup, no recommendation to challenge.

## 5. Follow-up Tasks

The archival of #768, #786, and #781 is the deliverable of task #835 itself (builder stage). No additional follow-up tasks needed beyond advancing #835.

**Additional finding:** #781 (not in original AC) should be included in the archival scope.
