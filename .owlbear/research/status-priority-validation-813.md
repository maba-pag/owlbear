# Status/Priority Validation — Test Design

> **Owning task:** #813 — Tests — status/priority validation
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #813 is the TDD RED phase for adding status/priority validation to `create_task` and `edit_task` in the kanban engine. Sibling task #814 (GREEN phase) implements the validation and depends on #813.

**Question:** What tests are needed, where should they live, and what assertions should they use?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `engine.py` — `move_task` validation | `serve/kanban/src/owlbear_kanban/engine.py:396-412` | 0.95 — existing validation pattern to replicate |
| `engine.py` — `create_task` (no validation) | `serve/kanban/src/owlbear_kanban/engine.py:232-295` | 0.95 — target function, currently no validation |
| `engine.py` — `edit_task` (no validation) | `serve/kanban/src/owlbear_kanban/engine.py:289-395` | 0.95 — target function, currently no validation |
| MCP `server.py` — `move_task` error mapping | `serve/mcp-kanban/src/.../server.py:205-211` | 0.90 — existing `ValueError→ToolError` pattern |
| MCP `server.py` — `create_task` (no error handling) | `serve/mcp-kanban/src/.../server.py:177-206` | 0.90 — no try/except at all |
| MCP `server.py` — `edit_task` (partial) | `serve/mcp-kanban/src/.../server.py:217-278` | 0.90 — catches `FileNotFoundError` only |
| `test_kanban_engine_crud.py` — move_task tests | `tests/test_kanban_engine_crud.py:440-475` | 0.85 — fixture + assertion pattern |
| `config.yml` — valid values | `.owlbear/kanban/config.yml` | 0.80 — source of truth for valid enums |
| Brief | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | 0.75 — Phase 1 work item context |

## 3. Analysis

### Current State

| Function | Status validation | Priority validation | Error mapping |
|----------|:-:|:-:|:-:|
| `engine.move_task` | ✓ ValueError | N/A | ✓ ToolError |
| `engine.create_task` | ✗ | ✗ | ✗ (no try/except) |
| `engine.edit_task` | ✗ | ✗ | ✗ (only FileNotFoundError) |

### Test File Design

Single file: `tests/test_status_priority_validation_813.py`

| Test Class | AC Coverage | Tests | RED Mechanism |
|------------|------------|-------|---------------|
| `TestFromAC_CreateTaskValidation` | AC1, AC2, AC5 | 5 | Engine silently accepts garbage → no ValueError raised |
| `TestFromAC_EditTaskValidation` | AC3, AC4, AC5 | 5 | Engine silently accepts garbage → no ValueError raised |
| `TestFromAC_MCPAdapterValidation` | AC6 | 4 | Engine doesn't raise → adapter doesn't catch → no ToolError |

**Fixtures:** Reuse `kanban_dir`/`engine` pattern from `test_kanban_engine_crud.py`. MCP tests use `AppContext` with real engine + `MagicMock` context.

### Assertion Pattern

Engine tests: `pytest.raises(ValueError)` — strict, not `(ValueError, KeyError, LookupError)` like the older `move_task` tests. The AC explicitly requires `ValueError`.

MCP tests: `pytest.raises(ToolError)` — verifying the adapter catches `ValueError` and re-raises as `ToolError`.

### Valid Values (from config)

- **Statuses:** research, backlog, todo, in-progress, review, docs, done
- **Priorities:** someday, nice-to-have, important, needed, critical

## 4. Recommendation

**Approach:** Single test file with 14 test cases across 3 classes. Reuse existing fixture pattern. Strict `ValueError`/`ToolError` assertions. All tests FAIL in RED phase.

Confidence: .95

Challenge: SKIPPED — trivial test task, pattern directly from existing `move_task` code.

## 5. Follow-up Tasks

- #814 (already exists) — GREEN phase implementation, depends on #813
- No additional follow-up tasks needed
