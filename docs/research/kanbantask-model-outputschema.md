# KanbanTask Model + outputSchema Validation

> **Owning task:** #495 — Define KanbanTask model + add outputSchema to show/move/pick
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #495 implements the KanbanTask Pydantic model and structured output for `show_task`,
`move_task`, `pick_task`. Prior research exists (docs/research/mcp-kanban-outputschema-annotations.md,
task #477). This validation confirms the prior design is still accurate after #489 completion
and identifies a field-set gap.

## 2. Sources Studied

| # | Source | URL/Path | Relevance |
|---|--------|----------|-----------|
| 1 | Prior research (#477) | docs/research/mcp-kanban-outputschema-annotations.md | 1.0 |
| 2 | FastMCP func_metadata.py (v1.26.0) | .venv/.../fastmcp/utilities/func_metadata.py L384-423 | 1.0 |
| 3 | MCP low-level server.py | .venv/.../mcp/server/lowlevel/server.py L555-577 | .95 |
| 4 | kanban-md v0.33.0 actual JSON output | Local: `kanban-md show --json` across multiple tasks | 1.0 |
| 5 | kanban-md JSON schemas reference | skills/kanban-md/references/json-schemas.md | .90 |
| 6 | FastMCP exceptions.py | .venv/.../fastmcp/exceptions.py L16-18 | .85 |

## 3. Analysis

### 3.1 Prior Research Validation

The approach from #477 research remains valid:
- FastMCP BaseModel return type → auto outputSchema + structuredContent (confirmed in func_metadata.py L384-386)
- ToolError → caught by low-level server → `isError: true` response (confirmed in lowlevel/server.py L587)
- ToolAnnotations already applied to all tools (#494 archived, confirmed in server.py)
- Dependency #489 (--json for move/pick) is archived — all 3 target tools now output JSON

### 3.2 Model Field Gap (CORRECTION)

The proposed model in prior research is missing 3 fields present in actual kanban-md output:

| Field | In proposed? | In actual output? | Type | Notes |
|-------|-------------|-------------------|------|-------|
| `class` | No | Always present | `str` | e.g., "standard" — required field |
| `claimed_by` | No | When claimed | `str \| None` | Dynamic agent claim (distinct from `assignee`) |
| `claimed_at` | No | When claimed | `str \| None` | ISO timestamp of claim |
| `assignee` | Yes | When set | `str \| None` | Static assignment — correct in proposed model |

**Complete field superset** (verified across all tasks on board):
`id`, `title`, `status`, `priority`, `created`, `updated`, `class` (always present);
`started`, `completed`, `assignee`, `claimed_by`, `claimed_at`, `tags`, `due`,
`estimate`, `parent`, `depends_on`, `blocked`, `block_reason`, `body`, `file` (omitempty).

### 3.3 Scope Adjustment: start_work

`start_work` injects a synthetic `claim_name` field not in the kanban-md schema.
Returning `KanbanTask` from `start_work` would lose this field. Two approaches:

| Approach | Pros | Cons |
|----------|------|------|
| Keep `start_work -> str` | No model change, `claim_name` preserved | Inconsistent with other structured tools |
| Create `StartWorkResult(KanbanTask)` subclass | Typed, adds `claim_name` field | Extra model for one tool |

**Recommendation (.85 confidence):** Keep `start_work -> str` for now. The AC explicitly
scopes to show/move/pick. A follow-up task can add a `StartWorkResult` model if needed.

### 3.4 ToolError Behavioral Impact

Current: `return f"error: {stderr.strip()}"` — returned as successful text content.
After: `raise ToolError(stderr)` — returned as `isError: true` response.

Impact is low — callers are LLM agents, not programmatic clients. The MCP skill's error
handling docs need updating. Pre-approved via #477 research.

## 4. Recommendation (.90 confidence)

The task AC is well-specified and ready for development. One correction needed:

**Add 3 missing fields to KanbanTask model:** `class_` (aliased from `class`), `claimed_by`, `claimed_at`.

Note: `class` is a Python reserved word — use `class_: str = Field(alias="class")` with
`model_config = ConfigDict(populate_by_name=True)`.

Classification: **T1 (Autonomous)** — implements already-researched, pre-approved design.
No T3 triggers apply. ToolError change was approved in #477 research.

## 5. Follow-up Tasks

No new tasks needed — #495 AC is complete and actionable. The field correction
is a refinement, not a new task. Builder should reference this doc for the corrected model.
