# Refactor mcp-knowledge Tools to Return Structured Data

> **Owning task:** #507 — Refactor mcp-knowledge tools to return structured data
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #507 proposes changing 4 mcp-knowledge tools from returning formatted
bullet strings (`-> str`) to structured data (`-> list[dict]` / `-> dict`).
This aligns with the pattern already established by mcp-project (`project_info`
returns `dict`, `project_list` returns `list[dict]`). Research question: is
the refactor feasible, what are the risks, and how does outputSchema behave?

## 2. Sources Studied

| Source | URL / Path | What | Relevance |
|--------|-----------|------|-----------|
| FastMCP docs — Structured Output | gofastmcp.com/servers/tools#structured-output | Auto `structuredContent` + `content` for typed returns; `list` needs annotation for schema | 1.0 |
| FastMCP docs — Output Schemas | gofastmcp.com/servers/tools#output-schemas | Auto-generation from return type; primitives/lists wrapped in `{"result": ...}` | 1.0 |
| Parent research #496 | docs/research/mcp-server-error-return-standardization.md | Return type audit, T1 classification (.90 confidence) | 1.0 |
| Prior research #492 | docs/research/knowledge-project-outputschema-annotations.md | SDK v1.26 auto-generates outputSchema; no manual hack needed | 0.9 |
| mcp-knowledge server.py | packages/mcp-knowledge/src/.../server.py | Current `-> str` tools, bullet formatting from Pydantic models | 1.0 |
| mcp-project server.py | packages/mcp-project/src/.../server.py | Reference pattern: `-> dict[str, Any] \| str`, `-> list[dict[str, str]]` | 1.0 |
| Knowledge models.py | packages/knowledge/src/.../models.py | Entity, KnowledgeSource Pydantic models with exact field names | 0.9 |
| KnowledgeQueryService | packages/knowledge/src/.../query_service.py | `StructuredSearchResult` model: doc_id, title, score, snippet, entity_type, scope | 1.0 |

## 3. Analysis

### 3a. Current Implementation vs Target

| Tool | Current return | Source model | Target dict keys | Change size |
|------|---------------|-------------|-----------------|-------------|
| `search_knowledge` | `str` bullet list | `StructuredSearchResult` | `{title, score, snippet}` | ~3 lines |
| `list_sources` | `str` bullet list | `KnowledgeSource` | `{name, source_type, scope}` | ~3 lines |
| `list_entities` | `str` bullet list + header | `Entity` | `{name, entity_type, description}` | ~5 lines |
| `get_stats` | `str` sentence | `tuple[int,int,int]` | `{documents, entities, edges}` | ~2 lines |

All 4 tools already fetch Pydantic models or tuples, then format them as
strings. The refactor replaces string formatting with dict comprehensions.

### 3b. outputSchema Auto-Generation

FastMCP v1.26+ auto-generates `outputSchema` from return type annotations.
For `list[dict]` returns, the SDK wraps the result:

- `-> list[dict[str, Any]]` generates `{"result": {"type": "array", "items": {"type": "object"}}}`
- `-> dict[str, int]` generates `{"result": {"type": "object", ...}}`

Both `content` (JSON text) and `structuredContent` (parsed JSON) are sent,
maintaining backward compatibility. Verified by FastMCP docs: "All results
always become traditional content blocks for backward compatibility."

**Schema specificity:** `dict[str, Any]` schemas don't enumerate key names.
For richer schemas, TypedDict or Pydantic models could be used, but this is
YAGNI — the AC specifies `list[dict]` which matches the mcp-project pattern.

### 3c. Empty Result Handling

| Tool | Current empty behavior | Target behavior |
|------|----------------------|-----------------|
| `search_knowledge` | `"No relevant knowledge found."` | `[]` (empty list) |
| `list_sources` | `"No sources found."` | `[]` (empty list) |
| `list_entities` | `"No entities found."` | `[]` (empty list) |
| `get_stats` | N/A (always has counts) | `{"documents": 0, ...}` |

Empty lists are the correct structured representation for "no results."

### 3d. Error Cases (Deferred to #506)

Service unavailability (`qs is None`) and validation errors (`Invalid
entity_type`) return error strings. These stay as `str` returns via union
types (`list[dict] | str`) or separate error handling. Error prefix
standardization is in sibling task #506.

### 3e. Test Impact

| Test file | What it tests | Assertions to update |
|-----------|--------------|---------------------|
| `packages/mcp-knowledge/tests/test_search_v2.py` | `search_knowledge` server.py | 6x `isinstance(result, str)`, bullet format checks |
| `packages/mcp-knowledge/tests/test_list_sources.py` | `list_sources` | `isinstance(result, str)`, `"No sources found."` |
| `packages/mcp-knowledge/tests/test_ingest_graph_tools.py` | `list_entities`, `get_stats` | `isinstance(output, str)`, string content checks |
| `packages/mcp-knowledge/tests/test_search_knowledge.py` | `tools.py` (separate module) | Out of scope — different module |

### 3f. Pagination in list_entities

The current `list_entities` includes a header string
`"Entities (0-50 of 100):"`. For structured returns, pagination metadata
should be handled separately — the returned `list[dict]` contains only the
page slice. Total count can be added as a wrapper dict later if needed (YAGNI).

## 4. Recommendation (.90 confidence)

**T1 — Autonomous.** This is a consistency refactor following the established
mcp-project pattern. No new capabilities, no architecture changes, no pipeline
modifications. Risk is low — each tool change is independently testable.

Proceed with implementation as stated in the AC. Two minor considerations
for the builder:

1. **Union return types** for error cases: use `list[dict[str, Any]] | str`
   (matching mcp-project's `project_info` pattern) so error strings remain
   valid returns. The `error:` prefix standardization (#506) handles the
   string format.
2. **Empty results**: return `[]` instead of sentinel strings for empty data.

## 5. Follow-up Tasks

No new tasks needed — #507 AC is comprehensive and well-scoped. The error
prefix work is covered by sibling task #506. The test update AC item covers
all affected test files identified in §3e.
