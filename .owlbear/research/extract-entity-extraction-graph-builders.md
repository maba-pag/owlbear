# Extract Entity Extraction + Graph Builders

> **Owning task:** #33 — Extract entity extraction + graph builders
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #33 is subtask 3/4 of knowledge engine extraction. The v2 `packages/knowledge/` already has **no-op stubs** for `extractor.py` and `graph_builder.py` (created during #15). These stubs return empty results with no LLM dependency. The AC asks to make them functional and add `ingest.py`/`intake.py`. The core design question: how to replace PydanticAI `Agent` with a pluggable LLM interface.

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| v1 EntityExtractor | `v1/src/owlbear/memory/knowledge/extractor.py` | 1.0 — source code being extracted |
| v1 IntraDocGraphBuilder | `v1/src/owlbear/memory/knowledge/graph_builder.py` | 1.0 |
| v1 InterDocGraphBuilder | `v1/src/owlbear/memory/knowledge/inter_doc_graph_builder.py` | 1.0 |
| v1 IngestPipeline | `v1/src/owlbear/memory/knowledge/ingest.py` | 1.0 |
| v1 intake | `v1/src/owlbear/memory/knowledge/intake.py` | 1.0 |
| fast-graphrag BaseLLMService | `github.com/circlemind-ai/fast-graphrag` | .80 — Protocol + `send_message(response_model=)` pattern |
| nano-graphrag LLM functions | `github.com/gusye1234/nano-graphrag` | .75 — plain async callable pattern |
| v2 existing stubs | `packages/knowledge/src/owlbear_knowledge/` | 1.0 |
| Python Protocol PEP 544 | `docs.python.org/3/library/typing.html#typing.Protocol` | .85 — structural subtyping |

## 3. Analysis

### 3.1 V2 State vs AC Requirements

| AC Item | V2 Status | Work Needed |
|---------|-----------|-------------|
| extractor.py (EntityExtractor) | No-op stub (48 LOC) | Replace stub with protocol-backed implementation |
| graph_builder.py (IntraDocGraphBuilder) | No-op stub (92 LOC) | Replace stub with protocol-backed implementation |
| inter_doc_graph_builder.py | Folded into graph_builder.py as stub | Separate file, real implementation |
| ingest.py (IngestPipeline) | **Does not exist** | Create from v1 (~395 LOC) |
| intake.py (readers) | **Does not exist** | Create from v1 (~76 LOC) |
| Pluggable LLM interface | **No protocol exists** | Design and implement |

### 3.2 LLM Protocol Design

V1 uses PydanticAI `Agent[None, ExtractionResult]` identically in all 3 modules: construct with model + system_prompt + output_type, then `await agent.run(prompt)` returning `result.output`. The AC says to replace this with a pluggable interface.

| Approach | KISS | Type Safety | Testability | Prior Art |
|----------|------|-------------|-------------|-----------|
| **A: Callable** `Callable[[str], Awaitable[ExtractionResult]]` | High | Medium — no method structure | High — any async func works | nano-graphrag |
| **B: Generic Protocol** `extract(prompt, output_type: type[T]) -> T` | Medium | High — generic return | Medium — generic mocking | fast-graphrag `BaseLLMService` |
| **C: Narrow Protocol** `StructuredExtractor` with `extract(prompt) -> ExtractionResult` | High | High — concrete type | High — trivial mock | OwlBear `EmbeddingProvider` pattern |

**Recommendation (.85): Option C — narrow `StructuredExtractor` protocol.**

All 3 v1 modules return `ExtractionResult`. The only difference is the system prompt (set at construction). A protocol with one method matches the existing `EmbeddingProvider` pattern in v2:

```python
@runtime_checkable
class StructuredExtractor(Protocol):
    """LLM-backed structured extraction — returns entities and edges from text."""

    async def extract(self, prompt: str) -> ExtractionResult: ...
```

Callers inject a pre-configured `StructuredExtractor` (system prompt baked in). Adapters:
- **PydanticAI adapter**: wraps `Agent.run()` → `.output` (built at MCP/orchestrator layer)
- **Mock adapter**: returns canned results (for unit tests)
- **Direct API adapter**: OpenAI client + JSON mode (future)

The system prompt constants (`EXTRACTION_PROMPT`, `GRAPH_BUILDER_PROMPT`, `INTER_DOC_PROMPT`) stay in the respective modules as documentation but are no longer used at construction — the caller provides a fully configured extractor.

### 3.3 Ingest Pipeline Dependencies

V1 `IngestPipeline` depends on `DocumentStore` (full CRUD, not just `StatusStore`). V2 only has `StatusStore`. Missing methods needed by ingest:

| Method Group | V1 Location | V2 Status |
|-------------|-------------|-----------|
| `insert_document`, `store_chunks` | `DocumentStore` | **Missing** |
| `store_embeddings`, `store_entity_embeddings` | `DocumentStore` | **Missing** |
| `store_extractions` | `DocumentStore` | **Missing** |
| `find_status_by_source`, `check_content_changed` | `DocumentStore` | Partial — `StatusStore` has these |
| `delete_document_data` | `DocumentStore` | **Missing** |
| `GraphEnricher` | `enrichment.py` | **Missing** — tracked by #135 (nice-to-have) |
| `CancelSignal` | `cancellation.py` | **Missing** — tracked by #135 |
| `sandbox_path` | `owlbear.paths` | **Missing** — tracked by #135 |

**Recommendation (.80):** Split #33 scope. The AC bundles 3 concerns of differing complexity:

1. **LLM protocol + entity/graph extractors** (core, ~250 LOC) — self-contained, no new deps
2. **intake.py** (simple, ~80 LOC) — BUT depends on `sandbox_path` (#135) and `httpx`
3. **ingest.py** (complex, ~350 LOC) — depends on `DocumentStore` extension, `GraphEnricher` (#135)

### 3.4 File Organization

| File | Content | Est. LOC | New/Replace |
|------|---------|----------|-------------|
| `protocol.py` | Add `StructuredExtractor` protocol | +15 | Extend |
| `extractor.py` | `ExtractionResult` + `EntityExtractor` with injected extractor | ~70 | Replace stub |
| `graph_builder.py` | `GraphBuildResult` + `IntraDocGraphBuilder` with injected extractor | ~130 | Replace stub |
| `inter_doc_graph_builder.py` | `InterDocGraphBuilder` with vector pre-filter + injected extractor | ~170 | New file |
| `intake.py` | `IntakeResult` + `read_file`/`read_url`/`read_text` | ~80 | New file |
| `ingest.py` | `IngestResult` + `IngestPipeline` orchestrator | ~300 | New file |

### 3.5 V1 Dependency Removal

| V1 Dependency | Replacement |
|--------------|-------------|
| `pydantic_ai.Agent` | `StructuredExtractor` protocol (injected) |
| `owlbear.memory.usage.UsageTracker` | Drop — usage tracking not in v2 scope |
| `owlbear.memory.usage.record_agent_usage` | Drop |
| `owlbear.core.retry.TRANSIENT_RETRY` | `tenacity` or stdlib retry (intake only) |
| `owlbear.paths.sandbox_path` | Port from v1 or use `Path.resolve()` with root check |
| `owlbear.memory.knowledge.cancellation.CancelSignal` | Optional `asyncio.Event` protocol |

## 4. Recommendation (.80 confidence)

**Refine AC into two focused tasks** rather than one large task:

**Task A (core, #33):** Implement `StructuredExtractor` protocol, replace `extractor.py`/`graph_builder.py` stubs with real implementations, separate `InterDocGraphBuilder` into its own file. Self-contained, no new external deps. ~400 LOC total.

**Task B (new task):** Create `intake.py` + `ingest.py` with `DocumentStore` extension. Depends on #135 (CancelSignal, sandbox_path). ~400 LOC total.

This separation aligns with KISS — Task A is pure logic (prompt formatting + post-processing), Task B involves I/O, storage, and pipeline orchestration.

**Risk:** The current AC bundles both concerns. If shipped as-is, the builder would need to also build `DocumentStore` CRUD extensions (not trivial) and decide how to handle missing utilities (sandbox_path, CancelSignal). Splitting prevents scope creep.

## 5. Follow-up Tasks

AC refinement for #33 (narrow to protocol + extractors). New task for ingest pipeline.
