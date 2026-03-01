---
id: 308
title: Test KnowledgeToolset — mock knowledge components
status: archived
priority: critical
created: 2026-03-01T03:51:13.0143876+01:00
updated: 2026-03-01T17:09:34.0210306+01:00
started: 2026-03-01T04:36:16.0846658+01:00
completed: 2026-03-01T17:09:34.0210306+01:00
tags:
    - phase-11
    - knowledge-graph
    - tools
    - test
class: standard
---

## Context
Preceding test task for #291 (KnowledgeToolset implementation).
TDD: write tests first, then implement.

## Acceptance Criteria
- [ ] Test file: tests/test_knowledge_toolset.py
- [ ] Fixtures: mock_graph_store (MagicMock), mock_vector_store (MagicMock), mock_embedder (MagicMock spec=['embed']), mock_ingest_pipeline (MagicMock with ingest=AsyncMock, ingest_text=AsyncMock), workspace_root (tmp_path)
- [ ] test_query_knowledge_returns_formatted_results -- embed called with [query], search_similar called with dense vector + top_k + embedding_type='document', get_document resolves IDs, output is numbered list
- [ ] test_query_knowledge_empty_results -- search_similar returns [], output is 'No results found.'
- [ ] test_query_knowledge_missing_document -- get_document returns None for an ID, skipped gracefully
- [ ] test_ingest_document_text -- doc_type='text' delegates to ingest_pipeline.ingest_text(source)
- [ ] test_ingest_document_file -- doc_type='file' calls _safe_path, delegates to ingest_pipeline.ingest(Path)
- [ ] test_ingest_document_url -- doc_type='url' delegates to ingest_pipeline.ingest(source)
- [ ] test_ingest_document_invalid_type -- doc_type='pdf' raises ValueError
- [ ] test_ingest_document_file_traversal -- path escaping workspace raises PermissionError
- [ ] test_list_knowledge_sources_formats_table -- list_documents returns docs, output is formatted list
- [ ] test_list_knowledge_sources_empty -- list_documents returns [], output is 'No documents ingested.'
- [ ] test_toolset_registers_three_tools -- verify add_function called 3x with correct names
- [ ] >= 90% coverage on test file
