# Test: type:user-action in NON_IMPL_TAGS Gate Sets

> **Owning task:** #665 — Test: type:user-action in NON_IMPL_TAGS gate sets
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Parent task #661 recommended adding `type:user-action` to both `_NON_IMPL_TAGS`
(gates.py) and `_PICK_NON_IMPL_TAGS` (server.py) so user-action tasks are
exempt from the TDD gate. Task #665 is the TDD RED phase: write failing tests
before the implementation in #662.

**Question:** Can the tests follow the #630 pattern, and will they correctly
fail against current code?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/orchestrator/src/owlbear/planner/gates.py` L24-26 | 1.0 | `_NON_IMPL_TAGS` — 8 tags, no `type:user-action` |
| 2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L531-533 | 1.0 | `_PICK_NON_IMPL_TAGS` — 8 tags, no `type:user-action` |
| 3 | `tests/test_tdd_gate_non_impl_630.py` | 1.0 | Test pattern: helpers, membership + behavioral tests |
| 4 | `.owlbear/research/user-action-required-pipeline-handling.md` | 0.9 | Parent research recommending `type:user-action` tag |
| 5 | `serve/orchestrator/src/owlbear/planner/models.py` | 0.8 | `Task.tags: list[str]` field available |

## 3. Analysis

### Current State Verification

| Location | Current tags | Contains `type:user-action` |
|----------|-------------|----------------------------|
| `gates.py` `_NON_IMPL_TAGS` | research, docs, type:config, type:docs, test, type:test, agent, quality | **No** |
| `server.py` `_PICK_NON_IMPL_TAGS` | research, docs, type:config, type:docs, test, type:test, agent, quality | **No** |

Tests asserting membership will correctly **FAIL** (TDD RED).

### Test Structure (follows #630 pattern exactly)

| AC # | Test | Assertion | Expected RED result |
|------|------|-----------|---------------------|
| 1 | Membership: `_NON_IMPL_TAGS` | `"type:user-action" in _NON_IMPL_TAGS` | FAIL — not in set |
| 2 | Membership: `_PICK_NON_IMPL_TAGS` | `"type:user-action" in _PICK_NON_IMPL_TAGS` | FAIL — not in set |
| 3 | Behavioral: `check_tdd()` | in-progress + type:user-action + no TW Notes → True | FAIL — returns False |
| 4 | Behavioral: `_check_pick_gates()` | in-progress + type:user-action + no TW Notes → True | FAIL — returns False |

### Implementation Notes

- File: `tests/test_user_action_non_impl_661.py` (per task AC)
- Reuse helper pattern from #630: `_task()`, `_task_dict()`, `_board()`, `_make_mcp_ctx()`
- Import `_NON_IMPL_TAGS` from `owlbear.planner.gates` and `_PICK_NON_IMPL_TAGS` from `owlbear_mcp_kanban.server`
- Behavioral tests use `check_tdd()` and `pick_tasks()` (same as #630)

## 4. Recommendation

Proceed with test implementation following the #630 pattern exactly. (confidence: .95)

Challenge: N/A — T1 test task, direct pattern extension, no trade-offs to challenge.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #662 (implementation) already depends on #665.
