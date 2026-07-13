---
id: 504
title: 'Delete dead knowledge modules: dedup.py and reranker.py'
status: archived
priority: medium
created: 2026-03-04 07:38:16.879398+01:00
updated: 2026-03-07 18:07:58.447301+01:00
started: 2026-03-06 19:25:59.366257+01:00
completed: 2026-03-07 18:07:58.447301+01:00
tags:
- audit
- yagni
- knowledge
class: standard
archival_reason: completed
archival_refs: []
---

Delete the two dead knowledge modules and their tests. Neither module is imported by any production code, exported from `__init__.py`, or wired into any pipeline.

## Acceptance Criteria

- [ ] `src/owlbear/memory/knowledge/dedup.py` deleted
- [ ] `src/owlbear/memory/knowledge/reranker.py` deleted
- [ ] `tests/test_knowledge_dedup.py` deleted
- [ ] `tests/test_knowledge_reranker.py` deleted
- [ ] `FlagEmbedding` remains in `pyproject.toml` `[project.optional-dependencies].knowledge` (still needed by `embeddings.py`)
- [ ] `knowledge/__init__.py` has no references to `dedup` or `reranker` (already true  verify unchanged)
- [ ] `uv run pytest -q --tb=short` passes with no new failures
- [ ] `uv run ruff check src/ tests/` clean

## Architecture Notes

- **reranker.py** (79 LOC): Superseded by ColBERT max_sim in `QdrantVectorStore._prefetch_rescore_hybrid()`. Cross-encoder path was never wired in, costs ~3 GB RAM, 40-150x slower. See docs/research/colbert-vs-crossencoder.md.
- **dedup.py** (131 LOC): Planned as ingest step 5 but never integrated. O(n^2) SequenceMatcher won't scale. If dedup is needed later, redesign with embedding similarity.
- **Total removal**: 4 files, ~875 lines (209 src + 666 test). Recoverable from git history.
- **No production imports**: grep confirms zero imports outside the modules' own test files.
- **No `__init__.py` exports**: neither module is listed in `knowledge/__all__`.
- **`FlagEmbedding` dep stays**: `embeddings.py` uses `BGEM3FlagModel` from the same package.

## Sources

- docs/integration-audit.md (INT-14)
- docs/research/colbert-vs-crossencoder.md (#239, .80 confidence)
- docs/research/knowledge-ingestion.md (step 5 never wired)
