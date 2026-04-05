# Add status and parent params to create_task, switch to JSON output

> **Owning task:** #475 — Add status and parent params to create_task, switch to JSON output
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

The `create_task` MCP tool currently lacks `status` and `parent` parameters, and returns raw text output. Agents (especially pipeline agents creating follow-up tasks at `ideation`) must use `kanban-md.exe` directly to set status on create, and the text return format cannot be parsed reliably. What changes are needed to add these parameters and switch to JSON output?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| kanban-md v0.33.0 `create --help` | Local binary | 1.0 — authoritative CLI flag reference |
| kanban-md `create --json` output | Local binary (tested) | 1.0 — confirmed JSON schema with all fields |
| mcp-kanban server.py (current) | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L148-176 | 1.0 — current implementation |
| mcp-kanban test_server.py | `packages/mcp-kanban/tests/test_server.py` L212-244 | 1.0 — existing test patterns |
| show_task `--json` pattern | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L141 | 1.0 — precedent for `--json` in same codebase |
| Modernize list_tasks research | `docs/research/modernize-list-tasks.md` | 0.9 — JSON output design precedent |
| FastMCP `func_metadata.py` | `.venv/Lib/site-packages/mcp/server/fastmcp/utilities/func_metadata.py` L180-330 | 1.0 — outputSchema auto-detection |
| MCP Python SDK `mcp.types` | `.venv/Lib/site-packages/mcp/types.py` L1310-1380 | 1.0 — Tool.outputSchema, CallToolResult.structuredContent |
| outputSchema research (#477) | `docs/research/mcp-kanban-outputschema-annotations.md` | 0.95 — KanbanTask model, error handling pattern |
| MCP Spec 2025-11-25 Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 — ToolError / isError specification |

## 3. Analysis

### 3.1 CLI flag availability (kanban-md v0.33.0)

All three flags exist and work correctly:

| Flag | kanban-md support | Currently exposed in MCP | Type |
|------|-------------------|-------------------------|------|
| `--status` | Yes | No | `str` |
| `--parent` | Yes | No | `int` |
| `--json` | Yes (global flag) | No | global |

No kanban-md changes needed — all flags ship with v0.33.0.

### 3.2 Verified JSON output from `create --json`

Tested: `kanban-md create "TITLE" --json --status ideation --parent 475` returns:

```json
{
  "id": 480,
  "title": "TEST-RESEARCHER-475-DELETE-ME",
  "status": "ideation",
  "priority": "important",
  "created": "2026-03-31T06:19:26+02:00",
  "updated": "2026-03-31T06:19:26+02:00",
  "parent": 475,
  "class": "standard",
  "file": "C:\\...\\kanban\\tasks\\480-test-researcher-475-delete-me.md"
}
```

The schema includes `id`, `title`, `status`, `priority`, `parent`, `class`, `created`, `updated`, `file`.

### 3.3 Implementation approach

The change follows the exact same pattern as existing optional parameters:

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| `status` param | `status: str = ""` — if non-empty, pass `--status` | Matches `priority`, `tags` pattern |
| `parent` param | `parent: int = 0` — if > 0, pass `--parent` | Int type matches CLI `--parent int`; 0 = unset |
| JSON output | Append `"--json"` to args unconditionally | Matches `show_task` precedent (L141) |
| Return value | Return raw JSON stdout | Agents parse JSON directly |

Complexity: ~6 LOC added to `create_task`. No new functions, no new dependencies, no architectural changes.

### 3.4 Test strategy

| Test | What it verifies |
|------|-----------------|
| Unit: create with `status="backlog"` | `--status backlog` in args |
| Unit: create with `parent=42` | `--parent 42` in args |
| Unit: create with `parent=0` | `--parent` NOT in args |
| Unit: `--json` always present | `--json` in args for any create call |
| Integration: create + show roundtrip with status | Created task has expected status |
| Integration: create + show with parent | Created task has parent field |

Existing test patterns in `test_server.py` (args-checking with `mock_run.call_args`) and `test_integration.py` (roundtrip with real binary) are directly reusable.

### 3.5 outputSchema and structuredContent for create_task

After `--json` is added (§3.4), `create_task` returns a JSON task object. Adding `outputSchema` makes this structured for MCP clients.

**How FastMCP derives outputSchema** (confirmed in `func_metadata.py` L180–330, `mcp.types.Tool` L1310):

| Return type | Schema quality | Notes |
|-------------|---------------|-------|
| `BaseModel` subclass | Precise field-level | Best option — auto-validated |
| `TypedDict` | Precise field-level | Converted to Pydantic internally |
| `str` (current) | No schema | Current state — no structured output |

Source: FastMCP `func_metadata.py`, MCP Python SDK v1.26.0 `mcp.types.Tool.outputSchema`.

**Shared KanbanTask model:** Task #495 defines a `KanbanTask(BaseModel)` in `models.py` matching the kanban-md JSON schema (see `skills/kanban-md/references/json-schemas.md`). Fields: `id`, `title`, `status`, `priority`, `created`, `updated`, plus optional `started`, `completed`, `assignee`, `tags`, `due`, `estimate`, `parent`, `depends_on`, `blocked`, `block_reason`, `body`, `file`.

Source: `docs/research/mcp-kanban-outputschema-annotations.md` (§3.1, §3.5).

**Implementation for create_task** (after #482 adds `--json` and #495 defines model):

```python
async def create_task(...) -> KanbanTask:
    ...
    if rc != 0:
        raise ToolError(stderr.strip())  # from mcp.server.fastmcp.exceptions
    return KanbanTask.model_validate_json(stdout)
```

FastMCP auto-generates `outputSchema` from the `KanbanTask` return type and produces both `content` (text) and `structuredContent` (validated dict) in `CallToolResult`.

**Error handling change:** `raise ToolError(msg)` replaces `return "error: ..."`. This is the MCP-specified error mechanism (`isError: true` in response). Source: MCP spec 2025-11-25 Tools, `mcp.server.fastmcp.exceptions.ToolError`.

**Dependency chain:** #482 (add `--json`) → #495 (define model + change return type). Task #495 currently covers `show/move/pick` — it should be expanded to include `create_task` and `edit_task` once their `--json` switches land (#482 and #472 respectively). The architect should assess this scope expansion.

## 4. Recommendation (.95 confidence)

**Core changes** (status, parent, --json): Straightforward — add `status: str = ""` and `parent: int = 0` params, append `--json` unconditionally. Follows established patterns. No design choices.

**outputSchema** (.90 confidence): Use the shared `KanbanTask` model from #495. Implementation is ~2 LOC change (return type + `model_validate_json`). Depends on #495 landing first. Recommend expanding #495 to cover `create_task` alongside `show/move/pick`.

**Risk:** Minimal. `parent` type uses `int` with `0` sentinel (matches CLI's `--parent int`). The `ToolError` switch is low-risk since callers are LLM agents.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement status, parent, JSON output for create_task MCP tool" --priority needed --status ideation --tags "scope:mcp,type:build,phase-2" --depends-on 475 --body "## Acceptance Criteria\n\n- [ ] Add status: str = '' parameter to create_task; when non-empty, pass --status\n- [ ] Add parent: int = 0 parameter; when > 0, pass --parent {value}\n- [ ] Append --json to create_task args unconditionally\n- [ ] Unit tests: status flag, parent flag, parent=0 no flag, --json always present\n- [ ] Integration tests: create+show roundtrip with status override, create+show with parent\n- [ ] Update skills/mcp-kanban/SKILL.md create_task row to include status, parent params\n\n## Implementation Notes\n\nSee docs/research/create-task-status-parent-json.md for full analysis.\n\nPattern: follow existing optional-param style (L148-176 in server.py).\nshow_task already uses --json (L141) — same approach for create.\nparent uses int type with 0 sentinel (CLI expects --parent int)."
```
