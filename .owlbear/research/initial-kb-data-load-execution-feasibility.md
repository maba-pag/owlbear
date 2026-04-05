# Initial KB Data Load — Execution Feasibility Review

> **Owning task:** #178 — Execute initial KB data load and verify search quality
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #178 is Phase B of #24 (archived, split into #176/#177/#178). It requires
running the data loader against the real knowledge.db, verifying hybrid search
quality, and confirming MCP access. This review validates whether the task is
executable given current codebase state and identifies AC discrepancies.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OwlBear loader.py (local) | `packages/knowledge/src/owlbear_knowledge/loader.py` | 1.0 — CLI entry point, QdrantVectorStore() defaults |
| MCP-knowledge server.py (local) | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 1.0 — App lifespan, also QdrantVectorStore() defaults |
| Qdrant vector store (local) | `packages/knowledge/src/owlbear_knowledge/qdrant.py` | 1.0 — location param behavior |
| Entity extractor (local) | `packages/knowledge/src/owlbear_knowledge/extractor.py` | .95 — No-op stub without injected extractor |
| Original research (local) | `docs/research/general-kb-initial-data-load.md` | .90 — Predicted no-op entities, ~50 doc subset |
| Knowledge toolset research (local) | `docs/research/knowledge-toolset.md` | .85 — Prescribes persistent Qdrant path |
| BgeM3EmbeddingProvider (local) | `packages/knowledge/src/owlbear_knowledge/embeddings.py` | .80 — FlagEmbedding ~2.2 GB dependency |

## 3. Analysis

### 3.1 Dependency Status

| Dep | Task | Status | Impact |
|-----|------|--------|--------|
| #16 | Build mcp-knowledge server | **archived** | Satisfied. MCP server works (84 tests passing). |
| #160 | Hybrid search upgrade | **todo** (reviewer FAIL) | Code implemented (d9082b2, 27 tests pass). Stuck on missing AC4b test. AC5 of #178 depends on this. |

### 3.2 Qdrant Persistent Storage Gap

Both the loader CLI and MCP server create `QdrantVectorStore()` with default
`:memory:`. Vectors are lost on process exit. The loader and MCP server run as
separate processes, so they can't share in-memory state.

**Fix:** Two lines — pass `location="data/knowledge/qdrant"` (or derive from
`OWLBEAR_KB_PATH`) in both `loader.py:main()` and `server.py:app_lifespan()`.
This was already prescribed by `docs/research/knowledge-toolset.md` §3.6. Include
this fix in #178's AC scope.

### 3.3 Document Count Discrepancy

| Source | AC estimate | Actual glob matches |
|--------|------------|---------------------|
| Research docs (`docs/research/*.md`) | ~50 | 511 |
| Skills (`skills/*/SKILL.md`) | ~25 | 23 |
| Instructions (`instructions/*.md`) | ~5 | 5 |
| **Total** | **~80** | **539** |

The AC assumed a curated subset; the manifest uses an unfiltered wildcard. Options:
(a) update AC2 to ~540, or (b) curate the manifest. Loading all 539 is valid for a
first wave — it exercises the pipeline at scale. Recommend updating AC2.

### 3.4 Entity Extraction No-Op

`EntityExtractor()` without an injected `StructuredExtractor` returns empty results
(0 entities, 0 edges). This was known at task creation — the original research
(§3.2) documented it. AC3 should clarify: expected counts are documents=~540,
entities=0, edges=0 until a real LLM extractor is configured (#33).

### 3.5 FlagEmbedding Availability

`BgeM3EmbeddingProvider` lazily loads `FlagEmbedding.BGEM3FlagModel` (~2.2 GB).
Must be installed before execution: `uv pip install FlagEmbedding`. First run
downloads the model. This is a pre-condition, not a blocker.

## 4. Recommendation (.80 confidence)

Advance #178 to backlog with **refined AC**:

1. Add Qdrant persistent storage fix to task scope (2-line change)
2. Update AC2: ~540 documents (full glob), not ~80
3. Clarify AC3: entity/edge counts = 0 (no-op extractor, documented)
4. Keep AC5 (hybrid vs dense) as conditional on #160 completion
5. Pre-condition: FlagEmbedding installed via `uv pip install FlagEmbedding`

Challenge: reconsider — confidence in original: .60. Challenger correctly identified
that the Qdrant fix is trivial and should be in-scope, not a separate prerequisite.
Accepted: integrated fix into recommendation. Researcher retains REFINE-the-AC
assessment since multiple AC lines need updating.

## 5. Follow-up Tasks

No new tasks needed. #178 is the execution task itself. AC refinements applied
via the architect gate when #178 advances to backlog.
