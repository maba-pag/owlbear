# Add dep/parent/title params to edit_task, switch to JSON output

> **Owning task:** #476 — Add dep/parent/title params to edit_task, switch to JSON output
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The `edit_task` MCP tool exposes a subset of `kanban-md edit` flags. Four useful
flags are missing (`--add-dep`, `--remove-dep`, `--parent`, `--title`) and the
tool returns raw text instead of structured JSON. Task #476 asks whether adding
these params and switching to `--json` output is safe and how to implement it.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | kanban-md CLI v0.33.0 help | `kanban\kanban-md.exe edit --help` (local) | .95 |
| 2 | Existing expand-mcp-kanban research | `docs/research/expand-mcp-kanban-tools.md` (#56) | .90 |
| 3 | Current `edit_task` impl | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L188–233 | .95 |
| 4 | Current test coverage | `packages/mcp-kanban/tests/test_server.py` L253–330 | .90 |
| 5 | `show_task` JSON precedent | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L143 | .85 |

## 3. Analysis

### 3a. CLI flag verification

All four flags are confirmed present in `kanban-md edit --help` (v0.33.0):

| Flag | Type | Behavior |
|------|------|----------|
| `--add-dep ints` | int list | Appends to `depends_on` — can pass multiple IDs |
| `--remove-dep ints` | int list | Removes from `depends_on` |
| `--parent int` | single int | Sets parent task ID |
| `--title string` | string | Renames task title |
| `--json` | global flag | Returns edited task as JSON object |

Verified: `kanban\kanban-md.exe edit 476 --json --claim researcher` returns valid JSON.

### 3b. Parameter type design

The AC specifies `add_dep: int = 0` and `remove_dep: int = 0` (single int per
call). This is simpler than the CLI's `ints` (comma-separated list) but matches
the MCP convention of atomic operations. Agents call `edit_task` in a loop for
multiple deps — acceptable trade-off per KISS.

| Parameter | Python type | Default | CLI mapping |
|-----------|-------------|---------|-------------|
| `add_dep` | `int` | `0` | `--add-dep {value}` when > 0 |
| `remove_dep` | `int` | `0` | `--remove-dep {value}` when > 0 |
| `parent` | `int` | `0` | `--parent {value}` when > 0 |
| `title` | `str` | `""` | `--title {value}` when non-empty |

### 3c. JSON output switch

`show_task` already uses `--json` (source [5]). The pattern is simple: append
`"--json"` to the args list unconditionally. This is a non-breaking change —
callers currently parse stdout as opaque text; switching to JSON is strictly
more useful. The MCP tool description should note it returns JSON.

### 3d. Impact assessment

| Concern | Risk | Mitigation |
|---------|------|------------|
| Breaking existing callers | Low — text output was unstructured | JSON is strictly more parseable |
| `add_dep`/`remove_dep` as single int | None — atomic is simpler | Multi-dep = multiple calls |
| `parent: 0` sentinel | Low — task ID 0 is invalid | Consistent with `add_dep` pattern |
| Test coverage | Medium — 4 new params + JSON | 6 new test cases needed |

## 4. Recommendation (.90 confidence)

Implement as specified in the AC. The changes are mechanical — 4 new parameters
mapped to CLI flags using existing patterns, plus one unconditional `--json` arg.
No design decisions or trade-offs require user input.

Implementation approach:
1. Add 4 params to `edit_task` signature with defaults
2. Map `add_dep`/`remove_dep`/`parent` with `if value > 0` guards
3. Map `title` with `if value` guard (same as existing string flags)
4. Append `"--json"` to args unconditionally
5. Update docstring to mention JSON output
6. Add tests for each new param + JSON format
7. Update SKILL.md parameter table

## 5. outputSchema and structuredContent (addendum 2026-03-31)

### 5a. MCP structured output support

The MCP Python SDK v1.26.0 (installed) supports structured output natively:

| Component | Location | Behavior |
|-----------|----------|----------|
| `Tool.outputSchema` | `mcp.types.Tool` | JSON Schema defining structured output shape |
| `CallToolResult.structuredContent` | `mcp.types.CallToolResult` | Dict returned alongside `content` blocks |
| FastMCP auto-detection | `mcp.server.fastmcp.utilities.func_metadata` | Infers outputSchema from return type annotation |
| Output validation | `mcp.server.lowlevel.server` | Validates structuredContent against outputSchema |

Sources: MCP Python SDK README (structured output section), `mcp.types` module (L1310–1380),
FastMCP `func_metadata.py` (L180–330).

### 5b. Implementation approach comparison

| Approach | outputSchema quality | Reusability | Complexity |
|----------|---------------------|-------------|------------|
| Return `dict[str, Any]` | Generic (`type: object`, no properties) | Low | Minimal |
| Return `TypedDict` | Typed properties, required fields | High — shared across tools | Low |
| Return Pydantic `BaseModel` | Full validation + typed schema | High — shared across tools | Medium |

**Recommendation (.90 confidence): TypedDict** — provides a specific outputSchema
with named properties (id, title, status, etc.) while avoiding Pydantic overhead.
A single `KanbanTask` TypedDict can be shared across `edit_task`, `create_task`,
`show_task`, `move_task`, and `pick_task` (tasks #472, #475, #476, #477).

FastMCP auto-detects TypedDict return types and generates outputSchema automatically.
No explicit `structured_output=True` needed.

### 5c. Proposed KanbanTask TypedDict

```python
from typing import TypedDict


class KanbanTask(TypedDict, total=False):
    id: int
    title: str
    status: str
    priority: str
    tags: list[str]
    depends_on: list[int]
    claimed_by: str
    blocked: bool
    block_reason: str
    # total=False makes all fields optional (kanban-md may omit some)
```

The function would `json.loads()` the kanban-md `--json` output and return it
as a dict matching `KanbanTask`. FastMCP generates both `content` (text
serialization for backward compat) and `structuredContent` (validated dict).

### 5d. Impact on existing AC

No AC changes needed — the outputSchema update is additive:

| Original AC item | Impact |
|-------------------|--------|
| Add `--json` flag | Still needed — outputSchema validates the JSON output |
| Return type | Changes from `str` to `KanbanTask` (TypedDict) |
| Tests | Add: verify outputSchema in tool registration, verify structuredContent in response |
| SKILL.md | Add: note about structured output format |

## 6. Follow-up Tasks

Task #476 itself is the implementation task — no additional decomposition needed.
The AC is concrete and the scope is well-defined. Advancing to backlog.
