---
id: 111
title: Create owlbear.memory.knowledge.embeddings module
status: todo
priority: high
created: 2026-02-27T03:31:36.4284447+01:00
updated: 2026-02-27T03:45:34.2621493+01:00
started: 2026-02-27T03:32:49.8548519+01:00
tags:
    - memory
    - knowledge-graph
    - phase-2
depends_on:
    - 106
    - 119
class: standard
---

Local embedding generation using FastEmbed (ONNX). Protocol-based adapter pattern for future swapability.

## Acceptance Criteria

- [ ] New file: `src/owlbear/memory/knowledge/embeddings.py`
- [ ] `EmbeddingProvider` — `typing.Protocol` with method:
  - `embed(texts: list[str]) -> list[list[float]]` — batch embed, returns one vector per input text
- [ ] `FastEmbedProvider` class implementing `EmbeddingProvider`:
  - `__init__(model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: Path | None = None)`
  - Lazy-initializes `fastembed.TextEmbedding` on first `embed()` call (avoid import cost at module load)
  - `embed(texts)` returns `list[list[float]]` with vectors of length 384
  - Handles empty input list (returns `[]`)
- [ ] `dimension` property on `FastEmbedProvider` returning the embedding dimension (384 for default model)
- [ ] Module-level constant `DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"`
- [ ] Module-level constant `DEFAULT_DIMENSION = 384`
- [ ] `ruff check` clean
- [ ] No dependency on other knowledge modules (graph, schema, vectors) — embeddings is standalone

See docs/knowledge-graph-research.md section 3.3, 4
