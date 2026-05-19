# Pydantic Response Model for GET /api/decisions/pending

> **Owning task:** #1640 — P2-05: Pydantic response model for GET /api/decisions/pending
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

The `list_pending_decisions` endpoint returns `dict[str, object]` — no schema enforcement. All other cockpit routes use Pydantic `response_model`. The question: what's the minimal implementation to add type-safe serialization with validation-based exclusion of malformed items?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` (current impl) | 1.0 |
| 2 | `serve/cockpit/src/owlbear_cockpit/routes/read.py` (existing pattern) | 0.9 |
| 3 | `serve/kanban/src/owlbear_kanban/decisions.py` (`parse_dr` return shape) | 0.9 |
| 4 | `tests/test_cockpit_decisions_api.py` (existing assertions) | 0.8 |
| 5 | FastAPI docs: response_model + validation_error handling | 0.7 |

## 3. Analysis

### Current Data Flow

```
parse_dr(path) → (meta: dict, body: str)
    ↓ manual dict construction
{"id", "task_id", "agent", "request_type", "created", "title", "body", "body_preview"}
    ↓ return as dict[str, object]
No serialization enforcement
```

### Implementation Approach

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Model location | Same file (`decisions.py`) | Models are route-local; only `BoardOut` lives in `models.py` and that's for cross-route reuse |
| `task_id` coercion | Pydantic `BeforeValidator` or field with `int` type (auto-coercion via `coerce_numbers_to_str=False`) | YAML may parse `task_id: "42"` as str; Pydantic v2 strict mode rejects str→int unless explicitly coerced |
| Malformed exclusion | Wrap `PendingDRItem.model_validate()` in try/except `ValidationError` → skip item | Matches AC: "silently excluded", endpoint still returns 200 |
| `response_model` | `PendingDRResponse` on `@router.get` decorator | Matches AC and existing pattern |
| `body` field in model | Keep as `str` — tests assert full body | Existing tests confirm this field exists |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Breaking existing tests | Low | Tests already assert shape that matches proposed model |
| `task_id` coercion edge cases (None, non-numeric) | Low | `ValidationError` catches → item excluded (AC behavior) |
| Performance overhead of Pydantic validation | Negligible | Pending dir typically has <20 files |

## 4. Recommendation

Implement directly with confidence **0.92**. This is a mechanical application of the pattern already used by all other cockpit routes.

**Proposed model shape:**

```python
class PendingDRItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    task_id: int
    agent: str
    request_type: str
    created: str
    title: str
    body: str
    body_preview: str

class PendingDRResponse(BaseModel):
    count: int
    items: list[PendingDRItem]
```

The endpoint constructs items as before, validates each via `PendingDRItem.model_validate()`, collects valid ones, and returns `PendingDRResponse(count=len(items), items=items)`.

Challenge: SKIP — trivial refactor applying existing codebase pattern verbatim. No architectural decision.

## 5. Follow-up Tasks

Delegate to planner: single implementation task at `todo` status (research gate passed — all items satisfied by this analysis).
