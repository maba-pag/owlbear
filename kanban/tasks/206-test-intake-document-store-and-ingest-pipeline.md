---
id: 206
title: 'Test: intake, document_store, and ingest pipeline modules'
status: in-progress
priority: needed
created: 2026-03-30T08:14:52.468527+02:00
updated: 2026-03-30T10:00:10.8117233+02:00
tags:
    - phase-1
    - scope:knowledge
    - test
class: standard
---

TDD RED tests for #158. All tests must FAIL before builder implements.

## intake.py tests
- [ ] IntakeResult model: frozen Pydantic with content, source, metadata fields
- [ ] read_file success: mock Path.read_text via asyncio.to_thread, verifies metadata source_type=file and fetched_at present
- [ ] read_file sandbox rejection: PermissionError when path traverses outside workspace_root (via _paths.sandbox_path)
- [ ] read_file missing: FileNotFoundError when file does not exist
- [ ] read_url success: mock httpx.AsyncClient.get, verifies metadata source_type=url
- [ ] read_url error: httpx.HTTPStatusError on non-2xx response
- [ ] read_text: sync wrapper returns IntakeResult with source_type=text metadata

## document_store.py tests
- [ ] Constructor: accepts conn, GraphStore, VectorStoreProtocol, EmbeddingProvider
- [ ] insert_document: inserts row into documents table (in-memory SQLite + init_db)
- [ ] store_chunks: inserts chunk rows, returns chunk_ids matching input count
- [ ] store_embeddings: calls VectorStoreProtocol.store_embedding per chunk
- [ ] store_extractions: calls GraphStore.insert_entity/insert_edge, returns (entity_count, edge_count)
- [ ] store_entity_embeddings: embeds entity descriptions via EmbeddingProvider, stores as entity type
- [ ] delete_document_data: cascade deletes chunks, edges, entities, documents, document_status rows
- [ ] Status roundtrip: set_status then find_status_by_source returns correct DocumentStatus
- [ ] check_content_changed: returns (True, None) for new content, (False, doc_id) for unchanged, (True, doc_id) for changed

## ingest.py upgrade tests
- [ ] IngestPipeline constructor accepts DocumentStore (from document_store.py), EntityExtractor, TextChunker, optional CancelSignal
- [ ] ingest_text preserved signature: (text, metadata=None, scope=global) returns IngestResult
- [ ] ingest takes IntakeResult, returns IngestResult with correct entity/edge counts
- [ ] Delta detection: unchanged content returns IngestResult(status=skipped)
- [ ] Parallel: asyncio.gather runs embed+extract concurrently (verify both called)
- [ ] CancelSignal: returns IngestResult(status=cancelled) when signal.is_set() is True
- [ ] Error handling: internal exception returns IngestResult(status=failed)
- [ ] IngestResult status values: ok, failed, skipped, cancelled

## Integration test
- [ ] E2E: text input with mock extractor returning canned entities+edges, verify graph_store has entities and edges, vector_store has embeddings

[[2026-03-30]] Mon 08:50
## Test-Writer Notes
- Test file: tests/test_knowledge_intake_docstore_ingest.py
- Classes: 22 TestFromAC_ classes
- Tests per category: happy 18, edge 6, error 11, boundary 5, integration 3
- Total: 53 tests, all FAIL
- ruff: clean
- AC coverage: all AC lines covered (IntakeResult, read_file, read_url, read_text, DocumentStore x8 methods, IngestPipeline upgrade x7, E2E x2)

[[2026-03-30]] Mon 09:16
## Builder Notes
- Files changed: intake.py (new), document_store.py (new), ingest.py (upgraded), server.py (updated import and ctor)
- Tests: 53 passed, coverage intake.py=100%, document_store.py=95%, ingest.py=95%
- Lint: ruff clean
- Fixes applied: SQLite thread-safety, FK constraint placeholder, IngestResult Pydantic Literal status

[[2026-03-30]] Mon 09:41
## Review Evidence

### Test Results
- pytest tests/test_knowledge_intake_docstore_ingest.py: **53 passed, 0 failed**

### Lint Results
- ruff check intake.py, document_store.py, ingest.py, test file: **All checks passed!**

### Coverage
intake.py: 100%; document_store.py: 95% (missed: 99, 115, 162); ingest.py: 95% (missed: 109-111)

### TestFromAC Modifications
All 22 TestFromAC_ classes preserved, no builder modifications.

### AC Compliance

| AC Line | Verdict |
|---------|---------|
| IntakeResult frozen Pydantic model | COVERED |
| read_file success, file metadata | COVERED |
| read_file sandbox rejection | COVERED |
| read_file missing FileNotFoundError | COVERED |
| read_url success, url metadata | COVERED |
| read_url HTTPStatusError on non-2xx | COVERED |
| read_text sync wrapper, source_type=text | COVERED |
| DocumentStore constructor | COVERED |
| insert_document: inserts row in documents | COVERED |
| store_chunks: inserts rows, returns chunk_ids | COVERED |
| store_embeddings: calls VectorStoreProtocol.store_embedding | COVERED |
| store_extractions: calls insert_entity/insert_edge returns counts | COVERED |
| store_entity_embeddings: entity type embedding | COVERED |
| delete_document_data: cascade deletes chunks/edges/entities/documents/status | **LAX** - entity+edge deletion path at line 162 never triggered; no test inserts entities before delete |
| Status roundtrip: set_status and find_status_by_source | COVERED |
| check_content_changed: (True,None)/(False,id)/(True,id) | COVERED |
| IngestPipeline constructor w/ optional CancelSignal | COVERED |
| ingest_text preserved signature | COVERED |
| ingest takes IntakeResult, returns IngestResult | COVERED |
| Delta detection: unchanged returns skipped | COVERED |
| Parallel: embed+extract both called | COVERED |
| CancelSignal: returns cancelled when signal.is_set() | COVERED |
| Error handling: internal exception returns failed | **LAX** - TestFromAC only tests ingest(), ingest_text() except block (L109-111) uncovered; no compensating test |
| IngestResult status values: ok/failed/skipped/cancelled | COVERED |
| E2E: text+mock extractor, verify graph+vector populated | COVERED |

### No TestBuilderDiscovered class found - LAX escalated to FAIL

### Critical Finding 1 - delete_document_data entity/edge path

AC says 'cascade deletes...edges, entities'. TestFromAC_DocumentStoreDelete (3 tests) verifies document, chunks, status ONLY. No test creates entities+edges before calling delete_document_data; line 162 (entity edge loop) never executed. Removing edge deletion code would not fail any test.

Additional concern: store_extractions inserts entities via insert_entity(entity) where Entity objects are created without document_id set. document_store.delete_document_data queries WHERE document_id = ?, so entities inserted through the pipeline (with document_id=NULL) are never cleaned up. This is a potential behavioral bug.

### Critical Finding 2 - ingest_text error handler

ingest.py lines 109-111 are the except Exception handler in ingest_text. TestFromAC_IngestErrorHandling only exercises ingest(), not ingest_text(). The ingest_text error handler is uncompensated.

### Verdict: FAIL - Confidence 0.78

Return to todo: test-writer must add (1) delete_document_data test with entities+edges (verify cascade), (2) ingest_text error path test (simulate exception, verify status=failed).

[[2026-03-30]] Mon 09:42
---
## Review Evidence

### Test Results
- pytest 53 passed, 0 failed
- ruff: All checks passed

### Coverage
- intake.py: 100%
- document_store.py: 95% (missed L99, L115, L162)
- ingest.py: 95% (missed L109-111)

### TestFromAC Modifications
All 22 TestFromAC_ classes preserved, no builder modifications detected.

### AC Compliance

22 of 24 AC lines: COVERED. 2 LAX findings:

LAX-1: delete_document_data AC says cascade deletes edges and entities, but TestFromAC_DocumentStoreDelete (3 tests) never inserts entities or edges before calling delete_document_data. Line 162 entity-edge deletion loop in document_store.py is never executed. Removing the edge deletion code would not fail any test. No TestBuilderDiscovered compensation. Additional concern: store_extractions inserts entities without document_id set (default None), so delete_document_data WHERE document_id=? can never find pipeline-inserted entities - potential behavioral bug.

LAX-2: Error handling AC tests ingest() only. ingest_text() except block (lines 109-111 ingest.py) is untested. No TestBuilderDiscovered compensation.

### Verdict: FAIL - Confidence 0.78

No TestBuilderDiscovered class found. LAX findings without compensation escalated to FAIL per review protocol.

Return to todo. Test-writer must add:
1. delete_document_data test: insert Document with entities+edges (document_id set), call delete_document_data, verify entities and edges removed
2. ingest_text error path test: simulate exception in chunker or store, verify IngestResult(status=failed)
---

[[2026-03-30]] Mon 09:43
---
## Review Evidence

### Test Results
- pytest 53 passed, 0 failed
- ruff: All checks passed

### Coverage
- intake.py: 100%
- document_store.py: 95% (missed L99, L115, L162)
- ingest.py: 95% (missed L109-111)

### TestFromAC Modifications
All 22 TestFromAC_ classes preserved, no builder modifications detected.

### AC Compliance

22 of 24 AC lines: COVERED. 2 LAX findings:

LAX-1: delete_document_data AC says cascade deletes edges and entities, but TestFromAC_DocumentStoreDelete (3 tests) never inserts entities or edges before calling delete_document_data. Line 162 entity-edge deletion loop in document_store.py is never executed. Removing the edge deletion code would not fail any test. No TestBuilderDiscovered compensation. Additional concern: store_extractions inserts entities without document_id set (default None), so delete_document_data WHERE document_id=? can never find pipeline-inserted entities - potential behavioral bug.

LAX-2: Error handling AC tests ingest() only. ingest_text() except block (lines 109-111 ingest.py) is untested. No TestBuilderDiscovered compensation.

### Verdict: FAIL - Confidence 0.78

No TestBuilderDiscovered class found. LAX findings without compensation escalated to FAIL per review protocol.

Return to todo. Test-writer must add:
1. delete_document_data test: insert Document with entities+edges (document_id set), call delete_document_data, verify entities and edges removed
2. ingest_text error path test: simulate exception in chunker or store, verify IngestResult(status=failed)
---
