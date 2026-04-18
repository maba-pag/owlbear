# list_sessions() RED Test Design

> **Owning task:** #923 — P1-01: RED — list_sessions() engine helper tests
> **Date:** 2026-04-18  **Status:** Complete

## 1. Context and Question

Task #923 writes failing tests for a `list_sessions()` engine helper that derives logical Work Sessions from `activity.jsonl` events. The brief (D10) defines sessions as one-per-claim-cycle views over the existing event stream, with six states: running, stuck, released, completed-pass, completed-fail, completed-rejected.

Key questions: (a) can session states be reliably derived from the current JSONL format? (b) what edge cases must the tests cover? (c) what test patterns should be used?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| 1 | `serve/kanban/src/owlbear_kanban/activity_log.py` | .95 | JSONL schema: 5 fields (timestamp, action, task_id, detail, actor) |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L734–830 | .95 | `end_work()` detail format by outcome; claim/release logging |
| 3 | `.owlbear/briefs/draft-cockpit/brief.md` D10 | .95 | Session definition, 6 states, "no new log schema" constraint |
| 4 | `serve/kanban/src/owlbear_kanban/engine.py` L620–690 | .90 | `claim_task()` / `release_task()` activity logging |
| 5 | `serve/kanban/tests/test_mtime_cache_942.py` | .85 | Test pattern: inline config YAML, `_make_board()`, tmp_path fixture |
| 6 | `serve/kanban/src/owlbear_kanban/dispatch.py` L81–89 | .80 | `_claim_is_active()` timeout logic — stuck detection precedent |

## 3. Analysis

### 3.1 Event Vocabulary (from engine.py call sites)

| Action | Detail format | Session impact |
|--------|---------------|----------------|
| `claim` | `"{agent_name}"` | Opens new session |
| `release` | `"{agent_name}"` | Closes session → **released** |
| `end_work` | `"{old} -> {new}"` (success) | Closes → **completed-pass** |
| `end_work` | `"outcome=fail"` (fail) | Closes → **completed-fail** |
| `end_work` | `"blocked: {reason}"` (block) | Closes → **?? (see 3.2)** |
| `end_work` | `"{old} -> {target}"` (reject) | Closes → **completed-rejected** |
| `sweep-release` | `"expired claim by {agent} released"` | Closes session → **released** |
| `create`, `edit`, `move`, `block`, `unblock` | various | Mid-session activity (updates last-activity timestamp) |

### 3.2 Findings

**F1 — `end_work` success/reject ambiguity (.85 confidence)**
Both produce identical `"X -> Y"` detail. Distinguishing requires comparing against status order from board config (forward = success, backward = reject). Edge case: `reject` with a forward target (e.g., `reject move_to="docs"` from "review") is indistinguishable from success.

| Resolution option | Pros | Cons | Fit |
|-------------------|------|------|:---:|
| A. Status-order heuristic | No schema change, works for 95%+ cases | Fails on forward-reject edge case | .75 |
| B. Prefix detail with outcome (e.g., `"success: X -> Y"`) | Unambiguous; backward-compatible reads | Changes engine write path (claimed out-of-scope by brief) | .85 |
| C. Add `outcome` key to JSONL entry | Clean, extensible | Schema extension; brief says "no new log schema" | .60 |

**Recommendation:** Tests should assume **option B** will be adopted in the GREEN phase — a one-line detail prefix change (`f"{outcome}: {old} -> {new}"`) is minimal and unambiguous. The existing JSONL entries (without prefix) can default to heuristic parsing for backward compatibility. Confidence: .80.

**F2 — Missing `block` session state**
The AC lists 6 states; `end_work(outcome="block")` has no explicit mapping. Since `end_work` always releases the claim, a block-outcome session is terminated. Two options: (a) map to `completed-fail`, (b) add `completed-block`.

**Recommendation:** Map to `completed-fail`. The block outcome means "work couldn't complete" — semantically equivalent to fail for session purposes. Adding a 7th state just for block is YAGNI when the cockpit UI groups failures. Confidence: .80.

**F3 — Sweep-release events**
`sweep-release` action (from engine `sweep()`) also terminates sessions. Should be treated as `released` — the claim expired and was cleaned up.

**F4 — Test fixture approach**
Tests should write JSONL fixtures directly (not go through the engine) to isolate session derivation from engine behavior. Pattern: `tmp_path / "activity.jsonl"`, write JSON lines, call `list_sessions()` with the path.

### 3.3 Session State Derivation (decision table for tests)

| Condition | State |
|-----------|-------|
| `claim` with no closing event, age < timeout | **running** |
| `claim` with no closing event, age ≥ timeout, no recent activity | **stuck** |
| `release` or `sweep-release` closes session | **released** |
| `end_work` with success outcome | **completed-pass** |
| `end_work` with fail outcome | **completed-fail** |
| `end_work` with block outcome | **completed-fail** |
| `end_work` with reject outcome | **completed-rejected** |

### 3.4 Test Scenario Matrix

| # | Scenario | AC line |
|---|----------|---------|
| 1 | Single claim→end_work(success) → completed-pass | Claim cycle derivation |
| 2 | Single claim→end_work(fail) → completed-fail | Session states |
| 3 | Single claim→end_work(reject) → completed-rejected | Session states |
| 4 | Single claim→end_work(block) → completed-fail | Block mapping (F2) |
| 5 | Single claim→release → released | Session states |
| 6 | Claim, no close, age < timeout → running | Running detection |
| 7 | Claim, no close, age ≥ timeout → stuck | Stuck detection |
| 8 | Filter: active-only (default) returns running+stuck | Filter by state |
| 9 | Filter: all returns everything | Filter by state |
| 10 | Filter: failed-or-rejected | Filter by state |
| 11 | Filter: released | Filter by state |
| 12 | Empty activity log → empty list | Empty log |
| 13 | Malformed JSON line skipped | Graceful skip |
| 14 | Incomplete entry (missing fields) skipped | Graceful skip |
| 15 | Same task claimed twice (release then re-claim) → 2 distinct sessions | Re-claim cycles |
| 16 | Multiple tasks interleaved → correct session per task | Multi-task |

## 4. Recommendation

Test design is sound. The test file should:
1. Build JSONL fixtures inline with explicit detail prefixes (F1 option B)
2. Map `block` outcome to `completed-fail` (F2)
3. Use `tmp_path` + direct JSONL writes (not engine operations)
4. Import `list_sessions` from `owlbear_kanban` (per AC)
5. Pass `claim_timeout` as a parameter (from board config)

Challenge: FALLBACK — subagent not invoked for bounded test-design research (no multi-option architectural decision).

Confidence: .82 — the detail-format finding (F1) introduces a dependency on a minor schema change, but the change is small and well-scoped.

## 5. Follow-up Tasks

- **#923 itself** advances to backlog (test-writer picks it up)
- Follow-up: activity log detail prefix change (needed before GREEN #926)
