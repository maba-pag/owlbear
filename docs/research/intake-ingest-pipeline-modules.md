# Intake + Ingest Pipeline Modules in Knowledge Package

> **Owning task:** #158 — Create intake + ingest pipeline modules in knowledge package
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #158 extracts the pipeline orchestration layer from v1 into `packages/knowledge/`: `intake.py` (content readers) and `ingest.py` (async pipeline coordinator). V2 already has a simplified `ingest.py` (~122 LOC, text-only, no delta detection). The question: what is the correct implementation approach, what dependencies block it, and should the AC be refined?

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| V1 intake.py | `v1/src/owlbear/memory/knowledge/intake.py` | 1.0 — source being extracted (~88 LOC) |
| V1 ingest.py | `v1/src/owlbear/memory/knowledge/ingest.py` | 1.0 — source being extracted (~395 LOC) |
| V2 ingest.py (current) | `packages/knowledge/src/owlbear_knowledge/ingest.py` | 1.0 — existing simplified version |
| LlamaIndex IngestionPipeline | developers.llamaindex.ai/python/.../ingestion_pipeline/ | .90 — docstore delta detection, async, composable transforms |
| nano-graphrag _op.py | github.com/gusye1234/nano-graphrag | .80 — asyncio.gather for parallel chunk extraction, injectable LLM |
| OwlBear research: entity extraction | `docs/research/extract-entity-extraction-graph-builders.md` | .95 — §3.3 dependency analysis |
| OwlBear research: ingest complexity | `docs/research/ingest-complexity-reduction.md` | .90 — DocumentStore extraction pattern |
| V2 StatusStore | `packages/knowledge/src/owlbear_knowledge/status_store.py` | 1.0 — has delta detection |
| V2 GraphStore | `packages/knowledge/src/owlbear_knowledge/graph_store.py` | 1.0 — has entity/edge/doc CRUD |

## 3. Analysis

### 3.1 V2 Gap Analysis

| AC Item | V2 Status | Work |
|---------|-----------|------|
| `intake.py` with IntakeResult + readers | **Missing** | New file, ~80 LOC |
| `ingest.py` full pipeline | Simplified stub (122 LOC) | Upgrade to ~300 LOC |
| DocumentStore with storage methods | Minimal wrapper (1 method) | New `document_store.py` ~250 LOC |
| Delta detection | StatusStore has `check_content_changed` | Wire into pipeline |
| Parallel embed+extract | V2 does `asyncio.gather` for extract only | Add embedding parallel path |

### 3.2 Storage Gap — DocumentStore Methods

V1 IngestPipeline calls these DocumentStore methods not yet in v2:

| Method | Purpose | V2 Equivalent |
|--------|---------|---------------|
| `store_chunks(doc_id, chunks, scope)` | Insert chunk rows | None — schema has `chunks` table |
| `store_embeddings(doc_id, chunks, embeds, scope)` | Store via VectorStoreProtocol | `VectorStoreProtocol.store_embedding` exists but no batch wrapper |
| `store_extractions(results, scope, doc_id, chunk_ids)` | Insert entities + edges | `GraphStore.insert_entity/insert_edge` (no batch) |
| `store_entity_embeddings(results, scope)` | Embed entity names | `EmbeddingProvider.embed` + `VectorStoreProtocol.store_embedding` |
| `delete_document_data(doc_id)` | Cascade delete | `GraphStore.delete_document` exists but doesn't cascade chunks/entities |

**Recommendation (.85):** Create `document_store.py` composing StatusStore + GraphStore + VectorStoreProtocol. This matches the existing v2 pattern (thin facade over SQLite) and prior research (ingest-complexity-reduction.md §4, Option A). LlamaIndex uses the same pattern: a `docstore` separate from the pipeline.

### 3.3 Dependency Analysis

| Dependency | Task | Status | Impact on #158 |
|------------|------|--------|-----------------|
| `StructuredExtractor` protocol | #33 | backlog | **Hard:** pipeline needs extraction interface |
| `EntityExtractor` (current no-op) | — | exists | Works for testing; pipeline doesn't change when #33 upgrades it |
| `CancelSignal` protocol | #135 | backlog | **Soft:** optional parameter, 4-line protocol can be inlined |
| `sandbox_path` | #135 | backlog | **Hard for read_file:** security-critical path sandboxing |
| `EmbeddingProvider` | — | exists | Available |
| `TextChunker` | — | exists | Available |

**Key finding:** #158 has an undeclared hard dependency on #33 (needs the `StructuredExtractor` protocol in `protocol.py`). The EntityExtractor interface needs to be stable before the ingest pipeline can be properly wired. The current no-op works for testing.

For `sandbox_path`: #135 targets `_paths.py` (private module, ~14 LOC). If #135 hasn't landed when #158 starts, the builder can either (a) inline a minimal `_sandbox_path` in intake.py or (b) wait. Given #135 is `nice-to-have`, option (a) is prudent.

### 3.4 Scope Boundary

| In scope | Out of scope |
|----------|-------------|
| `intake.py` — IntakeResult + 3 readers | GraphEnricher (background enrichment) — separate task |
| `document_store.py` — facade composing stores | Inter-doc graph builder wiring |
| `ingest.py` — upgrade to full pipeline | MCP server changes (handled by #55) |
| Delta detection via content hashing | Enrichment scheduling |
| Parallel embed+extract | Qdrant integration testing |
| CancelSignal support (optional param) | |

GraphEnricher is explicitly OUT. V1 couples enrichment into the pipeline, but prior research (ingest-complexity-reduction.md) recommends separating it. Both LlamaIndex and Haystack keep pipeline orchestration separate from post-processing.

### 3.5 MCP Compatibility

The current MCP test (`test_ingest_graph_tools.py`) mocks `IngestPipeline.ingest_text()`. The upgraded pipeline must preserve this method signature. The `ingest()` method (file/URL ingestion) and `DocumentStore` are new — no backward compat concern.

## 4. Recommendation (.85 confidence)

**Proceed with #158 as scoped, with three refinements:**

1. **Add `depends_on: [33]`** — the pipeline needs a stable extraction interface. The no-op EntityExtractor works for testing, but the StructuredExtractor protocol from #33 is the contract.
2. **DocumentStore goes to new `document_store.py`** — not an "extension" but a separate facade composing StatusStore + GraphStore + VectorStoreProtocol. This aligns with ingest-complexity-reduction research and LlamaIndex's docstore pattern.
3. **Inline minimal CancelSignal/sandbox_path** if #135 hasn't landed — 4-line protocol + 14-line path check are YAGNI-safe to inline, replaced when #135 arrives.

**Risk:** The existing v2 `ingest.py` has a different `DocumentStore` class (simple wrapper around GraphStore). The upgrade replaces it entirely. The MCP layer's `IngestPipeline` constructor will change — the MCP server code (#55) will need updating.

## 5. Follow-up Tasks

Task AC needs refinement. No new tasks needed — #158's scope is correct once AC is refined and dependencies declared.
