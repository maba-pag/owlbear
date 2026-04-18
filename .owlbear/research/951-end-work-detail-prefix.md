# Prefix end_work Activity Log Detail with Outcome Type

> **Owning task:** #951 — Prefix end_work activity log detail with outcome type
> **Date:** 2026-04-18  **Status:** Complete

## 1. Context and Question

Research #923 finding F1 identified that `end_work()` success and reject outcomes produce identical `"X -> Y"` detail format, making `list_sessions()` unable to distinguish `completed-pass` from `completed-rejected`. Task #951 proposes prefixing the outcome type. Research question: what is the exact change, what backward-compat is needed, and are there any risks?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| 1 | `engine.py` L900–903 (`end_work` details dict) | .95 | Current write format for all 4 outcomes |
| 2 | `engine.py` L55–62 (`_classify_end_work`) | .95 | Reader already expects `"success:"` and `"reject:"` prefixes |
| 3 | `test_list_sessions.py` L151–436 | .90 | All fixtures already use prefixed format |
| 4 | `.owlbear/research/923-list-sessions-tests.md` § 3.2 F1 | .90 | Original finding and option analysis |

## 3. Analysis

### 3.1 Current vs. Proposed Format

| Outcome | Current detail | Proposed detail |
|---------|---------------|----------------|
| success | `"todo -> in-progress"` | `"success: todo -> in-progress"` |
| fail | `"outcome=fail"` | `"fail: outcome=fail"` |
| block | `"blocked: {reason}"` | `"block: {reason}"` |
| reject | `"in-progress -> todo"` | `"reject: in-progress -> todo"` |

### 3.2 Key Findings

**F1 — Reader already expects the new format (.95 confidence)**
`_classify_end_work()` checks `startswith("success:")` and `startswith("reject:")`. All `test_list_sessions.py` fixtures use prefixed strings. The writer is the only part out of sync.

**F2 — No existing engine tests check old detail format (.90 confidence)**
Searched all test files under `serve/kanban/tests/` and `serve/mcp-kanban/tests/`. Zero assertions against the old unprefixed detail format. Only `test_list_sessions.py` tests detail strings — using prefixed format already.

**F3 — Backward-compat gap in reader (.85 confidence)**
`_classify_end_work()` has no fallback for unprefixed entries. Old `"X -> Y"` entries (without `"success:"` or `"reject:"` prefix) fall through to `completed-fail` — a misclassification. Practical impact is low since `list_sessions()` is new code, but the AC explicitly requires backward compat.

### 3.3 Backward-Compat Options

| Option | Description | Pros | Cons | Fit |
|--------|-------------|------|------|:---:|
| A. `" -> " in detail` fallback | Map unprefixed `"X -> Y"` to `completed-pass` | 1 line, handles 95%+ old entries | Old rejects misclassified as pass | .80 |
| B. Leave as-is | Old entries fall through to `completed-fail` | Zero code | Violates AC requirement | .40 |
| C. Status-order heuristic | Compare against pipeline order | Precise | Complex, needs board config in reader | .50 |

## 4. Recommendation

Prefix all 4 outcomes consistently (4 lines changed in `end_work()`). For backward compat, use Option A — add a single `" -> " in detail` fallback line in `_classify_end_work()` that maps unprefixed transition strings to `completed-pass`. This is a 5-line total change across 2 locations.

Confidence: .90 — the reader already expects this format; the change aligns writer with reader.

Challenge: FALLBACK — trivial implementation task with no multi-option architectural decision.

Tier: **T1 — Autonomous.** No new capability, no architecture change, no security impact.

## 5. Implementation Guidance

**Location 1** — `engine.py` L900–903 (`end_work` details dict):
```python
details = {
    "success": f"success: {old_status} -> {record.status}",
    "fail": "fail: outcome=fail",
    "block": f"block: {block_reason}",
    "reject": f"reject: {old_status} -> {move_to}",
}
```

**Location 2** — `engine.py` L55–62 (`_classify_end_work`), add fallback before final return:
```python
if " -> " in detail:
    return "completed-pass"  # unprefixed legacy entry
```

No follow-up tasks needed — task #951 AC already covers the full scope.
