# pick_tasks resolve_pending_drs Integration Testing

> **Owning task:** #1184 — P1-05: Test pick_tasks resolve_pending_drs integration
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1185 will add a `_try_resolve_pending_drs()` call at the top of `AgentView.pick_tasks()` that wraps `decisions.resolve_pending_drs(engine)` in a try/except guard. Task #1184 writes the tests that define this integration contract. Since `decisions.py` doesn't exist yet (#1181), tests must mock the module-level function.

**Question:** What test patterns verify the 5 ACs (call ordering, exception isolation, pre-filter resolution, no-DR graceful, no-directory graceful)?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | `serve/kanban/tests/test_engine_pick_tasks_1074.py` | 1.0 | Existing pick_tasks test patterns: tmp_path boards, `_make_board`, `_write_task`, `KanbanEngine(board, activity_log=False)` |
| S2 | `.owlbear/briefs/draft-dr-script-replacement/brief.md` §pick_tasks Integration | 1.0 | "call `resolve_pending_drs(engine)` at top, wrapped in try/except — never stall dispatch" |
| S3 | `.owlbear/briefs/draft-dr-script-replacement/stances/architect.md` §2 | 1.0 | `_try_resolve_pending_drs()` private method on AgentView; calls `scan_pending_responses()` then `resolve_decision()` per file |
| S4 | `serve/kanban/src/owlbear_kanban/engine.py` L1860-1880 | .95 | `AgentView.__init__(self, engine)` — stores engine ref; `pick_tasks` is method on AgentView |
| S5 | Task #1185 AC | 1.0 | Implementation contract: call at top, try/except, log, never propagate |

## 3. Analysis

### 3.1 Test Strategy

Since `decisions.py` won't exist when tests are written, all tests mock the integration point. The implementation (#1185) will wire the real function; tests verify the contract.

| AC | Approach | Mock strategy |
|----|----------|---------------|
| Calls resolve before selection | `monkeypatch` the function; verify call happened + results unchanged | Side-effect records call, returns `[]` |
| Exceptions don't propagate | Mock raises `RuntimeError`; assert pick_tasks returns valid response | Side-effect raises |
| Resolved DRs processed before filtering | Mock has side-effect that unblocks a task (file write); pick_tasks includes it | Mutate task file in side-effect |
| No pending DRs → works | No mock (or returns `[]`); standard board → normal results | Returns empty list |
| No pending/ directory → works | Board without decisions dir; function handles gracefully | Returns `[]` or skips |

### 3.2 Test Location and Structure

- **File:** `tests/test_pick_tasks_resolve_1184.py`
- **Pattern:** Follows `test_engine_pick_tasks_1074.py` — `tmp_path` boards, `_make_board`/`_write_task` helpers
- **Mock target:** `owlbear_kanban.decisions.resolve_pending_drs` (once module exists); implementation will import it at module or function level in `engine.py`
- **Class:** Single `TestFromAC_PickTasksResolveIntegration` with 5 test methods

### 3.3 Key Design Decision: Mock Granularity

The brief shows two architectural layers:
1. `AgentView._try_resolve_pending_drs()` — private method, catches exceptions
2. `decisions.resolve_pending_drs(engine)` — called by the private method

Tests should mock at the `decisions.resolve_pending_drs` level (the module function), not at the `_try_resolve_pending_drs` level. This tests the actual integration contract (try/except wrapping, call ordering) rather than just testing a mock.

**Alternative considered:** Mocking `_try_resolve_pending_drs` directly. Rejected — this only proves the method is called, not that it correctly wraps exceptions. The AC explicitly requires testing the try/except behavior.

## 4. Recommendation

Write 5 tests in `tests/test_pick_tasks_resolve_1184.py` using `monkeypatch` on the decisions module function. The test file imports will need a conditional guard since `decisions.py` won't exist until #1181 lands — use `unittest.mock.patch` targeting the import path that #1185 will use.

Confidence: .90 — the pattern is well-established; the only risk is the exact import path the implementation chooses (mitigated by the brief specifying the module location).

Challenge: FALLBACK — test specification task with clear established patterns; no design decision to challenge.

## 5. Follow-up Tasks

None needed — this task IS the test task. Advances to backlog for test-writer to implement.
