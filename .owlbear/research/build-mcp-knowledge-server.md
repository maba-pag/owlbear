# Build mcp-knowledge Server

> **Owning task:** #16 — Build mcp-knowledge server
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #16 asks us to build an MCP server wrapping the knowledge engine (hybrid graph+vector search, ingest, source management) as MCP tools. Dependencies #2 (MCP Python SDK) and #15 (extract knowledge engine) are both archived. The question: what is the correct architecture, what can be built now, and what is blocked?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| mcp-kanban server.py (internal) | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 1.0 — exact reference pattern |
| MCP Python SDK README | `https://github.com/modelcontextprotocol/python-sdk` | 0.9 — decorator API, lifespan, resource patterns |
| MCP Python SDK research doc (internal) | `docs/research/mcp-python-sdk.md` | 0.9 — SDK deep-dive from task #2 |
| MCP reference Memory server | `https://github.com/modelcontextprotocol/servers/tree/main/src/memory` | 0.7 — knowledge-graph MCP prior art |
| Existing TDD tests (internal) | `packages/mcp-knowledge/tests/test_*.py` | 1.0 — defines the test contract |
| v1 IngestPipeline (internal) | `v1/src/owlbear/memory/knowledge/ingest.py` | 0.8 — prior art for ingest tool |
| owlbear_knowledge API (internal) | `packages/knowledge/src/owlbear_knowledge/` | 1.0 — the API we're wrapping |

## 3. Analysis

### 3a. Architecture Pattern (consensus from 3 sources)

The mcp-kanban server, MCP SDK docs, and SDK research doc all agree on the same pattern:

| Component | Pattern | Source |
|-----------|---------|--------|
| Server init | `mcp = FastMCP("name", lifespan=app_lifespan)` | mcp-kanban, SDK README |
| Lifespan | `async def app_lifespan(server)` yields `AppContext` dataclass | mcp-kanban, SDK README |
| Tools | `@mcp.tool()` async functions, access ctx via `ctx.request_context.lifespan_context` | mcp-kanban, SDK README |
| Resources | `@mcp.resource("uri://path")` decorator | SDK README |
| Entry point | `__main__.py`: `from .server import mcp; mcp.run()` | mcp-kanban |
| Transport | stdio (KISS, single-user) | mcp-kanban, copilot-instructions |

**Recommendation (.95):** Follow mcp-kanban pattern exactly. No deviations needed.

### 3b. Knowledge API Availability

| Tool/Resource | Required API | Available in owlbear_knowledge? | Status |
|---------------|-------------|--------------------------------|--------|
| `search_knowledge` | `KnowledgeQueryService.query()` | Yes (query_service.py) | Ready |
| `list_entities` | `GraphStore.list_entities()` | Yes (graph_store.py) | Ready |
| `list_sources` | `KnowledgeSourceStore.list_all()` | Yes (source_store.py) | Ready |
| `get_stats` | `GraphStore.get_counts()` | **No** — method doesn't exist | Blocked |
| `ingest_document` | `IngestPipeline.ingest_text()` | **No** — not extracted from v1 | Blocked (#33) |
| `knowledge://stats` | doc/entity/edge counts | **No** — needs `get_counts()` | Blocked |

### 3c. Dependency Gap

Tests in `test_ingest_graph_tools.py` (TDD RED from task #55) import:

- `DocumentStore` — does not exist in v2. Not found anywhere.
- `IngestPipeline` / `IngestResult` — exist in v1 (`v1/src/owlbear/memory/knowledge/ingest.py`) but extraction is task #33 scope
- `GraphStore.get_counts()` — method not present. Needs ~10 LOC addition to `graph_store.py`

Task #33 (extract entity extraction + graph builders + ingest pipeline) is at ideation, depends on #32 (extract vector store + embedding pipeline, at backlog). Both must complete before ingest tools can be built.

### 3d. Implementation Strategy

| Option | Description | Pros | Cons | KISS/YAGNI |
|--------|-------------|------|------|------------|
| A. Wait for #33 | Don't build until full API available | Clean, all tests pass | Blocks all progress | Neutral |
| B. Phased build | Build search+list+stats now, defer ingest | Unblocks 60% of AC, TDD-compatible | Ingest tests stay red | High |
| C. Protocol stubs | Define IngestPipeline Protocol in mcp-knowledge | Can write all code now | Over-engineering, duplicates #33 | Low |

**Recommendation (.85):** Option B — phased build. Build server.py with lifespan, search_knowledge, list_entities, list_sources tools, and knowledge://stats resource. `get_counts()` is a small addition (~10 LOC) that can be added as a subtask. Mark ingest tests as `xfail` until #33 delivers IngestPipeline. Update `depends_on` to include #33 for the ingest phase.

### 3e. Configuration

Both mcp-kanban and test expectations align on env-var config:

| Env Var | Purpose | Default |
|---------|---------|---------|
| `OWLBEAR_KB_PATH` | SQLite + Qdrant data directory | `data/knowledge/` |
| `OWLBEAR_MODEL` | LLM model for entity extraction | (none — ingest phase) |

### 3f. pyproject.toml Fix

Current `pyproject.toml` is missing the `owlbear-knowledge` dependency. Must add:
```toml
dependencies = ["mcp[cli]>=1.26", "owlbear-knowledge"]
```
With path-based dev dep: `owlbear-knowledge = {path = "../knowledge", editable = true}`

## 4. Recommendation (.85 confidence)

**Phase A (task #16 scope):** Build server.py following mcp-kanban pattern with tools for search, list_entities, list_sources, get_stats, and knowledge://stats resource. Add `GraphStore.get_counts()` method. Fix pyproject.toml deps. Register in mcp.json. Write SKILL.md.

**Phase B (after #33):** Add ingest_document tool once IngestPipeline is extracted. This is a separate task.

**Risk:** 4 of 12 existing tests (`test_ingest_graph_tools.py`) will remain red until phase B. Builder should mark them `xfail` with reason string referencing #33.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add GraphStore.get_counts() method" --priority needed --status ideation --tags "phase-1,scope:knowledge" --body "Add a get_counts() method to GraphStore returning document, entity, and edge counts. ~10 LOC. Needed by mcp-knowledge get_stats tool. Ref: docs/research/build-mcp-knowledge-server.md"
kanban\kanban-md.exe create "Add ingest_document tool to mcp-knowledge (phase B)" --priority important --status ideation --tags "phase-1,scope:mcp" --depends-on 33 --body "After task #33 extracts IngestPipeline/DocumentStore, add ingest_document tool to mcp-knowledge server. Un-xfail ingest tests. Ref: docs/research/build-mcp-knowledge-server.md"
```
