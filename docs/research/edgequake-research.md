# EdgeQuake — Graph-RAG Framework Analysis

> **Owning task:** #597 — raphaelmansuy/edgequake
> **Date:** 2026-03-06 (initial), 2026-03-10 (updated with MCP/tooling analysis) **Status:** Complete

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

```python
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

### Task 1: LLM Cost Tracking

```powershell
kanban\kanban-md.exe create -t "Research: LLM cost tracking per operation" -s backlog -p nice-to-have --tags "research,scope:core,phase-research" -b "**Source:** #597 edgequake-research §3.3\n\nEdgeQuake tracks per-operation LLM costs (input/output tokens × model pricing). OwlBear has no cost visibility across knowledge ingestion, source evaluation, and agent turns.\n\n**AC:**\n1. Survey OwlBear's current LLM call sites (Copilot HTTP transport, SourceEvaluator, InterDocGraphBuilder).\n2. Evaluate lightweight token-counting + cost-accumulator patterns.\n3. Propose a minimal cost tracker that integrates with OwlBear's existing httpx transport.\n4. Document in docs/research/llm-cost-tracking-research.md.\n5. Create follow-up implementation tasks if warranted."
```

### Task 2: Cooperative Pipeline Cancellation

```powershell
kanban\kanban-md.exe create -t "Research: Cooperative pipeline cancellation via asyncio.Event" -s backlog -p nice-to-have --tags "research,scope:core,phase-research" -b "**Source:** #597 edgequake-research §3.4\n\nEdgeQuake uses CancellationToken for cooperative early-exit in long pipelines. OwlBear's RefreshOrchestrator and BookmarkPipeline lack cancellation support.\n\n**AC:**\n1. Identify all OwlBear pipeline loops that could benefit from cancellation.\n2. Propose an asyncio.Event-based cancellation pattern.\n3. Document in docs/research/cooperative-cancellation-research.md.\n4. Create follow-up implementation tasks if warranted."
```

### Task 3: Gleaning Awareness (Future Reference)

```powershell
kanban\kanban-md.exe create -t "Bookmark: EdgeQuake gleaning (multi-pass LLM extraction) for future reference" -s backlog -p someday --tags "research,scope:core" -b "**Source:** #597 edgequake-research §3.2\n\nEdgeQuake's gleaning pattern (multi-pass LLM extraction for +18-25% recall) is not applicable today but valuable if OwlBear adds LLM-based document entity extraction beyond InterDocGraphBuilder.\n\n**AC:**\n1. No action needed now. This is a reference bookmark.\n2. Re-evaluate if OwlBear's knowledge pipeline adds LLM-based entity extraction."
```

## 6. Additional Findings — MCP Server & Developer Tooling (2026-03-10)

Updated analysis following full repo clone (v0.5.4, 7743 files). Focus areas per refined AC: agent orchestration, tool registration, CLI patterns, prompt engineering.

### 6.1 MCP Server — Modular Tool Registration Pattern

EdgeQuake's MCP server (`mcp/src/`) uses a **register-per-domain** pattern: each domain (document, graph, query, workspace, health) exports a `registerXTools(server)` function. The server factory composes them sequentially. Each tool uses Zod schemas for parameter validation and returns structured JSON.

**Key observation:** Clean separation of concerns — tool definition (schema + handler) colocated in one file per domain. Prompts and resources are separate modules. This mirrors OwlBear's `Toolset` pattern in Python.

**OwlBear applicability:** Low-medium. OwlBear already uses per-concern toolsets. If we ever expose an MCP server, this register pattern transfers directly.

### 6.2 MCP Prompt Templates as Workflow Encodings

Two MCP prompts (`rag_query`, `document_summary`) encode multi-step tool-use workflows as prompt resources. Agents calling the MCP server get guided instructions ("use document_get → document_status → query → graph_search_entities").

**OwlBear applicability:** Medium. This is a lightweight alternative to full orchestration — encode known-good tool sequences as reusable prompts. Could complement OwlBear's skill files if we expose MCP.

### 6.3 Auto-Discovery Client Bootstrap

`client.ts` implements lazy singleton initialisation with auto-discovery: on first use, if tenant/workspace env vars are unset, it queries the server to find defaults. Multi-tenant security warnings are logged. This avoids forcing users to configure upfront.

**OwlBear applicability:** Low. OwlBear is single-user. The lazy-singleton-with-discovery pattern is clean but not needed.

### 6.4 Models Configuration via TOML

`models.toml` defines every LLM/embedding model with structured metadata: capabilities (context, vision, function calling, streaming), cost/1K tokens, priority, and tags. Config priority: env var → CWD → home dir → built-in defaults. 9 providers defined.

**OwlBear applicability:** Low. OwlBear uses Copilot exclusively. The pattern is a good reference if multi-provider support is ever revisited.

### 6.5 Documentation Traceability Validator

A `.github/skills/doc-traceability-validator/` skill with Python scripts validates bidirectional links between code `@implements FEATXXXX` annotations and documentation registries. Composite scoring (completeness 40%, uniqueness 30%, cross-refs 20%, namespace 10%) gates PRs. Integrated via pre-commit hook.

**OwlBear applicability:** Low. OwlBear doesn't use `@implements` annotations — AC traceability is managed through kanban task bodies and the reviewer/auditor pipeline. The scoring concept is interesting but would over-engineer our current workflow.

### 6.6 Orphaned Task Recovery on Startup

`main.rs` unconditionally resets all "processing" tasks to "pending" on startup. Safe because: (a) no workers running at boot → all processing tasks are orphaned; (b) pipeline uses idempotent upserts with checkpointing.

**OwlBear applicability:** Medium. OwlBear's daemon could similarly detect stale `in-progress` kanban claims from before the last shutdown. Current behavior: stale claims persist until manually released.

### 6.7 Smart Mock Provider Convention

`.claude/SKILLS.md` documents a pattern for mocks that return structurally valid, realistic data (valid entity/relationship JSON) instead of empty responses.

**OwlBear applicability:** Low. OwlBear already uses realistic fixtures sporadically. Formalising this is a minor docs improvement.

### 6.8 Patterns Not Applicable

| Pattern | Reason |
|---------|--------|
| Rust crate workspace | Python project; doesn't transfer |
| PostgreSQL AGE graph | OwlBear uses SQLite; different scale |
| Multi-language SDKs | YAGNI for laptop-resident tool |
| React/Next.js + Sigma.js frontend | OwlBear has no web UI |
| Makefile dev workflow | OwlBear uses uv + PowerShell |
| PDF Vision Pipeline | Outside OwlBear scope |
| `bestmode.agent.md` | Generic "keep going" prompt; no value |
| Playwright E2E skill | No web frontend to test |

