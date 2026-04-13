# Status/Priority Validation — Implementation Design

> **Owning task:** #814 — Add status/priority validation
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #814 is the TDD GREEN phase for adding `ValueError` validation to `create_task` and `edit_task`, plus `ValueError→ToolError` mapping in MCP adapter handlers. Implementation must replicate the existing `move_task` pattern.

**Question:** Where exactly should validation go, what edge cases exist, and what's the minimal change set?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `engine.py` — `move_task` validation | `serve/kanban/src/owlbear_kanban/engine.py` | 0.95 |
| `engine.py` — `create_task` | same file | 0.95 |
| `engine.py` — `edit_task` | same file | 0.95 |
| MCP `server.py` — `move_task` handler | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 0.90 |
| MCP `server.py` — `create_task` handler | same file | 0.90 |
| MCP `server.py` — `edit_task` handler | same file | 0.90 |
| `models.py` — `BoardConfig` | `serve/kanban/src/owlbear_kanban/models.py` | 0.85 |
| `config.yml` — valid enums | `.owlbear/kanban/config.yml` | 0.80 |
| #813 research doc | `.owlbear/research/status-priority-validation-813.md` | 0.85 |

## 3. Analysis

### Existing Validation Pattern (move_task)

```python
valid_statuses = {s["name"] for s in self._config.statuses}
if status != "archived" and status not in valid_statuses:
    msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
    raise ValueError(msg)
```

MCP handler wraps: `except (FileNotFoundError, ValueError) as exc: raise ToolError(str(exc))`

### Implementation Approach — Trade-off Matrix

| Approach | LOC | KISS | Testability | Risk |
|----------|-----|------|-------------|------|
| A. Inline validation (replicate pattern) | ~12 | 0.95 | 0.95 | Low — proven pattern |
| B. Shared `_validate_status`/`_validate_priority` helpers | ~20 | 0.80 | 0.90 | Low — mild over-engineering for 3 call sites |
| C. Pydantic validators on Task model | ~15 | 0.60 | 0.70 | Medium — model needs config context |

Recommendation: **Approach A** — inline validation, identical to `move_task`.

### Edge Cases

| Case | `create_task` | `edit_task` |
|------|--------------|-------------|
| Empty string `""` | Falls back to default (valid) — no error | `status is not None` → validates → ValueError (correct: empty status is invalid) |
| `None` | N/A (defaults used) | `status is None` → skip validation (no change requested) |
| Valid value | Accepted | Accepted |
| Invalid value | ValueError | ValueError |

### Placement

**`create_task`:** After `config` reload, before `Task(...)` construction. Only validate when caller provides non-empty value (empty triggers default fallback via `or`).

```python
config = load_config(self._kanban_dir)
# -- validation block (new) --
valid_statuses = {s["name"] for s in config.statuses}
if status and status not in valid_statuses:
    msg = f"Invalid status {status!r}. Valid: {sorted(valid_statuses)}"
    raise ValueError(msg)
valid_priorities = set(config.priorities)
if priority and priority not in valid_priorities:
    msg = f"Invalid priority {priority!r}. Valid: {sorted(valid_priorities)}"
    raise ValueError(msg)
```

**`edit_task`:** After `_find_task_path`, before mutating `record`. Validate when not `None`.

```python
if status is not None:
    valid_statuses = {s["name"] for s in self._config.statuses}
    if status not in valid_statuses:
        msg = f"Invalid status {status!r}. Valid: {sorted(valid_statuses)}"
        raise ValueError(msg)
if priority is not None:
    valid_priorities = set(self._config.priorities)
    if priority not in valid_priorities:
        msg = f"Invalid priority {priority!r}. Valid: {sorted(valid_priorities)}"
        raise ValueError(msg)
```

**MCP `create_task` handler:** Wrap engine call in `try/except ValueError`.

**MCP `edit_task` handler:** Add `ValueError` to existing `FileNotFoundError` except clause.

### Caller Safety Check

All 20+ existing `engine.create_task`/`edit_task` callers use valid values or empty strings (default fallback). No breakage.

## 4. Recommendation

Inline validation replicating `move_task` pattern. 4 changes total: 2 in engine (create/edit), 2 in MCP adapter (create/edit handlers). ~20 LOC net addition.

Confidence: .92

Challenge: SKIPPED — T1 pattern replication from existing code, no architectural decisions.

## 5. Follow-up Tasks

No additional follow-up tasks needed — #814 is the implementation task itself.
