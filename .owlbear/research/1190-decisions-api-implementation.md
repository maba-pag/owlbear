# Decisions API Implementation Approach

> **Owning task:** #1190 — P3-02: Implement decisions API endpoints
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1190 implements two Cockpit endpoints for DR management:
- `GET /api/decisions/pending` — list pending DRs as structured JSON
- `POST /api/decisions/{id}/resolve` — set response + append notes

Tests exist at `tests/test_cockpit_decisions_api_1189.py`. The decisions engine
module exists at `serve/kanban/src/owlbear_kanban/decisions.py`. This research
determines the implementation approach.

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` — read route pattern | 0.95 |
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — mutation pattern | 0.95 |
| `serve/cockpit/src/owlbear_cockpit/deps.py` — DI pattern | 0.95 |
| `tests/test_cockpit_decisions_api_1189.py` — test expectations | 1.00 |
| `serve/kanban/src/owlbear_kanban/decisions.py` — `_parse_dr()` | 0.85 |
| `.owlbear/decisions/README.md` — response enum, file schema | 0.90 |
| `.owlbear/research/1189-decisions-api-test-design.md` — prior design | 0.80 |

## 3. Analysis

### 3.1 Route Module Placement

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `routes/decisions.py` | Separate concern, clean | One more file |
| B | Add to `mutation.py` | Fewer files | Mixes board-task ops with DR ops |
| C | Split: GET in read.py, POST in mutation.py | Follows existing read/write split | DR logic scattered |

**Recommendation:** Option A (confidence: 0.88). DRs are a separate domain from tasks.
Matches how `read.py` handles board/tasks and `mutation.py` handles task edits.

### 3.2 DI for Decisions Directory

Test expects `cockpit_deps.get_decisions_dir` overridable via `app.dependency_overrides`.
Production path: `engine._kanban_dir.parent / "decisions"` (`.owlbear/decisions/`).

Implementation: add `get_decisions_dir(engine=Depends(get_engine)) -> Path` to `deps.py`.

### 3.3 Parsing Approach

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Import `owlbear_kanban.decisions._parse_dr` | DRY | Private API coupling |
| B | Inline YAML parsing in route module | No coupling, tailored output | ~15 LOC duplication |
| C | Make `_parse_dr` public in kanban pkg | Clean import | Scope creep on kanban pkg |

**Recommendation:** Option B (confidence: 0.80). The cockpit needs different output shape
(title extraction, body truncation). Inline parsing avoids coupling to private API.

### 3.4 Response Enum and Validation

Valid resolve values: `approved`, `needs-info`, `rejected`, `completed`.
Use `typing.Literal` in a Pydantic request model for automatic 422 on invalid values.

### 3.5 Resolve Semantics

Per AC: "sets response field in frontmatter, appends ## Response with notes."
Does NOT move file to `resolved/` — that's the engine's `resolve_pending_drs()` job.
Test `_find_dr_file` checks both dirs, confirming the file can stay in pending/.

### 3.6 Title Extraction

Test fixtures write bodies like `"# Question\nShould we proceed..."`.
`title` = first `# ` heading from body, fallback to filename stem.

### 3.7 Implementation Blueprint

```
deps.py:
  + get_decisions_dir(engine) -> Path  # kanban_dir.parent / "decisions"

routes/decisions.py:
  + DecisionItem (Pydantic model): id, task_id, agent, request_type, created, title, body_preview
  + PendingResponse: count, items
  + ResolveRequest: response (Literal), notes (optional)
  + GET /decisions/pending → parse pending/*.md, return PendingResponse
  + POST /decisions/{id}/resolve → validate, rewrite frontmatter, append section

main.py:
  + from .routes.decisions import router as decisions_router
  + app.include_router(decisions_router, prefix="/api")
```

## 4. Recommendation

Implement as a new `routes/decisions.py` module with `get_decisions_dir` DI dependency.
Inline YAML parsing (~15 LOC), Pydantic `Literal` for enum validation, file rewrite on
resolve. No engine coupling beyond directory discovery.

Confidence: 0.88. Straightforward feature following proven patterns.

Challenge: FALLBACK — no competing architectural options; implementation follows existing
patterns with minor extension.

## 5. Follow-up Tasks

None — #1190 is the implementation task. Tests exist (#1189). No further decomposition needed.
