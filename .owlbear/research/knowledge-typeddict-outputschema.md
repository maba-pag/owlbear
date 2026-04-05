# TypedDict Return Types for mcp-knowledge outputSchema

> **Owning task:** #541 — Add TypedDict return types for outputSchema specificity on mcp-knowledge
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

mcp-knowledge tools return `dict[str, Any]` and `dict[str, str]`, producing generic
outputSchema without field names. Can TypedDict annotations generate field-level
outputSchema via FastMCP auto-generation?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | FastMCP `func_metadata.py` (SDK v1.26+) | `.venv/.../fastmcp/utilities/func_metadata.py` L385 | 1.0 — TypedDict Case 2 handling |
| 2 | FastMCP `_create_model_from_typeddict` | `.venv/.../fastmcp/utilities/func_metadata.py` L455–472 | 1.0 — TypedDict-to-Pydantic conversion |
| 3 | FastMCP `convert_result` | `.venv/.../fastmcp/utilities/func_metadata.py` L100–131 | 0.9 — wrap_output + validation behavior |
| 4 | mcp-knowledge `server.py` | `packages/mcp-knowledge/src/.../server.py` | 1.0 — current return types |
| 5 | mcp-kanban `server.py` L197–230 | `packages/mcp-kanban/src/.../server.py` | 0.8 — manual schema override pattern |
| 6 | Prior research (#492 v2) | `docs/research/knowledge-project-outputschema-annotations.md` | 1.0 — field shapes, annotation status |
| 7 | Runtime verification | `uv run python -c` (this task) | 1.0 — confirmed both baseline and TypedDict schemas |

## 3. Analysis

### 3a. Current schema quality (verified at runtime)

| Tool | Current return type | Schema quality |
|------|-------------------|---------------|
| search_knowledge | `list[dict[str, Any]] \| str` | Generic: `additionalProperties: true` — no field names |
| list_sources | `list[dict[str, str]]` | Generic: `additionalProperties: {type: string}` — no field names |
| list_entities | `list[dict[str, Any]] \| str` | Generic: `additionalProperties: true` — no field names |
| get_stats | `dict[str, int]` | Generic: `additionalProperties: {type: integer}` — **no** field names |
| ingest_document | `str` | Good: `{result: string}` — no change needed |

### 3b. TypedDict schema quality (verified at runtime)

Defined `SearchResult(TypedDict)` with `title: str, score: float, snippet: str` and
tested `list[SearchResult] | str`. FastMCP wraps in `{result: ...}` (standard for
generic return types) but items contain full `$defs/SearchResult` with properties:

```
{title: {type: string}, score: {type: number}, snippet: {type: string}}
```

**Key mechanics (FastMCP func_metadata.py):**
- Direct TypedDict → Case 2 → `_create_model_from_typeddict` → no wrapping
- `list[TypedDict]` → GenericAlias → `_create_wrapped_model` → `{result: [...]}`
- `list[TypedDict] | str` → union → wrapped → `{result: anyOf[array, string]}`
- Wrapping is inherent to ALL generic return types — BaseModel would wrap identically

### 3c. TypedDict vs alternatives

| Criterion | TypedDict | BaseModel | Manual fn_metadata override |
|-----------|-----------|-----------|----------------------------|
| Field-level schema | Yes | Yes | Yes |
| list wrapping | `{result: [...]}` | `{result: [...]}` | None (full control) |
| Direct return wrapping | None | None | N/A |
| Boilerplate | Minimal (3-5 fields) | ConfigDict + Field defs | Manual JSON schema |
| Maintenance | Auto-synced with code | Auto-synced with code | Can drift from code |
| Output validation | Yes (Pydantic validates) | Yes (Pydantic validates) | No runtime check |
| Reuse internal models? | N/A | No — internal models have extra fields | N/A |

Existing internal BaseModels (`StructuredSearchResult`, `Entity`, `KnowledgeSource`)
have 6–12 fields each. MCP tools expose 3 fields per tool. Reusing internal models
would leak internal structure across the MCP boundary.

### 3d. Validation tightening — feature, not risk

TypedDict annotations add Pydantic validation on tool output. This catches upstream
data bugs (e.g., a None score) at the MCP boundary rather than passing malformed data
to clients. Upstream code (`query_service.query()` returns `StructuredSearchResult`)
already guarantees field existence, so validation only catches code-level bugs.

## 4. Recommendation (.85 confidence)

Challenge: reconsider — confidence in original: .65. Addressed all 5 concerns;
revised confidence from .90 to .85 (acknowledged validation tightening and wrapping).

**Use TypedDict annotations.** Minimal boilerplate, auto-generated field-level schema,
desirable output validation. The `{result: ...}` wrapping for list returns is standard
FastMCP behavior — consistent with SDK, not a TypedDict-specific issue.

**T1 — Autonomous.** Refines existing return types. No new capabilities, no architecture
changes, no agent/skill/pipeline modifications.

**Critical implementation constraints:**

1. TypedDicts MUST be defined at **module scope**, NOT under `if TYPE_CHECKING:`.
   `from __future__ import annotations` makes annotations lazy; FastMCP resolves
   them via `inspect.signature(func, eval_str=True)` at registration time.
2. `get_stats` NEEDS TypedDict — current `dict[str, int]` does NOT list field names.
3. Schema-pinning tests should assert specific field names in `fn_metadata.output_schema`
   to prevent regression.

## 5. Follow-up Tasks

No new tasks needed — #541 AC already covers the implementation. Implementation
constraints above should be incorporated by the architect during AC refinement.
