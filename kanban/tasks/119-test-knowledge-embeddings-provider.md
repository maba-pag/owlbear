---
id: 119
title: Test knowledge embeddings provider
status: todo
priority: high
created: 2026-02-27T03:42:51.8453017+01:00
updated: 2026-02-27T03:45:28.9921884+01:00
tags:
    - memory
    - knowledge-graph
    - test
    - phase-2
depends_on:
    - 106
class: standard
---

TDD test suite for `owlbear.memory.knowledge.embeddings`. Write tests BEFORE implementation (#111).

## Acceptance Criteria

- [ ] New file: `tests/test_knowledge_embeddings.py`
- [ ] Test `EmbeddingProvider` protocol — verify it defines `embed(texts: list[str]) -> list[list[float]]`
- [ ] Test `FastEmbedProvider` conforms to `EmbeddingProvider` protocol (runtime_checkable or isinstance)
- [ ] Test `FastEmbedProvider()` default model_name is `'BAAI/bge-small-en-v1.5'`
- [ ] Test `FastEmbedProvider.dimension` property returns 384 for default model
- [ ] Test `embed([])` returns `[]` (empty input)
- [ ] Test `embed(['hello'])` returns `list[list[float]]` with one vector of length 384
- [ ] Test `embed(['hello', 'world'])` returns 2 vectors, each of length 384
- [ ] Test lazy initialization — `TextEmbedding` not imported until first `embed()` call (mock fastembed)
- [ ] Test `DEFAULT_MODEL` and `DEFAULT_DIMENSION` module constants
- [ ] Mark integration tests (real FastEmbed model download) with `@pytest.mark.slow`
- [ ] Unit tests mock `fastembed.TextEmbedding` to avoid model download in CI
- [ ] All tests initially fail (import error) until #111 implements the module
- [ ] `ruff check` clean on test file
