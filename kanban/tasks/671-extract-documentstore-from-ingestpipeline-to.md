---
id: 671
title: Extract DocumentStore from IngestPipeline to document_store.py
status: archived
priority: needed
created: 2026-03-08T03:00:05.9284428+01:00
updated: 2026-03-09T00:41:27.005265+01:00
started: 2026-03-08T03:43:54.1526019+01:00
completed: 2026-03-09T00:41:27.005265+01:00
tags:
    - modularity
    - knowledge
class: standard
---

Move document CRUD, status tracking, chunk/embedding/extraction storage, and content hashing from IngestPipeline to a new DocumentStore class in src/owlbear/memory/knowledge/document_store.py. AC: (1) DocumentStore class exists in document_store.py with methods: find_status_by_source, check_content_changed, delete_document_data, store_chunks, store_embeddings, store_extractions, store_entity_embeddings, insert_document, set_status, update_content_hash. (2) DocumentStatus model and compute_content_hash function moved to document_store.py. (3) IngestPipeline.__init__ accepts a DocumentStore parameter. (4) IngestPipeline delegates all storage/CRUD calls to self._store (DocumentStore instance). (5) bootstrap.py constructs DocumentStore and passes it to IngestPipeline. (6) All existing tests pass unchanged (update imports only). (7) Ruff clean. (8) No circular imports -- document_store.py depends only on leaf modules (graph.py, chunker.py, extractor.py, intake.py, protocol types). See docs/research/ingest-complexity-reduction.md.

[[2026-03-08]] Sun 23:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 00:41
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: DocumentStore with 10 methods | All 10 present in document_store.py L122-325 | .97 |
| AC2: DocumentStatus + compute_content_hash | Both in document_store.py L40-66 | .97 |
| AC3: IngestPipeline accepts DocumentStore | ingest.py L87 store param | .97 |
| AC4: Delegates via self._store | 16 calls in ingest.py | .97 |
| AC5: bootstrap constructs DocumentStore | bootstrap/knowledge.py L136-162 | .97 |
| AC6: All tests pass | 1271 passed, 1 unrelated fail (slack_sdk) | .97 |
| AC7: Ruff clean | All checks passed | .97 |
| AC8: No circular imports | Verified via python import | .97 |

### Verdict
Confidence: .97
