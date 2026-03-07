# EdgeQuake — Graph-RAG Framework Analysis

> **Owning task:** #597 — raphaelmansuy/edgequake
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Analyze EdgeQuake (Rust LightRAG implementation) for edge computing patterns, local-first AI deployment, and lightweight processing approaches applicable to OwlBear's knowledge system.

EdgeQuake is a **high-performance Graph-RAG framework** (1.4K stars, Apache-2.0) that implements the LightRAG algorithm (arxiv:2410.05779) in Rust. It is NOT an edge computing framework — the name is misleading. It is a document-to-knowledge-graph pipeline with 6 query modes, targeting server/laptop deployment with local LLMs (Ollama) or cloud providers.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| EdgeQuake GitHub | github.com/raphaelmansuy/edgequake | .90 | Full codebase: 11 Rust crates, React frontend, MCP server, Python/TS SDKs |
| EdgeQuake deep-dive: LightRAG algorithm | docs/deep-dives/lightrag-algorithm.md | .85 | Dual-level retrieval (local entity + global community), graph-bridging across documents |
| EdgeQuake deep-dive: entity normalization | docs/deep-dives/entity-normalization.md | .80 | UPPERCASE_UNDERSCORE canonical form, description merging, 36-40% dedup |
| EdgeQuake deep-dive: gleaning | docs/deep-dives/gleaning.md | .80 | Multi-pass LLM extraction: +18-25% entity recall via iterative re-prompting |
| EdgeQuake deep-dive: community detection | docs/deep-dives/community-detection.md | .75 | Louvain modularity optimization for thematic clustering |
| EdgeQuake deep-dive: cost tracking | docs/deep-dives/cost-tracking.md | .70 | Per-operation token/cost tracking (input/output × pricing per model) |
| EdgeQuake pipeline source | edgequake/crates/edgequake-pipeline/src/ | .85 | Resilient extraction, cooperative cancellation via CancellationToken, lineage |
| LightRAG paper | arxiv.org/abs/2410.05779 | .90 | Original algorithm: entity extraction → graph → dual-level retrieval |
| OwlBear community-detection-research.md | docs/community-detection-research.md | .85 | Prior OwlBear research: community detection is YAGNI at our scale |
| OwlBear graph-augmented-retrieval-research.md | docs/graph-augmented-retrieval-research.md | .85 | OwlBear's existing neighbor-expansion retriever |

## 3. Analysis

### 3.1 Architecture Comparison

| Aspect | EdgeQuake | OwlBear | Delta |
|--------|-----------|---------|-------|
| Language | Rust (Tokio async) | Python 3.12 (asyncio) | Different ecosystem |
| Graph storage | PostgreSQL AGE | SQLite | Both relational; EQ heavier |
| Vector storage | pgvector | Qdrant | OwlBear's is more capable |
| Entity extraction | LLM-based (tuple parsing) | Code-analysis based | Fundamentally different |
| Entity types | 7 generic (Person, Org, etc.) | 6 code-oriented (file, function, etc.) | Domain-specific |
| Query modes | 6 (naive→bypass) | 1 (graph-augmented hybrid) | EQ more flexible |
| Community detection | Louvain (built-in) | Researched, YAGNI at scale | Confirmed by prior research |
| Cancellation | CancellationToken (cooperative) | None on pipelines | Gap |
| Cost tracking | Per-operation token tracking | None | Gap |
| Multi-tenant | Full workspace isolation | Single-user projects | Not needed |

### 3.2 Patterns Evaluated for OwlBear

| Pattern | Applicability | Confidence | Rationale |
|---------|--------------|------------|-----------|
| Tuple-based LLM extraction | Low (.30) | .75 | OwlBear uses code analysis, not LLM extraction. File for future reference only. |
| Gleaning (multi-pass extraction) | Low (.30) | .75 | Same — no LLM extraction today. Valuable if added later. |
| Cooperative pipeline cancellation | Medium (.60) | .80 | `RefreshOrchestrator` and `BookmarkPipeline` could benefit from cancellation support. Translates to `asyncio.Event`. |
| LLM cost tracking | Medium (.65) | .85 | OwlBear uses LLMs for entity extraction (inter-doc graph), source evaluation, and agent runs. No cost visibility today. |
| Resilient partial-failure processing | Already present (.20) | .90 | `RefreshOrchestrator` already has per-item error collection. Pattern confirmed. |
| Entity name normalization | Low (.25) | .80 | OwlBear entities are code-derived with stable names, not LLM-extracted. Less fragmentation risk. |
| Document lineage/provenance | Already present (.20) | .90 | OwlBear has `chunk_id` on entities and `document_id` linkage. Pattern confirmed. |
| MCP server for agent access | Low (.20) | .70 | OwlBear exposes knowledge via toolsets to in-process agents. MCP adds no value for a daemon. |

### 3.3 Key Insight: LLM Cost Tracking

EdgeQuake tracks costs per operation with a clean `ModelPricing` + `OperationCost` structure: input tokens × price + output tokens × price, accumulated per pipeline stage. This is the most directly actionable pattern.

OwlBear currently has no cost visibility across: (a) knowledge ingestion (BGE-M3 embedding, inter-doc graph LLM calls), (b) source evaluation (SourceEvaluator agent), (c) agent turns (Copilot API calls). A lightweight cost tracker modeled on EdgeQuake's approach would provide budget visibility.

### 3.4 Key Insight: Cooperative Cancellation

EdgeQuake's `CancellationToken` pattern is elegant: pass an optional token through the pipeline, check it before starting each new chunk extraction, let in-flight work finish naturally. This maps directly to Python's `asyncio.Event`:

```
# Conceptual — not a code proposal
cancel = asyncio.Event()
for item in work_items:
    if cancel.is_set():
        break  # cooperative exit
    await process(item)
```

OwlBear's `RefreshOrchestrator` and `BookmarkPipeline` both process items in loops without cancellation support. Adding an optional cancellation event would allow graceful shutdown during long ingestion runs.

## 4. Recommendation (.70 confidence)

EdgeQuake is a well-engineered Graph-RAG system, but its core domain (LLM-based entity extraction into knowledge graphs) overlaps minimally with OwlBear's code-oriented knowledge system. The two most transferable patterns are **LLM cost tracking** and **cooperative pipeline cancellation**.

Neither is urgent. Cost tracking becomes more valuable as OwlBear's LLM usage grows. Cancellation is a quality-of-life improvement for long ingestion runs. Both are low-complexity additions (est. 50-100 LOC each).

The gleaning and tuple-based extraction patterns are worth bookmarking for the future if OwlBear ever adds LLM-based document entity extraction (beyond the current `InterDocGraphBuilder`).

## 5. Follow-up Tasks

See kanban commands below — two `nice-to-have` tasks for cost tracking and cancellation, plus one `someday` task for gleaning awareness.

