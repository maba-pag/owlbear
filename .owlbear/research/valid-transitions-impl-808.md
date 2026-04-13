# Add valid_transitions(status) — Implementation Research

> **Owning task:** #808 — Add valid_transitions(status)
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #808 is the GREEN-phase implementation task for `valid_transitions(status)` on
`KanbanEngine`. Paired with #807 (RED tests). Both are Phase 1, parent #798.

**Central question:** What work remains for the builder to satisfy all 6 AC lines?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L111–129 | 1.0 | `valid_transitions()` fully implemented: returns `{all} - {status}`, raises `ValueError` |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L518–580 | 1.0 | `end_work()` docstring — no mention of linear behavior being agent-specific |
| 3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L290–320 | 0.8 | MCP `end_work` wrapper — thin passthrough, one-line docstring |
| 4 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` L40 | 0.9 | Brief: "`end_work`'s linear behavior documented as agent-specific" |
| 5 | `tests/test_kanban_engine_compound.py` | 0.8 | 20+ `end_work` tests covering success/fail/block/reject outcomes |
| 6 | `.owlbear/research/valid-transitions-tests-807.md` | 0.9 | #807 research confirms implementation pre-exists |

## 3. Analysis

### AC Gap Assessment

| AC | Status | Evidence | Builder action |
|----|--------|----------|----------------|
| AC1: `valid_transitions(status)` method | ✅ Done | engine.py L111 | None |
| AC2: Returns set of all except given | ✅ Done | engine.py L124–128 | None |
| AC3: Raises `ValueError` for invalid | ✅ Done | engine.py L125–127 | None |
| AC4: `end_work()` linear behavior documented | ❌ Gap | Docstring at L528–543 lacks agent-specific note | Add note |
| AC5: #807 tests pass GREEN | ⏳ Blocked | #807 at `todo`, tests not yet written | Verify after #807 |
| AC6: Existing MCP tests pass | ⏳ Verify | No code changes for AC1–3; AC4 is docstring-only | Run tests |

### AC4 Docstring Fix — Options

| Option | Description | Risk |
|--------|-------------|------|
| A: Note in `end_work()` engine docstring only | Add paragraph explaining linear progression is agent-specific; GUI should use `move_task()` + `valid_transitions()` | Low — single change point |
| B: Note in both engine and MCP server docstring | Same as A, plus update MCP wrapper docstring | Low — two change points, keeps both in sync |

**Recommendation: Option A** (confidence: 0.90). The engine docstring is the canonical
API surface. The MCP server docstring is a one-liner tool description and isn't consumed
by non-agent callers — updating it adds marginal value.

### GREEN-on-Arrival Analysis

Identical situation to #807: the implementation pre-exists. The builder's only code
change is the AC4 docstring update. All other ACs are either already satisfied or
verification-only (run tests).

Challenge: FALLBACK — T1 docstring task, no architectural trade-offs to challenge.

## 4. Recommendation

Builder should:
1. Update `end_work()` docstring (engine.py ~L528) to note that the `outcome="success"`
   linear status progression is an **agent-specific workflow convention**. General
   consumers should use `move_task()` for arbitrary transitions and
   `valid_transitions()` to discover available targets.
2. Verify #807 tests pass GREEN (after #807 is complete).
3. Run existing MCP/engine test suite to confirm O4.

Confidence: 0.90. Tier: T1 — autonomous (docstring update, no new capability).

## 5. Follow-up Tasks

None needed. #808 is the implementation task itself. #807 (dependency) already exists.
