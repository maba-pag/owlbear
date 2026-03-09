---
id: 674
title: Tests for DocumentStore and GraphEnricher extraction
status: archived
priority: needed
created: 2026-03-08T03:00:29.8302888+01:00
updated: 2026-03-09T00:41:16.0590457+01:00
started: 2026-03-08T13:23:51.2900936+01:00
completed: 2026-03-09T00:41:16.0590457+01:00
tags:
    - test
    - modularity
    - knowledge
depends_on:
    - 671
class: standard
---

Write unit tests for the extracted DocumentStore and GraphEnricher classes from #671 and #672. AC: (1) test_document_store.py covers: find_status_by_source (found/not found), check_content_changed (changed/unchanged), delete_document_data (cascading delete of chunks+vectors+entities), store_chunks, store_embeddings, store_extractions. (2) test_enrichment.py covers: schedule_graph_enrichment creates background task, semaphore limits concurrency, inter-doc scheduling. (3) Existing test_knowledge_ingest.py still passes (pipeline orchestration unchanged). (4) All tests pass; ruff clean.

[[2026-03-08]] Sun 23:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 00:41
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: find_status_by_source (found/not found) | TestDocumentStoreFindStatus: test_not_found + test_found, pass | .97 |
| AC1: check_content_changed (changed/unchanged) | TestDocumentStoreContentChanged: 3 cases (new/unchanged/changed), pass | .97 |
| AC1: delete_document_data (cascade chunks+vectors+entities) | TestDocumentStoreDelete::test_cascade_delete inserts entities+edges into SQLite, verifies all 0 after delete. Source L325-364 confirms cascade. | .97 |
| AC1: store_chunks | TestDocumentStoreChunks::test_stores_chunks_returns_ids, pass | .97 |
| AC1: store_embeddings | TestDocumentStoreEmbeddings::test_stores_embeddings, pass | .97 |
| AC1: store_extractions | TestDocumentStoreExtractions::test_stores_entities_and_edges, pass | .97 |
| AC2: schedule_graph_enrichment creates bg task | TestScheduleGraphEnrichment::test_schedules_task (anyio), pass | .97 |
| AC2: semaphore limits concurrency | TestEnricherSemaphoreBounds: graph + inter-doc bounded to bg_concurrency=2, pass | .97 |
| AC2: inter-doc scheduling | TestScheduleInterDocEnrichment::test_schedules_task + skip/no-op cases, pass | .97 |
| AC3: test_knowledge_ingest.py still passes | 91 passed in 3.18s | .97 |
| AC4: all tests pass, ruff clean | 42 passed (doc_store + enrichment), ruff all checks passed | .97 |

### Note
Block reason 'cascade delete test missing entity/edge coverage' is stale. TestDocumentStoreDelete::test_cascade_delete (L237) now inserts entities and edges directly into SQLite and verifies all are deleted. Unblocked.
