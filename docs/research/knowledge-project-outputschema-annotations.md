# outputSchema and Tool Annotations for Knowledge & Project MCP Servers

> **Owning task:** #492 — Add outputSchema and tool annotations to knowledge and project MCP servers
> **Date:** 2026-03-31, updated 2026-04-02 **Status:** Complete (v3)

## 1. Context and Question

Task #492 asks to apply MCP best practices (outputSchema + ToolAnnotations) to
`mcp-knowledge` and `mcp-project`, matching the pattern established in `mcp-kanban`
(#472–#477). Child tasks #501 and #502 completed ToolAnnotations. v2 corrected
factual errors. This v3 update reflects current board state (2026-04-02) and
integrates challenger feedback on AC gaps.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | MCP Spec 2025-11-25 — Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 — outputSchema, structuredContent, ToolAnnotations |
| 2 | MCP Spec 2025-11-25 — Schema | modelcontextprotocol.io/specification/2025-11-25/schema | 1.0 — ToolAnnotations fields: readOnly/destructive/idempotent/openWorld |
| 3 | FastMCP SDK v1.26+ internals | `.venv/.../mcp/server/fastmcp/tools/base.py` | 1.0 — auto-generation from TypedDict return types |
| 4 | MCP low-level Server | `.venv/.../mcp/server/lowlevel/server.py` | 1.0 — listChanged via NotificationOptions |
| 5 | mcp-kanban server.py | `packages/mcp-kanban/src/.../server.py` | 1.0 — reference implementation |
| 6 | mcp-knowledge server.py | `packages/mcp-knowledge/src/.../server.py` | 1.0 — current state verification |
| 7 | mcp-project server.py | `packages/mcp-project/src/.../server.py` | 1.0 — current state verification |

## 3. Analysis

### 3a. ToolAnnotations — COMPLETE

All annotations correctly set (verified in source, 2026-04-02):

| Server | Tool | readOnly | idempotent | destructive |
|--------|------|:--------:|:----------:|:-----------:|
| knowledge | search_knowledge | True | True | — |
| knowledge | list_sources | True | True | — |
| knowledge | ingest_document | False | — | — (*gap*) |
| knowledge | list_entities | True | True | — |
| knowledge | get_stats | True | True | — |
| project | project_info | True | True | — |
| project | project_list | True | True | — |
| project | project_readme | True | True | — |
| project | project_structure | True | True | — |

**Gap:** `ingest_document` has `readOnlyHint=False` but lacks explicit
`destructiveHint=False`. The mcp-kanban reference sets `destructiveHint=False`
on all write tools. This is tracked as AC6 in #541 test file.

### 3b. outputSchema — partially done

| Server | Tool | Return type | Schema state |
|--------|------|-------------|-------------|
| knowledge | search_knowledge | `list[dict[str, Any]] \| str` | Generic (needs TypedDict) |
| knowledge | list_sources | `list[dict[str, str]] \| str` | Generic (needs TypedDict) |
| knowledge | ingest_document | `str` | Adequate (`{result: string}`) |
| knowledge | list_entities | `list[dict[str, Any]] \| str` | Generic (needs TypedDict) |
| knowledge | get_stats | `dict[str, int] \| str` | Generic (needs TypedDict) |
| project | project_info | `ProjectInfoResult` | Complete (TypedDict) |
| project | project_list | `list[ProjectListItem]` | Complete (manual override) |
| project | project_readme | `str` | Adequate (`{result: string}`) |
| project | project_structure | `str` | Adequate (`{result: string}`) |

**mcp-project:** Fully done. TypedDicts already implemented (commit df21f2f).
String-returning tools (`project_readme`, `project_structure`) have adequate
auto-generated schemas — the AC doesn't require anything beyond `type: string`.

**mcp-knowledge:** 4 tools need TypedDict return types. The `| str` union on
error paths must be removed (replaced by `ToolError` exceptions, matching the
`project_info` pattern). This applies to `search_knowledge`, `list_sources`,
`list_entities`, and `get_stats` — all have error guard paths returning strings.

### 3c. listChanged — correct at false

**AC correction needed:** #492 AC says "listChanged=true". The verified state is
`listChanged=false` on all servers. This is correct — none dynamically add/remove
tools at runtime. Setting `true` would be wrong (requires change notifications).
The AC line is factually incorrect and should be corrected.

### 3d. knowledge-ops SKILL.md

Already documents field names accurately. May need minor update after #541 lands
if TypedDict names appear in tool signatures (currently does not reference types).

## 4. Recommendation (.80 confidence)

Challenge: reconsider (confidence in original: .68). Revised after integrating
C1 (listChanged AC gap), C4 (destructiveHint tracking), C6 (get_stats union
removal). All valid and addressed in this v3.

**Approach: TypedDict return types for mcp-knowledge** — Replace `dict[str, Any]`
unions with TypedDict classes + ToolError for error paths. Same pattern as
mcp-project's completed implementation. FastMCP auto-generates precise schemas.

**T1 — Autonomous.** No new capabilities, no architecture changes. Refines
existing return types and adds missing annotation hint.

### Task status assessment

| Task | Status | Assessment |
|------|--------|-----------|
| #501 | archived | ToolAnnotations for mcp-knowledge — done |
| #502 | archived | ToolAnnotations for mcp-project — done |
| #512 | blocked | Duplicate of #502 — should be archived |
| #544 | archived | Tests for mcp-knowledge TypedDicts — done |
| #541 | todo | TypedDict for mcp-knowledge — READY |
| #543 | blocked | Tests for mcp-project TypedDict — stuck (AC4) |
| #542 | todo | TypedDict for mcp-project — deps blocked |

**#543/#542:** Implementation committed, 15 tests pass at .97 confidence. AC4
("all tests fail in RED") is structurally unsatisfiable. Architect should mark
AC4 N/A and unblock, allowing normal pipeline completion.

**#512:** Duplicate of completed #502. Should be archived.

## 5. Follow-up Tasks

No new tasks needed — #541 covers remaining mcp-knowledge TypedDict work
(including destructiveHint on ingest_document as AC6). #543/#542 need architect
unblock, not new tasks. AC correction for listChanged noted in task body.
