# General KB Initial Data Load

> **Owning task:** #24 — General KB initial data load
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #24 calls for seeding the general knowledge base with initial data (internal docs, tech references, design patterns) and documenting the curation process. **Key questions:** (a) What sources should be loaded? (b) What's the ingestion workflow? (c) What upstream work is blocking? (d) How should curation work long-term?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| GraphRAG quickstart | microsoft.github.io/graphrag/get_started/ | .85 — `input/` directory + `graphrag index` pipeline for bulk text ingestion |
| LightRAG insert API | github.com/HKUDS/LightRAG | .85 — `rag.ainsert("text")` for incremental ingestion, workspace isolation |
| Mem0 memory.add() | github.com/mem0ai/mem0 | .70 — Incremental `memory.add(messages)` pattern, scope-based isolation |
| OwlBear knowledge package (local) | `packages/knowledge/` | 1.0 — IngestPipeline, GraphStore, KnowledgeSourceStore, StatusStore APIs |
| OwlBear mcp-knowledge server (local) | `packages/mcp-knowledge/` | 1.0 — MCP tools: search_knowledge, ingest_document, list_entities, get_stats |
| knowledge-scoping research (local) | `docs/research/knowledge-scoping.md` | .95 — Scope system: `global`, `project:{name}`, `agent:{name}` |
| knowledge-ingestion research (local) | `docs/research/knowledge-ingestion.md` | .90 — Chunking, embedding, entity extraction pipeline design |

## 3. Analysis

### 3.1 Dependency Status — What's Blocked

| Upstream task | Status | What it unblocks for #24 |
|---------------|--------|--------------------------|
| #16 Build mcp-knowledge server | backlog | MCP access (AC: "accessible via mcp-knowledge") |
| #32 Extract vector store + embedding | backlog | Embedding storage for search |
| #33 Extract entity extraction + graph builders | backlog | Entity extraction during ingest |
| #160 Upgrade query_service hybrid search | ideation | AC: "verify hybrid search returns relevant results" |
| #149 GraphStore.get_counts() | backlog | Stats tool for verification |

**Critical:** The AC item "verify hybrid search returns relevant results" requires #160 (hybrid search). The AC item "accessible via mcp-knowledge server" requires #16. Both are at backlog/ideation. **The actual data load cannot be fully verified until these complete.**

### 3.2 Available Ingestion Infrastructure

The v2 `IngestPipeline.ingest_text()` works end-to-end today: text → chunk (TextChunker, 512-token recursive) → extract (EntityExtractor, **no-op stub**) → store (GraphStore.insert_document). However:

- **EntityExtractor is a no-op** — entities and edges will be empty. Graph search won't work until #33.
- **BgeM3EmbeddingProvider requires FlagEmbedding** (~2.2 GB). Not a default dep.
- **QdrantVectorStore works** in-memory or on disk. Standard dep with `[qdrant]` extra.
- **StatusStore** tracks content hashes for delta detection (avoid re-ingesting unchanged docs).

### 3.3 Initial Data Sources — What to Load

| Category | Source | Files | Est. words | Scope | Priority |
|----------|--------|-------|-----------|-------|----------|
| Internal research | `docs/research/*.md` | 420 | ~388K | global | High — curated subset (~50 high-value) |
| Skills | `skills/*/SKILL.md` | ~25 | ~15K | global | High — agent operational knowledge |
| Instructions | `instructions/*.md` | 5 | ~8K | global | High — project conventions |
| Agent definitions | `agents/*.agent.md` | 11 | ~10K | global | Medium — role descriptions |
| Decision records | `docs/decisions/**/*.md` | varies | ~5K | global | Medium — rationale history |
| Python 3.12 docs | docs.python.org/3.12/ | external | N/A | global | Low — defer to phase 2 |
| PydanticAI docs | ai.pydantic.dev/ | external | N/A | global | Low — defer to phase 2 |
| MCP SDK docs | modelcontextprotocol.io | external | N/A | global | Low — defer to phase 2 |

**Key insight from GraphRAG and LightRAG:** Both projects bootstrap with a seed document set placed in an `input/` directory, then run bulk indexing. GraphRAG uses `graphrag index`; LightRAG uses `rag.ainsert()`. OwlBear's equivalent is `IngestPipeline.ingest_text()` per document. Both recommend starting small (one book / one dataset) before scaling.

**Recommendation (.85):** Start with a curated subset of ~50 high-signal research docs + all skills + instructions. Load ~80 documents total in wave 1. External references (Python docs, framework docs) defer to wave 2 after verifying internal corpus search quality.

### 3.4 Curation Process Design

Both GraphRAG and LightRAG lack a formal curation process — they are "load and reindex" systems. OwlBear has better primitives:

| Step | Tool | Purpose |
|------|------|---------|
| 1. Register source | `KnowledgeSourceStore.create()` | Track where content came from |
| 2. Check delta | `StatusStore.check_content_changed()` | Skip unchanged documents |
| 3. Ingest | `IngestPipeline.ingest_text()` | Chunk, extract, embed, store |
| 4. Update status | `StatusStore.set_status()` + `update_content_hash()` | Track ingestion state |
| 5. Verify | `KnowledgeQueryService.query()` | Spot-check search relevance |
| 6. Bookmark | `BookmarkStore.create()` | Track external URLs |

**Curation workflow:** A data loader script reads a manifest file (`data/knowledge/general/sources.yaml`) listing source globs and URLs, iterates through documents, and calls IngestPipeline for each. The manifest is the curated list — adding/removing sources is a file edit.

### 3.5 Data Directory Layout

AC specifies `owlbear/data/knowledge/general/`. Current state: directory exists with only `.gitkeep`. Schema uses `data/knowledge/knowledge.db` as default path (`OWLBEAR_KB_PATH`).

| Path | Purpose |
|------|---------|
| `data/knowledge/general/sources.yaml` | Manifest of registered sources |
| `data/knowledge/knowledge.db` | SQLite database (gitignored) |
| `data/knowledge/qdrant/` | Qdrant persistent storage (gitignored) |

### 3.6 AC Feasibility Assessment

| AC Item | Feasible now? | Blocker |
|---------|---------------|---------|
| Identify initial data sources | **Yes** | None |
| Ingest v1 research documents | **Partial** — pipeline works, entities are no-op | #33 for full extraction |
| Ingest key external references | **No** — needs working search to verify value | #32, #160 |
| Verify hybrid search returns relevant results | **No** | #160 (hybrid search) |
| Document curation process | **Yes** | None |
| KB lives in data/knowledge/general/ | **Yes** — directory exists | None |
| Accessible via mcp-knowledge server | **No** | #16 (backlog) |

## 4. Recommendation (.80 confidence)

**Split #24 into two phases:**

**Phase A (can proceed now as standalone build task):** Write the data loader script + sources manifest + curation docs. This is a concrete deliverable: a Python script that reads `sources.yaml`, walks internal docs, and calls IngestPipeline. The script validates the curation process end-to-end using in-memory storage (no FlagEmbedding required for tests — mock the embedding provider).

**Phase B (blocked on #16, #32, #33, #160):** Execute the actual data load against the real KB, verify hybrid search quality, wire MCP access. This task should depend on #16 and #160 explicitly.

**Risk:** Phase A can start now but tests must use mocks for embedding (BgeM3 is 2.2 GB). The loader script design should follow the GraphRAG `input/` directory pattern — simple file glob, no complex crawling.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Build KB data loader script and sources manifest" --priority needed --status ideation --tags "phase-2,scope:knowledge,type:build" --depends-on 32 --body "## Objective\nCreate data/knowledge/general/sources.yaml manifest and a loader script (packages/knowledge/src/owlbear_knowledge/loader.py) that reads the manifest and ingests documents via IngestPipeline.\n\n## Acceptance Criteria\n- [ ] sources.yaml manifest format: list of {name, type: file_glob|url_list, config: {glob/urls}, scope, enabled}\n- [ ] Loader script reads manifest, resolves file globs relative to project root\n- [ ] Registers each source via KnowledgeSourceStore.create()\n- [ ] Checks content delta via StatusStore before re-ingesting\n- [ ] Calls IngestPipeline.ingest_text() for new/changed documents\n- [ ] CLI entry point: uv run python -m owlbear_knowledge.loader --manifest path\n- [ ] Unit tests with mock EmbeddingProvider (no FlagEmbedding dep)\n- [ ] Initial sources.yaml includes ~50 curated research docs + all skills + instructions\n\n## Context\nSplit from #24. See docs/research/general-kb-initial-data-load.md."

kanban\kanban-md.exe create "Document KB curation process" --priority important --status ideation --tags "phase-2,scope:knowledge,type:docs" --body "## Objective\nWrite curation process documentation for adding, updating, and removing knowledge sources.\n\n## Acceptance Criteria\n- [ ] docs/research/ or skills/ doc covering: how to add a new source, how to refresh existing sources, how to remove stale content\n- [ ] Describes sources.yaml manifest format\n- [ ] Describes the delta detection workflow (StatusStore content hashing)\n- [ ] Covers scope assignment conventions (global vs project vs agent)\n- [ ] Includes examples for adding internal docs and external URLs\n\n## Context\nSplit from #24 AC item 'Document the curation process for adding new sources'. See docs/research/general-kb-initial-data-load.md."

kanban\kanban-md.exe create "Execute initial KB data load and verify search quality" --priority important --status ideation --tags "phase-2,scope:knowledge,type:build" --depends-on 16,160 --body "## Objective\nRun the data loader against the real knowledge.db, verify hybrid search returns relevant results, confirm MCP access works.\n\n## Acceptance Criteria\n- [ ] Execute loader script against data/knowledge/knowledge.db with BgeM3 embeddings\n- [ ] ~80 documents ingested (50 research docs + skills + instructions)\n- [ ] get_stats shows expected document/entity/edge counts\n- [ ] 5 sample queries via search_knowledge return relevant results (manual spot-check)\n- [ ] Hybrid search (dense + sparse) returns better results than dense-only for at least 3/5 queries\n- [ ] MCP server serves search results via mcp-knowledge tools\n\n## Context\nPhase B of #24. Blocked on #16 (mcp-knowledge server) and #160 (hybrid search). See docs/research/general-kb-initial-data-load.md."
```
