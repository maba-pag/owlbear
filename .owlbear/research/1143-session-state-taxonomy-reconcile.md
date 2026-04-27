# Reconcile pre-D31 session-state taxonomy in legacy test suites

> **Owning task:** #1143 — Reconcile pre-D31 session-state taxonomy in legacy test suites
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

Brief B (#1044) D31 introduced flat session-state labels (completed, blocked, rejected) replacing the earlier hyphenated labels (completed-pass, completed-fail, completed-rejected). The implementation at `engine.py:192-200` already uses the D31 taxonomy. Two legacy test suites (#923, #952) still assert the old labels and are currently failing (10 failures out of 60 tests).

**Question:** What is the full scope of changes needed to align these suites with D31?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `engine.py:191-213` — `_classify_end_work_state()` and `_classify_end_work_outcome()` | 1.0 — canonical implementation |
| 2 | Brief B paper-integration.md:402 — SessionRecord state/outcome enum | 1.0 — canonical spec |
| 3 | `test_list_sessions.py` (task #923) — 8 failing assertions | 1.0 — primary affected file |
| 4 | `test_list_sessions_952.py` (task #952) — 2 failing assertions | 1.0 — secondary affected file |
| 5 | `test_engine_cockpit_view_1078.py` — already uses D31 labels | 0.8 — confirms correct taxonomy |
| 6 | `test_engine_activity.py` — already uses D31 labels | 0.8 — confirms correct taxonomy |

## 3. Analysis

### State field mismatches (7 assertions across 2 files)

| File | Line | Old (pre-D31) | New (D31) |
|------|------|---------------|-----------|
| test_list_sessions.py | 191 | `completed-pass` | `completed` |
| test_list_sessions.py | 213 | `completed-fail` | `blocked` |
| test_list_sessions.py | 237 | `completed-fail` | `blocked` |
| test_list_sessions.py | 261 | `completed-rejected` | `rejected` |
| test_list_sessions.py | 724 | `completed-pass` | `completed` |
| test_list_sessions.py | 725 | `completed-fail` | `blocked` |
| test_list_sessions_952.py | 234 | `completed-pass` | `completed` |
| test_list_sessions_952.py | 266 | `completed-rejected` | `rejected` |

### Outcome field mismatches (3 assertions in test_list_sessions.py)

Tests assert raw detail strings; implementation returns classified labels per Brief B.

| Line | Old (raw detail) | New (classified) |
|------|------------------|------------------|
| 1204 | `"success: todo -> in-progress"` | `"success"` |
| 1225 | `"outcome=fail"` | `"fail"` |
| 1245 | `"released"` | `"release"` |

### Negative assertions needing label updates (2 in test_list_sessions_952.py)

Lines 249, 281 check `!= "completed-fail"`. Currently pass vacuously but should update to `!= "blocked"` for semantic accuracy under D31.

### Ancillary updates

- Module-level docstrings (both files) reference old labels in AC tables
- Section headers and method docstrings reference old labels
- Error message strings in assertion tuples reference old labels

### AC gap

Task AC mentions lines 191, 213, 237, 261 (state) in test_list_sessions.py and lines 234, 266 in test_list_sessions_952.py. It does **not** mention:

- Lines 724-725 (state, test_list_sessions.py) — 2 additional state assertions
- Lines 1204, 1225, 1245 (outcome, test_list_sessions.py) — 3 outcome assertions
- Lines 249, 281 (negative checks, test_list_sessions_952.py) — semantic drift

**Total: 10 failing tests, not 6.** The builder must address all 10.

## 4. Recommendation

**T1 — Autonomous.** Update test assertions to match the D31 implementation. No code changes to engine.py. Confidence: **0.95**.

Challenge: FALLBACK — trivial label alignment, no recommendation to challenge.

Risk: Near-zero. The engine is the authority; tests must match. Regression suites (test_engine_activity.py, test_engine_cockpit_view_1078.py) already use D31 labels and pass.

## 5. Follow-up Tasks

One follow-up task at `research` status to advance through the pipeline.
