# Cockpit: Delegate Decision Resolution to kanban resolve_decision()

> **Owning task:** #1869 — Cockpit: delegate decision resolution to kanban resolve_decision()
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1868 extracted domain logic into `owlbear_kanban.decisions.resolve_decision()`. The cockpit resolve endpoint (`routes/decisions.py` lines 191–222) still has the inline duplicate: parse → stale-check → rewrite frontmatter → append response section → persist → edit_task (summary + unblock) → move_to_resolved. This task replaces that inline code with a single delegation call.

**Question:** What are the integration considerations for this delegation?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/kanban/src/owlbear_kanban/decisions.py:187-223` | Codebase | 1.0 — the target function |
| `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:155-226` | Codebase | 1.0 — the code being replaced |
| `serve/cockpit/src/owlbear_cockpit/main.py:55-74` | Codebase | 0.9 — global error handler confirms ConcurrencyError→409 |
| Task #1868 (archived) | Kanban | 0.9 — proves function correctness (28 tests GREEN) |
| `tests/test_cockpit_decisions_api.py` (409 tests) | Codebase | 0.8 — verifies tests assert on status codes, not message text |

## 3. Analysis

### Integration Points

| Concern | Current Route | After Delegation | Impact |
|---------|--------------|------------------|--------|
| Parse errors | Caught (TypeError/ValueError/YAMLError) → 422 | Must still catch — kanban propagates parse errors | Wrap call in try/except |
| Stale check | Route raises ConcurrencyError directly | kanban raises ConcurrencyError internally | Global handler catches → 409 ✓ |
| FileNotFoundError | Route catches inline `pass` | kanban catches internally | Transparent ✓ |
| Name collision | Route function named `resolve_decision` | Import alias needed | `as kanban_resolve_decision` |
| Error message | `"Decision {decision_id!r} ..."` (no `.md`) | `"Decision {path.name!r} ..."` (with `.md`) | Tests check status/envelope only — safe |

### Removals After Delegation

| Item | Reason |
|------|--------|
| `_append_response_section` helper (lines 91–100) | Logic now in kanban module |
| `_rewrite_response` helper (lines 103–109) | Logic now in kanban module |
| `from io import StringIO` | Only used by `_rewrite_response` |
| `from ruamel.yaml import YAML` | Only used by `_rewrite_response` |
| `canonical_summary` import | Only used in replaced inline code |
| `move_to_resolved` import | Only used in replaced inline code |

### Retained Imports

- `parse_dr` — still used by `list_pending_decisions` and resolved-path fallback check
- `YAMLError` — still used by `list_pending_decisions` and resolved-path fallback check

## 4. Recommendation (confidence: 0.92)

Straightforward T1 refactoring. No alternatives to evaluate — the task specifies the exact implementation. The kanban function signature matches the route's needs precisely. Existing test suite provides full behavioral coverage.

Challenge: skipped — no decision point (approach dictated by task body, no competing options).

### Implementation Sketch

```python
from owlbear_kanban.decisions import parse_dr, resolve_decision as kanban_resolve_decision

# ... in resolve endpoint, replace lines 191-222 with:
try:
    kanban_resolve_decision(
        pending_path,
        req.response,
        engine,
        notes=req.notes,
        resolved_by="cockpit-api",
    )
except (TypeError, ValueError, YAMLError) as exc:
    detail = "Invalid decision file format"
    raise HTTPException(status_code=422, detail=detail) from exc

return {"id": decision_id, "response": req.response}
```

## 5. Follow-up Tasks

No additional tasks needed — #1869 itself is the implementation task (currently at `research`, advances to `backlog`). Parent #1865 gates completion of both children.
