# EntityExtractor Code-Corpus Recall Harness

> **Owning task:** #906 - Build EntityExtractor code-corpus recall benchmark harness
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #891 established benchmark-first as the safe path for `EntityExtractor`
work. Task #906 narrows that into an implementation question: how should OwlBear
build a repo-native recall harness for the current single-pass extractor so that
the benchmark uses representative code-and-doc samples, stable gold annotations,
and reportable recall metrics without requiring real model calls in unit tests?

The answer needs to fit current repo patterns. OwlBear already has custom
benchmark code in `tests/benchmarks/`, already registers an opt-in `benchmark`
marker in `pyproject.toml`, and already treats real model calls as something to
block or stub in normal tests.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| scikit-learn `recall_score` | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | .90 | Recall definition plus `micro`, `macro`, and per-label scoring options |
| spaCy `Scorer` | <https://spacy.io/api/scorer> | .85 | `ents_r` and `ents_per_type` prior art for overall and per-type reporting |
| pytest marker docs | <https://docs.pytest.org/en/stable/example/markers.html> | .80 | Registered custom markers and `-m` selection for opt-in benchmark runs |
| Microsoft GraphRAG dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | .80 | TextUnit provenance and merge-by-title-and-type extraction model |
| Existing local benchmark pattern | `tests/benchmarks/bench_graph_expansion.py` | .95 | Checked-in data, custom scorer, optional `@pytest.mark.benchmark`, formatted output |
| Retrieval benchmark helpers | `tests/benchmarks/harness.py`; `tests/benchmarks/evaluate.py` | .90 | Existing helpers are `ranx`-oriented and designed for query-doc retrieval, not entity recall |
| Entity extraction contract | `src/owlbear/memory/knowledge/extractor.py` | .95 | Current extractor shape, empty-result-on-failure behavior, and per-call usage recording |
| Entity model | `src/owlbear/memory/knowledge/models.py` | .90 | `Entity.id` is UUID-based, so benchmark gold cannot key on ids |
| Ingest flow | `src/owlbear/memory/knowledge/ingest.py` | .85 | Extraction is chunk-oriented and preserves metadata/provenance per chunk |
| No-real-model test precedent | `tests/test_knowledge_extractor.py` | .90 | Repo-standard pattern is to stub extractor behavior and block live model requests |
| Benchmark config | `pyproject.toml` | .85 | Existing `benchmark` marker and benchmark extras do not include sklearn or spaCy |
| Upstream benchmark recommendation | `docs/research/entity-extractor-gleaning-benchmark.md` | .90 | Prior task already recommends benchmark-first and stable `(name, entity_type)` keys |

## 3. Analysis

### 3.1 Harness Shape

| Option | Repo fit | Dependency cost | Testability | Verdict |
|--------|----------|-----------------|-------------|---------|
| Reuse `ranx` retrieval helpers directly | Low | Low | Medium | Reject |
| Add sklearn or spaCy as benchmark dependencies | Medium | High | High | Reject |
| Add a small custom scorer in `tests/benchmarks/` | High | Low | High | Best fit |

`tests/benchmarks/harness.py` and `tests/benchmarks/evaluate.py` are built for
query-document relevance objects (`Qrels`, `Run`, `ndcg@10`, `precision@10`,
`mrr`). #906 needs exact-match entity-set comparison instead. The sklearn and
spaCy docs are useful references for metric semantics, but the required scorer is
small enough that OwlBear should implement it locally rather than add new
benchmark dependencies.

Recommended metrics:

- Primary: micro recall on exact gold-vs-predicted entity keys.
- Secondary: per-type recall.
- Supporting: predicted entity count per sample or run.

### 3.2 Corpus and Gold Data Shape

| Option | Fidelity | Drift risk | Unit-testability | Verdict |
|--------|----------|------------|------------------|---------|
| Live repo crawl at runtime | High | High | Low | Reject |
| Synthetic snippets only | Low | Low | High | Reject |
| Checked-in curated OwlBear sample | High | Medium | High | Recommend |

The benchmark should use trimmed, checked-in OwlBear excerpts rather than a live
repo walk. That keeps runs deterministic, avoids coupling tests to unrelated repo
changes, and still matches the current ingest shape where extraction happens per
chunk with metadata.

Gold annotations should key entities by `(normalized_name, entity_type)`, not by
`Entity.id`. `Entity.id` is random UUID hex in current models, while GraphRAG's
merge behavior is title-and-type based. Stable textual keys are the only viable
benchmark contract.

Minimum corpus shape:

- Python-source samples and Markdown-doc samples both represented.
- Stable source labels and sample metadata checked into the repo.
- Trimmed excerpts, not full-file snapshots.
- Gold entities stored independently from model-generated ids.

### 3.3 Execution Model

| Option | Contract tests | Benchmark realism | Verdict |
|--------|----------------|-------------------|---------|
| Real model calls in normal tests | Poor | High | Reject |
| Stubbed extractor outputs in tests, opt-in live benchmark path | High | High | Recommend |
| Scorer-only helpers with no runnable harness | Medium | Low | Incomplete |

`tests/test_knowledge_extractor.py` already blocks real model requests and
stubs the extractor boundary. `pyproject.toml` already registers a `benchmark`
marker, and pytest markers support opt-in selection with `-m`. The harness should
therefore support two modes:

- Deterministic contract tests that stub extractor outputs.
- An opt-in benchmark-marked path for real extractor runs when a human chooses
  to measure live behavior.

That preserves unit-testability while still leaving a practical measurement path
for later tasks like #908.

### 3.4 Recommended Task Split

| Slice | Why it should be separate | Likely files |
|-------|---------------------------|--------------|
| Corpus and gold schema (RED/GREEN) | Keeps fixture design, provenance, and stable-key rules separate from runner behavior | `tests/benchmarks/test_entity_extractor_corpus.py`, `tests/benchmarks/entity_extractor_corpus.py` or equivalent fixture files |
| Recall harness and reporting (RED/GREEN) | Keeps scoring, execution, and report formatting separate from checked-in sample curation | `tests/benchmarks/test_entity_extractor_recall.py`, `tests/benchmarks/bench_entity_extractor_recall.py` |

This split fits OwlBear's TDD rules better than sending #906 directly to a
builder as one mixed benchmark card.

## 4. Recommendation (.89 confidence)

Build the benchmark around a checked-in OwlBear sample corpus, stable gold keys
`(normalized_name, entity_type)`, and a small custom scorer that reports micro
recall and per-type recall. Keep contract tests model-free by stubbing extractor
outputs, and make any real benchmark execution opt-in under the existing
`@pytest.mark.benchmark` workflow. Treat #906 as the parent tracker and execute
it through two RED/GREEN pairs: corpus/schema first, then harness/reporting.

## 5. Follow-up Tasks

1. **Test EntityExtractor benchmark corpus and gold schema (RED)** - Priority:
   nice-to-have. Dependencies: none. One-line AC: add failing tests for a
   checked-in Python+Markdown corpus with stable `(normalized_name,
   entity_type)` gold keys and no live model dependency. Created: #911.

2. **Build EntityExtractor benchmark corpus and gold schema** - Priority:
   nice-to-have. Dependencies: #911. One-line AC: add the checked-in benchmark
   sample set and gold annotations under `tests/benchmarks/` without relying on
   live repo crawling or UUID ids. Created: #912.

3. **Test EntityExtractor recall harness and reporting (RED)** - Priority:
   nice-to-have. Dependencies: #912. One-line AC: add failing tests for a custom
   micro-recall plus per-type-recall runner that uses stubbed extractor outputs
   and links run instructions back to this research doc. Created: #913.

4. **Build EntityExtractor recall harness and reporting** - Priority:
   nice-to-have. Dependencies: #912, #913. One-line AC: implement the custom
   scorer, benchmark runner, and formatted output using the checked-in corpus and
   the existing opt-in benchmark marker flow. Created: #914.
