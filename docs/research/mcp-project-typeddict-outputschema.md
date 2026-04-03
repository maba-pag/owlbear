# TypedDict Return Types for mcp-project outputSchema

> **Owning task:** #542 — Add TypedDict return types for outputSchema specificity on mcp-project
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

mcp-project tools `project_info` and `project_list` return generic `dict` types
(`dict[str, Any] | str` and `list[dict[str, str]]`). FastMCP auto-generates
outputSchema from these annotations, but the schemas lack field-level specificity.
The question: does TypedDict produce precise field-level schemas, and what's the
correct implementation pattern?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | FastMCP `func_metadata.py` v1.26.0 | `.venv/.../mcp/server/fastmcp/utilities/func_metadata.py` L385-473 | 1.0 — TypedDict detection + `_create_model_from_typeddict` |
| 2 | Prior outputSchema research (#492) | `docs/research/knowledge-project-outputschema-annotations.md` v2 | .95 — field shapes, generic schema diagnosis |
| 3 | mcp-kanban KanbanTask pattern (#495) | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` L230-509 | .90 — BaseModel return + ToolError error path |
| 4 | mcp-project server.py | `packages/mcp-project/src/owlbear_mcp_project/server.py` L99-127 | 1.0 — current return types and error paths |
| 5 | Runtime verification (local) | `func_metadata()` calls in workspace | 1.0 — confirmed TypedDict and list[TypedDict] schemas |

## 3. Analysis

### 3a. Schema precision: current vs TypedDict (runtime verified)

| Tool | Current annotation | Current schema | TypedDict annotation | TypedDict schema |
|------|-------------------|----------------|---------------------|-----------------|
| `project_info` | `dict[str, Any] \| str` | `anyOf[{additionalProperties: true}, string]` | `ProjectInfoResult` | `{properties: {name: str, type: str, project_path: str, owlbear_path: str, created_at: str}, required: [all]}` |
| `project_list` | `list[dict[str, str]]` | `array of {additionalProperties: string}` | `list[ProjectListItem]` | `{result: {array of {name: str, path: str}}}` (wrapped) |

Both improvements verified at runtime via `func_metadata()` calls.

### 3b. TypedDict vs BaseModel design rationale

mcp-kanban uses BaseModel (`KanbanTask`) because it validates external process
output (`kanban-md --json` stdout). mcp-project data is **pre-validated** —
`project_info` reads from `OwlbearProjectFile(BaseModel)` (already validated),
and `project_list` constructs dicts from `path.stem` (always str) and
`data.get("path", "")` (str default). TypedDict is appropriate here:
lighter, no double-validation, and FastMCP handles schema generation identically.

### 3c. Error handling: ToolError for project_info

`project_info` currently returns `"error: ..."` string on missing config.
With a TypedDict return type, the union `ProjectInfoResult | str` defeats
schema precision (falls to wrapped generic). Solution: raise `ToolError`
for errors (same as mcp-kanban `show_task` pattern). `project_readme` retains
`return "error: ..."` — it returns `str` type regardless, so no schema conflict.

### 3d. list[TypedDict] wrapping

`list[ProjectListItem]` gets wrapped in `{result: [...]}` by FastMCP — same
wrapping as current `list[dict[str, str]]`. The inner items schema gains
field-level precision. No behavioral change for consumers.

## 4. Recommendation (.85 confidence)

Challenge: proceed — confidence in original: .85

Use TypedDict for both tools. Define `ProjectInfoResult` and `ProjectListItem`
as TypedDict classes in `server.py` (or a separate types module). Change
`project_info` error path from `return "error: ..."` to `raise ToolError(...)`.
Leave `project_list` empty-list return and `project_readme`/`project_structure`
unchanged.

**T1 — Autonomous.** No new capabilities, no architecture change. Type
annotation refinement on 2 existing tools with proven SDK support.

Design convention note: TypedDict for pre-validated/constructed data (mcp-project),
BaseModel for external process output validation (mcp-kanban).

## 5. Follow-up Tasks

Task #542 already exists with correct AC. No additional tasks needed — the AC
covers TypedDict definitions, ToolError migration, and runtime schema verification.
