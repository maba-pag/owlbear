---
id: 504
title: Wire or remove dead knowledge modules dedup and reranker
status: backlog
priority: important
created: 2026-03-04T07:38:16.8793979+01:00
updated: 2026-03-06T19:25:59.3662573+01:00
started: 2026-03-06T19:25:59.3662573+01:00
tags:
    - audit
    - yagni
    - knowledge
class: standard
---

INT-14: knowledge/dedup.py and knowledge/reranker.py are never imported anywhere except their own test files. Wire into ingest/retrieval pipeline or delete. Dead code with tests is still dead code. AC: modules used in production or removed. See docs/integration-audit.md.

## Research Findings (2026-03-06)

### 1. Import Analysis  Both modules are dead code

| Module | Lines (src) | Lines (test) | Production imports | `__init__.py` export |
|--------|------------|-------------|-------------------|----------------------|
| `dedup.py` | 130 | 468 | **0** | No |
| `reranker.py` | 79 | 198 | **0** | No |

Neither module is imported by any production code. Combined: **209 LOC source + 666 LOC test = 875 lines of dead code**.

### 2. reranker.py  Superseded by ColBERT

`BGERerankerProvider` wraps `FlagEmbedding.FlagReranker` (568M param cross-encoder, ~3 GB RAM). Research #239 (docs/colbert-vs-crossencoder-research.md, .80 confidence) concluded:

- ColBERT max_sim reranking is **40-150x faster** than cross-encoder on CPU
- Quality gap is only ~1-2 nDCG@10 points, shrinks further with hybrid retrieval
- Saves ~3 GB RAM on 16 GB hardware
- **Already implemented**: `QdrantVectorStore` uses prefetchColBERT rescore natively

The research explicitly recommended keeping the code as optional fallback. However, it was never wired in and no config toggle was added. With ColBERT already handling reranking server-side, this module has no near-term use case.

**Verdict: Delete.** YAGNI  the cross-encoder path has been superseded. If ever needed again, the ~79 LOC can be reconstructed from git history. Keeping it creates maintenance burden and misleading test coverage.

### 3. dedup.py  Never wired, O(n²) scaling concern

Originally planned as step 5 of the ingest pipeline (knowledge-ingestion-research.md). The pipeline was implemented WITHOUT it: intake  chunk  embed+extract  store  graph enrichment. No dedup step exists.

Concerns with current implementation:
- **O(n²) SequenceMatcher**: compares all entity pairs. Poor scaling for large graphs.
- **No trigger point**: neither post-ingest hook nor scheduled maintenance calls it
- **difflib-only**: fuzzy string matching without embedding similarity is brittle for semantic duplicates

**Verdict: Delete.** YAGNI  never integrated, O(n²) won't scale, and when dedup is truly needed it should use embedding-based similarity (already available via bge-m3) rather than string matching. Can be reconstructed from git history if needed.

### 4. Recommendation (.85 confidence)

**Delete both modules and their tests.** Total removal: 4 files, ~875 lines.

| File | Action |
|------|--------|
| `src/owlbear/memory/knowledge/dedup.py` | Delete |
| `src/owlbear/memory/knowledge/reranker.py` | Delete |
| `tests/test_knowledge_dedup.py` | Delete |
| `tests/test_knowledge_reranker.py` | Delete |

Risk: Low. Neither is called anywhere. Both are recoverable from git history. ColBERT reranking is already the production path. Entity dedup, if needed, should be redesigned with embedding similarity.

### Sources
- docs/integration-audit.md (INT-14)
- docs/colbert-vs-crossencoder-research.md (task #239, .80 confidence: drop cross-encoder)
- docs/knowledge-ingestion-research.md (step 5 planned but never wired)
- Codebase grep: zero production imports of either module
- `knowledge/__init__.py`: neither module exported
