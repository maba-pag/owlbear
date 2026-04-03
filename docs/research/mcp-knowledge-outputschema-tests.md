# TypedDict outputSchema Tests for mcp-knowledge

> **Owning task:** #544 — Test: TypedDict return types for mcp-knowledge outputSchema
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #544 is the TDD RED test task for #541 (implementation). It needs tests
that verify `fn_metadata.output_schema` produces field-level definitions when
mcp-knowledge tool return types are changed from generic `dict[str, Any]` to
TypedDict. Tests must fail until #541 is implemented.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | FastMCP func_metadata | `.venv/.../mcp/server/fastmcp/utilities/func_metadata.py` | 1.0 — schema generation from TypedDict |
| 2 | mcp-kanban test_server.py | `packages/mcp-kanban/tests/test_server.py` L1104-1125 | 1.0 — reference test pattern |
| 3 | Runtime verification script | `docs/scratch/544-schema-test.py` (deleted) | 1.0 — empirical schema shapes |
| 4 | Research doc (v2) | `docs/research/knowledge-project-outputschema-annotations.md` | 0.9 — parent research |

## 3. Analysis

### Schema shapes by return type (verified empirically)

| Return type | Schema shape | Field location |
|-------------|-------------|----------------|
| `TypedDict` direct | Unwrapped: top-level `properties` with field defs | `schema["properties"]` |
| `list[TypedDict]` | Wrapped: `{result: {items: {$ref: #/$defs/T}}}` | `schema["$defs"]["T"]["properties"]` |
| `list[TypedDict] \| str` | Wrapped: `{result: {anyOf: [{items: {$ref}}, {type: string}]}}` | Same `$defs` location |
| `str` | Wrapped: `{result: {type: string}}` | No field-level info (as expected) |

### Current vs target (per AC)

| Tool | Current schema | Target schema | AC |
|------|---------------|---------------|-----|
| search_knowledge | `anyOf[array(generic), string]` | `$defs.SearchResult` with title/score/snippet | AC1 |
| list_sources | `array(generic object)` | `$defs.SourceInfo` with name/source_type/scope | AC2 |
| list_entities | `anyOf[array(generic), string]` | `$defs.EntityInfo` with name/entity_type/description | AC3 |
| get_stats | `additionalProperties: int` | Top-level properties: documents/entities/edges | AC4 |
| ingest_document | `{result: string}` | Unchanged (wrapped str) | AC5 |
| ingest_document annotations | `destructiveHint=None` | `destructiveHint=False` | AC6 |

### Test pattern

Access tool objects via `mcp._tool_manager._tools` (same as mcp-kanban). Key
assertions: check `fn_metadata.output_schema` for `$defs` (list-returning) or
top-level `properties` (direct TypedDict). AC7 verifies importability via
`from owlbear_mcp_knowledge.server import SearchResult, SourceInfo, EntityInfo`.

### Feasibility

(.95 confidence) All TypedDict schema shapes verified at runtime. The test
pattern is established in mcp-kanban. No blockers.

## 4. Recommendation

No recommendation needed — this is a test task with fully specified AC.
Tier classification: **T1 — Autonomous** (test code only, no new capabilities).

Challenge: SKIP — info-only research, no recommendation to challenge.

## 5. Follow-up Tasks

No new follow-up tasks needed. #544 → #541 dependency chain already exists.
