# list_sessions() GREEN Implementation Research

> **Owning task:** #926 — P1-02: GREEN — list_sessions() engine helper implementation
> **Date:** 2026-04-18  **Status:** Complete

## 1. Context and Question

Task #926 calls for implementing `list_sessions()` on `KanbanEngine` to pass the RED tests from #923. Investigation reveals the implementation already exists (helpers + public method + model) and all 23 tests pass. However, three gaps exist between the implementation and the AC, plus a critical format mismatch that will cause incorrect session classification with real production data.

Questions: (a) what gaps remain between implementation and AC? (b) is the `end_work` detail format compatible with `_classify_end_work()`? (c) what follow-up work is needed?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L46–130 | .95 | WorkSession dataclass (2 fields), helper functions, public method |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L898–915 | .95 | `end_work()` detail format: unprefixed `"{old} -> {new}"` |
| 3 | `serve/kanban/tests/test_list_sessions.py` | .95 | 23 tests, all pass; write JSONL directly with prefixed format |
| 4 | `.owlbear/kanban/activity.jsonl` (tail 200) | .90 | 11387 entries; zero `end_work` actions; all closures via release+move |
| 5 | `.owlbear/briefs/draft-cockpit/brief.md` D10 | .90 | Session spec: one row per claim cycle, derived from activity.jsonl |
| 6 | `.owlbear/research/923-list-sessions-tests.md` F1 | .85 | Identified success/reject ambiguity; recommended detail prefix (Option B) |
| 7 | `serve/kanban/src/owlbear_kanban/__init__.py` | .80 | Exports: KanbanEngine, pick_dispatchable only; no WorkSession |
| 8 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L302–330 | .80 | MCP `end_work` tool delegates to `engine.end_work()` |

## 3. Analysis

### 3.1 Current State

| Component | Status | Location |
|-----------|--------|----------|
| `WorkSession` dataclass | Exists, 2 fields (`task_id`, `state`) | engine.py L46–52 |
| `_classify_end_work()` | Exists, expects `"success:"` / `"reject:"` prefixes | engine.py L54–60 |
| `_collect_task_sessions()` | Exists, full state machine | engine.py L66–110 |
| `_apply_session_filter()` | Exists | engine.py L119–126 |
| `list_sessions()` | Exists, fully wired | engine.py L978–998 |
| `_derive_sessions()` | Exists | engine.py L1024–1043 |
| `_read_log_entries()` | Exists, validates timestamps | engine.py L1000–1022 |
| Tests (23) | All pass | test_list_sessions.py |

### 3.2 Findings

**F1 — WorkSession model missing 4 of 6 AC fields (.90 confidence)**

AC specifies: `task_id, agent, status, started_at, duration, outcome`. Current model has only `task_id` and `state`. The RED tests (from #923) only assert on `task_id` and `state`, so tests pass despite the gap.

| Field | AC required | Implemented | Source |
|-------|:-----------:|:-----------:|--------|
| task_id | ✓ | ✓ | WorkSession.task_id |
| agent | ✓ | ✗ | — |
| status | ✓ | ✓ (as `state`) | WorkSession.state |
| started_at | ✓ | ✗ | — |
| duration | ✓ | ✗ | — |
| outcome | ✓ | ✗ | — |

Missing fields are derivable from existing JSONL data: `agent` from `claim.detail`, `started_at` from `claim.timestamp`, `duration` from `close.timestamp - claim.timestamp`, `outcome` from the end_work detail string.

**F2 — Detail format mismatch: critical production bug (.95 confidence)**

`_classify_end_work()` expects prefixed details (`"success: todo -> in-progress"`). The engine's `end_work()` writes unprefixed details (`"todo -> in-progress"`). Tests pass because they write JSONL directly with prefixed format — they never go through `end_work()`.

| Detail origin | Format written | `_classify_end_work()` result | Correct? |
|---------------|----------------|-------------------------------|:--------:|
| `end_work(success)` | `"todo -> in-progress"` | `completed-fail` | ✗ |
| `end_work(fail)` | `"outcome=fail"` | `completed-fail` | ✓ |
| `end_work(block)` | `"blocked: needs X"` | `completed-fail` | ✓ |
| `end_work(reject)` | `"in-progress -> todo"` | `completed-fail` | ✗ |
| Test fixture | `"success: todo -> in-progress"` | `completed-pass` | ✓ |
| Test fixture | `"reject: in-progress -> todo"` | `completed-rejected` | ✓ |

**Impact:** Real pipeline agents calling `end_work(outcome="success")` through the MCP server will produce log entries that `list_sessions()` misclassifies. Currently harmless (zero `end_work` entries in production log — legacy CLI used release+move), but will break once agents use the Python engine's MCP `end_work` tool.

**Resolution options:**

| Option | Change | Pros | Cons | Fit |
|--------|--------|------|------|:---:|
| A. Prefix detail in `end_work()` | 1-line format change in engine.py L903–906 | Unambiguous; matches test expectations | Modifies write path (but detail content, not schema) | .85 |
| B. Heuristic in `_classify_end_work()` | Status-order comparison | No write-path change | Ambiguous for forward-reject edge case (#923 F1) | .65 |
| C. Add `outcome` field to JSONL | New JSON key | Clean, extensible | Schema extension; brief says "no new log schema" | .50 |

**Recommendation:** Option A. The #923 research already recommended it. Changing the detail string content is not a schema change (fields remain the same). One-line diff per outcome.

**F3 — WorkSession not exported from package (.75 confidence)**

`__init__.py` exports `KanbanEngine` and `pick_dispatchable`. Cockpit backend will need `WorkSession` for type annotations. Low-effort fix (1 line).

**F4 — No integration test path (.70 confidence)**

All 23 tests write JSONL directly. No test exercises `end_work()` → `list_sessions()` round-trip. This is why F2 was not caught. A single integration test would close this gap.

## 4. Recommendation

The implementation is 80% complete. Remaining work is incremental, not architectural. Three follow-up tasks:

1. **Fix detail format mismatch (F2)** — prefix `end_work()` detail strings with outcome. Highest priority: prevents production misclassification.
2. **Extend WorkSession model (F1)** — add `agent`, `started_at`, `duration`, `outcome` fields; update `_collect_task_sessions()` to populate them.
3. **Export + integration test (F3, F4)** — export `WorkSession` from `__init__.py`; add one end_work→list_sessions round-trip test.

All three are T1 (autonomous) — implementation within existing architecture, no new capabilities or design decisions.

Confidence: .85. Challenge: FALLBACK — challenger not invoked; findings are code-verifiable, not opinion-based.

## 5. Follow-up Tasks

See kanban tasks created at `research` status.
