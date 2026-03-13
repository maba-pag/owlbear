---
id: 248
title: Implement BgeM3EmbeddingProvider
status: archived
priority: needed
created: 2026-02-28T12:38:59.179835+01:00
updated: 2026-02-28T23:54:25.4561123+01:00
started: 2026-02-28T16:34:30.4442563+01:00
completed: 2026-02-28T23:54:25.4561123+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
depends_on:
    - 247
class: standard
---

## Context

Wrap FlagEmbedding BGEM3FlagModel. Lazy loading, embed_hybrid() returns dense+sparse+ColBERT in one pass. Replaces FastEmbedProvider.

## Research Done

- docs/research/bge-m3-integration.md (328 lines) — full code analysis
- FP16 auto-disabled on CPU, FP32 ~3.0 GB RAM
- Sparse output: Dict[str(token_id), float], positive-only (ReLU)
- ColBERT output: ndarray (T-1, 1024), skip CLS
- Constructor is NOT lazy — we must wrap with lazy init ourselves
- Adapter pattern from §3.10: ~80 LOC

## Research Answers (Architect Decisions)

### Q1: Idle-timeout model unloading?

Deferred — YAGNI for this task. Provide manual `unload()` only. Idle-timeout is a separate follow-up task if needed.

### Q2: Batch size tuning?

Default `batch_size=16` for CPU (16 GB RAM). BGEM3FlagModel auto-reduces on OOM. No auto-tuning needed in our adapter.

### Q3: Wrap FlagEmbedding or thin torch wrapper?

Use FlagEmbedding BGEM3FlagModel directly. Rationale: PyTorch already present for BGERerankerProvider, all 3 outputs from one call, upstream-maintained. See research doc §4.

### Q4: Test with actual model?

CI tests mock BGEM3FlagModel. Manual model benchmarking is a separate task.

## Acceptance Criteria

- [ ] `BgeM3EmbeddingProvider` class in `src/owlbear/memory/knowledge/embeddings.py` (same module as FastEmbedProvider)
- [ ] Implements `EmbeddingProvider` protocol: `embed(texts) -> list[list[float]]` (dense only, 1024d)
- [ ] `embed_hybrid(texts: list[str]) -> list[HybridEmbedding]` — one HybridEmbedding per input text:
  - `dense`: `list[float]` from `encode()["dense_vecs"]` row (1024d)
  - `sparse`: `SparseVector(indices=[int(k) for k in d.keys()], values=list(d.values()))` from `encode()["lexical_weights"]` entry
  - `colbert`: `ndarray.tolist()` from `encode()["colbert_vecs"]` entry — shape (T-1, 1024)
- [ ] Constructor: `model_name: str = "BAAI/bge-m3"`, `batch_size: int = 16`
- [ ] Lazy loading via `_ensure_model()` — first call to `embed()` or `embed_hybrid()` creates `BGEM3FlagModel`
- [ ] `unload()` method: `self._model = None` + `gc.collect()` — releases ~3 GB RAM
- [ ] `ImportError` with helpful message when FlagEmbedding not installed — guard in `_ensure_model()`, mirror `BGERerankerProvider` pattern
- [ ] `embed([])` and `embed_hybrid([])` return empty list without loading model
- [ ] Do NOT add FlagEmbedding to `pyproject.toml` yet (deferred to #250)

## TDD — tests in `tests/test_knowledge_embeddings.py`

- [ ] `BgeM3EmbeddingProvider` satisfies `EmbeddingProvider` protocol (`isinstance` check)
- [ ] `embed()` returns `list[list[float]]` with correct length and 1024d vectors
- [ ] `embed_hybrid()` returns `list[HybridEmbedding]` with all 3 fields populated
- [ ] Lazy loading: `_model` is `None` until first `embed()`/`embed_hybrid()` call
- [ ] `unload()` sets `_model` to `None`
- [ ] `ImportError` raised when FlagEmbedding not installed (mock import failure)
- [ ] Empty input returns empty output without loading model
- [ ] All tests mock `BGEM3FlagModel` — no real model download in CI

## Architecture Notes

- Follow `BGERerankerProvider` pattern in `reranker.py`: lazy `from FlagEmbedding import BGEM3FlagModel` in `_ensure_model()`
- `embed_hybrid()` is NOT part of `EmbeddingProvider` protocol — it's an extra method for hybrid-aware callers
- Import `SparseVector`, `HybridEmbedding` from `owlbear.memory.knowledge.protocol` (#247)
- ~80 LOC estimate (research doc §3.10)
