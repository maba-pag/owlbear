---
id: 158
title: Create intake + ingest pipeline modules in knowledge package
status: todo
priority: needed
created: 2026-03-29T19:35:58.8584239+02:00
updated: 2026-03-30T08:16:46.5430641+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 206
class: standard
---

## Objective
Create intake.py (content readers), document_store.py (storage facade), and upgrade ingest.py (pipeline orchestration) in packages/knowledge/. This is the pipeline orchestration layer that coordinates intake, chunking, embedding, and entity extraction.

## Acceptance Criteria

### intake.py (new module)
- [ ] `IntakeResult` frozen Pydantic model: `content: str`, `source: str`, `metadata: dict[str, Any]`
- [ ] `async read_file(path: str | Path, *, workspace_root: Path) -> IntakeResult` â€” resolves via `_paths.sandbox_path`, reads via `asyncio.to_thread(Path.read_text)`, sets `metadata[source_type] = file`. Raises `PermissionError` on traversal, `FileNotFoundError` on missing.
- [ ] `async read_url(url: str) -> IntakeResult` â€” uses `httpx.AsyncClient` (optional dep), sets `metadata[source_type] = url`. Raises `httpx.HTTPStatusError` on non-2xx.
- [ ] `read_text(text: str, source: str = inline) -> IntakeResult` â€” sync wrapper, sets `metadata[source_type] = text`
- [ ] All readers set `metadata[fetched_at]` to current UTC ISO timestamp

### document_store.py (new module, NOT extension of existing ingest.py class)
- [ ] `DocumentStore.__init__(conn: sqlite3.Connection, graph_store: GraphStore, vector_store: VectorStoreProtocol, embedding_provider: EmbeddingProvider)`
- [ ] `insert_document(document_id: str, intake: IntakeResult, *, scope: str = global) -> None` â€” inserts into documents table
- [ ] `store_chunks(document_id: str, chunks: list[Chunk], *, scope: str = global) -> list[str]` â€” inserts into chunks table, returns generated chunk_ids
- [ ] `store_embeddings(document_id: str, chunks: list[Chunk], embeddings: list[HybridEmbedding], *, scope: str = global) -> None` â€” stores via VectorStoreProtocol
- [ ] `store_extractions(results: list[ExtractionResult], *, scope, document_id, chunk_ids, pipeline_name=ingest) -> tuple[int, int]` â€” inserts entities+edges via GraphStore, stamps provenance metadata, returns (entity_count, edge_count)
- [ ] `store_entity_embeddings(results: list[ExtractionResult], *, scope: str = global) -> None` â€” embeds entity descriptions via EmbeddingProvider, stores as embedding_type=entity
- [ ] `delete_document_data(document_id: str) -> None` â€” cascades: chunks, entity edges, entities, documents, document_status
- [ ] Status tracking: `set_status`, `find_status_by_source`, `check_content_changed`, `update_content_hash` â€” delegate to StatusStore or compose equivalent SQL

### ingest.py (upgrade existing 122 LOC)
- [ ] Remove existing minimal DocumentStore class (replaced by document_store.py)
- [ ] `IngestPipeline.__init__(document_store: DocumentStore, entity_extractor: EntityExtractor, text_chunker: TextChunker, *, cancel_signal: CancelSignal | None = None)`
- [ ] `async ingest_text(text: str, *, metadata: dict | None = None, scope: str = global) -> IngestResult` â€” PRESERVED call signature for MCP backward compatibility
- [ ] `async ingest(intake_result: IntakeResult, *, scope: str = global) -> IngestResult` â€” full pipeline: delta check, chunk, parallel(embed, extract), store, update status
- [ ] Delta detection: calls `check_content_changed` before processing; returns `IngestResult(status=skipped)` if unchanged
- [ ] Parallel: `asyncio.gather(embed_task, extract_task)` â€” embed runs EmbeddingProvider via to_thread, extract runs EntityExtractor.extract per chunk
- [ ] CancelSignal: checked between pipeline stages; returns `IngestResult(status=cancelled)` if set
- [ ] `IngestResult` status field valid values: `ok`, `failed`, `skipped`, `cancelled`

### Package configuration
- [ ] `pyproject.toml`: add httpx as optional dep group `intake = [httpx>=0.27]`; add to `full` group
- [ ] `__init__.py`: add `IntakeResult`, `IngestPipeline`, `IngestResult` to `__all__`; add `DocumentStore` import from `document_store` module

### Constraints
- No PydanticAI imports in any modified file
- `ruff check` clean on all new/modified files
- Use existing `CancelSignal` from `cancellation.py` and `sandbox_path` from `_paths.py` â€” do NOT recreate
- MCP server constructor change expected â€” wiring update tracked by #55

## Context
Split from #33 per research (docs/research/extract-entity-extraction-graph-builders.md S4). The v1 IngestPipeline is ~395 LOC; intake is ~76 LOC; DocumentStore is ~280 LOC. See docs/research/intake-ingest-pipeline-modules.md for full findings. GraphEnricher is OUT of scope (separate concern per ingest-complexity-reduction research).

## Research
See docs/research/intake-ingest-pipeline-modules.md for full findings.

[[2026-03-30]] Mon 08:16
## Architecture Review
See docs/scratch/158-architect.md for full review.
