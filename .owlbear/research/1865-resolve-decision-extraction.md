# Kanban: expose resolve_decision() and delegate from Cockpit

> **Owning task:** #1865 — Kanban: expose resolve_decision() and delegate from Cockpit
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Cockpit's `routes/decisions.py` directly manages DR file lifecycle (rewrite frontmatter, persist, side-effects, move to resolved). This violates the boundary: Cockpit owns the *HTTP layer* but kanban owns the *decision file format and transitions*. Should a `resolve_decision()` entry point live in `owlbear_kanban.decisions`, and what shape should it take?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` | Codebase — current write path | 1.0 |
| `serve/kanban/src/owlbear_kanban/decisions.py` | Codebase — existing helpers | 1.0 |
| `.owlbear/research/cockpit-api-boundary-audit.md` | Prior research (#1849) | 0.9 |
| `serve/kanban/src/owlbear_kanban/errors.py` | Domain error types | 0.8 |
| `tests/test_decisions.py` | Existing test coverage | 0.7 |

## 3. Analysis

### Current Cockpit resolve_decision endpoint (lines 155–225)

| Step | Code | Belongs to |
|------|------|-----------|
| Validate decision_id pattern | `_validate_decision_id` | HTTP layer (Cockpit) |
| Find pending file, check 404/stale | File existence checks | HTTP layer (Cockpit) |
| Parse DR file | `parse_dr(pending_path)` | Already in kanban |
| Validate still pending | `meta.get("response") != "pending"` → ConcurrencyError | Domain logic |
| Update frontmatter (response, resolved_by) | `updated["response"] = ...` | Domain logic |
| Append response section to body | `_append_response_section()` | Domain logic |
| Persist rewritten file | `_rewrite_response()` → `path.write_text()` | Domain logic |
| Append canonical summary to task | `engine.edit_task(append_body=...)` | Domain logic |
| Unblock task (approved/rejected) | `engine.edit_task(blocked=False)` | Domain logic |
| Move to resolved dir | `move_to_resolved()` | Already in kanban |

Steps marked "Domain logic" should move into `owlbear_kanban.decisions.resolve_decision()`.

### Proposed API

```python
def resolve_decision(
    path: Path,
    response: str,
    engine: DecisionEngine,
    *,
    notes: str | None = None,
    resolved_by: str = "unknown",
) -> Path:
    """Resolve a pending DR: rewrite, apply side-effects, move to resolved."""
```

**Parameters:**
- `path` — pending DR file (caller locates it)
- `response` — "approved" / "rejected" / "needs-info"
- `engine` — for task-body and blocked-state side-effects
- `notes` — optional human notes appended to response section
- `resolved_by` — attribution tag (Cockpit passes "cockpit-api")

**Returns:** resolved file path (from `move_to_resolved`)

**Raises:** `ConcurrencyError("ERR_STALE", ...)` if file is not pending.

### Symmetry with `create_dr()`

| Operation | Function | Side-effects |
|-----------|----------|--------------|
| Create | `create_dr(decisions_dir, engine, ...)` | Blocks task |
| Resolve | `resolve_decision(path, response, engine, ...)` | Unblocks task (approved/rejected) |

### Impact on `resolve_pending_drs()`

`resolve_pending_drs()` is a batch reconciliation path for hand-edited files. It could be refactored to call `resolve_decision()` internally, but this is optional — the two paths have subtly different semantics (batch skips body-section append since files are already complete). Recommend deferring that unification.

### Cockpit route simplification

After extraction, the Cockpit endpoint reduces to:
1. Validate decision_id (HTTP concern)
2. Resolve pending_path / check 404 (HTTP concern)
3. `resolve_decision(pending_path, req.response, engine, notes=req.notes, resolved_by="cockpit-api")`
4. Return JSON response

The `_rewrite_response` and `_append_response_section` helpers move to kanban (or become internal to `resolve_decision`).

## 4. Recommendation

Add `resolve_decision()` to `owlbear_kanban.decisions` with the API above. Cockpit delegates to it, removing ~30 lines of file-lifecycle code from the route.

Confidence: 0.90 — well-defined refactor, clear boundary, symmetric with existing `create_dr`.

Challenge: skipped — recommendation inherited from challenged research (#1849, Finding 1). No new options to evaluate.

## 5. Follow-up Tasks

1. **Add `resolve_decision()` to kanban decisions module + unit tests** (T1 — add function, test in isolation)
2. **Cockpit: delegate to `resolve_decision()`** (T1 — replace inline lifecycle with single call)
