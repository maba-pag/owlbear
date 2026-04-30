# Decisions API Test Design

> **Owning task:** #1189 — P3-01: Test decisions API endpoints
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1189 requires RED-phase tests for two cockpit endpoints:
- `GET /api/decisions/pending` — list pending DRs with count + items
- `POST /api/decisions/{id}/resolve` — resolve a specific DR by filename-stem ID

The implementation (#1190) depends on both this test task and the engine module (#1181).
Tests must be self-contained — decisions.py does not exist yet.

**Research question:** What test architecture fits the existing cockpit patterns while
testing the decisions API contract specified in the AC?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `tests/test_cockpit_mutation_api.py` — existing mutation test patterns | 0.95 |
| `tests/test_cockpit_read_api.py` — existing read endpoint test patterns | 0.95 |
| `.owlbear/decisions/README.md` — DR file format and response enum | 0.90 |
| `.owlbear/decisions/resolved/1155-*.md` — real DR file structure | 0.85 |
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` — router pattern | 0.80 |
| `serve/cockpit/src/owlbear_cockpit/deps.py` — DI pattern | 0.80 |
| Parent #1179 decomposition — dependency graph and planned API | 0.75 |

## 3. Analysis

### 3.1 DR Identity

DR files use `{task_id}-{slug}.md` naming. The API "id" = filename stem (e.g., `42-scope-params`).
This avoids coupling to an auto-increment integer — file-based identity is self-describing.

### 3.2 Decisions Directory Discovery

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `get_decisions_dir` dependency | Testable via `dependency_overrides`, isolated | Extra DI boilerplate |
| B | Derive from engine: `kanban_dir.parent / "decisions"` | Zero new deps | Couples layout assumption |
| C | Add `decisions_dir` param to KanbanEngine | Single config point | Scope creep on engine |

**Recommendation:** Option A (confidence: 0.82). Matches `get_engine`/`get_cache`/`get_view` pattern.
Test fixture overrides `get_decisions_dir` → `tmp_path / "decisions"`.

### 3.3 Test Fixture Design

```
tmp_path/
  decisions/
    pending/
      42-waiting-on-dep.md    (standard DR, body > 200 chars)
      99-short-body.md        (body < 200 chars, for truncation edge)
    resolved/                 (empty dir)
```

Fixture creates raw YAML-frontmatter files directly — no dependency on `owlbear_kanban.decisions`.

### 3.4 Response Enum Values

From README: `approved | needs-info | rejected | completed`. The `pending` value is the
initial state, not a valid resolve target.

### 3.5 Test Matrix

| AC | Test | Assertions |
|----|------|------------|
| GET returns count + items | `test_pending_returns_count_and_items` | 200, `count` int, `items` list |
| Item shape | `test_pending_item_shape` | id, task_id, agent, request_type, created, title, body_preview |
| body_preview truncated | `test_body_preview_truncated_to_200` | len ≤ ~200, no trailing mid-word cut |
| Empty list | `test_pending_empty_returns_zero` | 200, count=0, items=[] |
| Resolve happy path | `test_resolve_accepted_response` | 200, file updated |
| Resolve updates file | `test_resolve_writes_response_and_section` | YAML `response` changed, `## Response` appended |
| Resolve 404 | `test_resolve_nonexistent_returns_404` | 404, id in detail |
| Resolve invalid enum | `test_resolve_invalid_response_returns_422` | 422 |

## 4. Recommendation

**Follow existing cockpit test patterns verbatim:**
- `tmp_path` fixture with pre-written DR files (same as board fixture creates task files)
- New `get_decisions_dir` dependency override in the `client` fixture
- Test class per endpoint: `TestFromAC_DecisionsPending`, `TestFromAC_DecisionsResolve`
- File: `tests/test_cockpit_decisions_api_1189.py`

Confidence: 0.85. Low risk — patterns are proven, AC is unambiguous, no architectural novelty.

Challenge: FALLBACK — trivial test-infrastructure research, no competing options to challenge.

## 5. Follow-up Tasks

None needed — #1190 (implement) already exists in the dependency graph. The test file
itself is the deliverable for #1189's downstream (test-writer phase).
