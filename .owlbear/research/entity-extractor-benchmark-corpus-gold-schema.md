# EntityExtractor Benchmark Corpus and Gold Schema

> **Owning task:** #911 - Test EntityExtractor benchmark corpus and gold schema (RED)
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #911 is the research gate for the RED slice that defines the checked-in
benchmark corpus contract before #912 implements the fixture data. The question
here is narrower than #906: how should OwlBear store and validate the corpus so
tests can assert checked-in OwlBear text, stable source labels, stable gold
entity keys, deterministic ordering, and zero real-model dependency?

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| Microsoft GraphRAG inputs docs | <https://microsoft.github.io/graphrag/index/inputs/> | .90 | Stable document ids, text-plus-metadata schema, and JSON/text input patterns |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | .90 | TextUnit provenance and merge-by-title-and-type extraction semantics |
| spaCy data formats docs | <https://spacy.io/api/data-formats> | .85 | Checked-in corpus shapes pairing raw text with typed entity annotations |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | .80 | Exact-match PRF and per-type reporting conventions |
| PydanticAI testing docs | <https://ai.pydantic.dev/testing/> | .90 | `TestModel`, `FunctionModel`, and `ALLOW_MODEL_REQUESTS=False` for model-free tests |
| pytest marker docs | <https://docs.pytest.org/en/stable/example/markers.html> | .80 | Registered markers and `-m` selection for opt-in benchmark execution |
| Existing benchmark dataset pattern | `tests/benchmarks/routing_dataset.py` | .95 | Ordered checked-in dataset as typed Python records |
| Existing benchmark fixture pattern | `tests/benchmarks/bench_graph_expansion.py` | .95 | Checked-in corpus, explicit labels, and deterministic list order |
| Current entity model contract | `src/owlbear/memory/knowledge/models.py` | .95 | `Entity.id` is UUID-based and unsuitable as benchmark gold identity |
| Current no-live-model test pattern | `tests/test_knowledge_extractor.py`; `pyproject.toml` | .95 | Blocked model requests in normal tests and existing `benchmark` marker |

## 3. Analysis

### 3.1 Corpus Storage Options

| Option | Repo fit | Determinism | Schema clarity | Verdict |
|--------|----------|-------------|----------------|---------|
| Live repo crawl at test time | Low | Low | Low | Reject |
| Checked-in JSON manifest plus thin loader | High | High | High | Best fit |
| Python-only constants | High | High | Medium | Viable fallback |

The live-crawl option fails #911 directly: unrelated repo edits would change the
benchmark surface and filesystem traversal order would become part of the test
contract. OwlBear's local benchmark patterns already prefer checked-in ordered
records. A small JSON manifest plus a Python loader is the clearest fit for this
task because it separates benchmark data from test code while still keeping the
loader small and deterministic.

Recommended sample record fields:

- `source_label`: stable human-readable label used by tests and reports
- `source_kind`: `python` or `markdown`
- `origin_path`: original OwlBear file path for provenance
- `text`: trimmed checked-in excerpt
- `gold_entities`: ordered list of `{normalized_name, entity_type}` pairs

This mirrors GraphRAG's text-plus-metadata input shape and spaCy's
text-plus-annotation example structure without introducing a runtime benchmark
dependency.

### 3.2 Gold Key Options

| Option | Stability | Match to current extractor | Prior-art fit | Verdict |
|--------|-----------|----------------------------|---------------|---------|
| `Entity.id` UUIDs | Low | Low | Low | Reject |
| Character offsets plus type | Medium | Medium | Medium | Too brittle |
| `(normalized_name, entity_type)` | High | High | High | Recommend |

`Entity.id` cannot be the benchmark identity because OwlBear generates ids with
`uuid4().hex`. Offset-based gold is also a poor fit for trimmed benchmark
excerpts because any whitespace or formatting cleanup would churn the labels.
GraphRAG's merge behavior is title-and-type based, and spaCy's scoring/reporting
conventions are label-centric rather than generated-id-centric. The stable gold
contract should therefore stay textual: one canonical normalized name paired with
the current `EntityType` value.

Practical rule: keep normalization shallow and explicit in one helper shared by
loader and tests. The fixture should store the canonical gold spelling once and
never derive identity from model-generated ids.

### 3.3 Loader and Test Seam

| Option | Unit-test safety | Cost | Fit with #911 | Verdict |
|--------|------------------|------|---------------|---------|
| Build or validate corpus by invoking the extractor | Poor | Low | Low | Reject |
| Pure loader and validator over checked-in data | High | Low | High | Best fit |
| Benchmark-only path with no unit-level contract checks | Medium | Medium | Medium | Incomplete |

The RED task should test only the corpus contract. PydanticAI's testing guidance
and OwlBear's own extractor tests both treat real model calls as something to
block or replace. That means #911 should assert that corpus loading and schema
validation work with model requests disabled, while any live extractor run stays
in the later benchmark tasks under the existing `benchmark` marker.

### 3.4 Determinism and Coverage Rules

| Concern | Recommended rule | Why |
|---------|------------------|-----|
| Sample order | Preserve manifest array order exactly | Matches local benchmark datasets and avoids filesystem-order drift |
| Source labels | Store explicit stable labels, not generated hashes alone | Human-readable provenance is needed for failing tests and reports |
| Corpus text | Check in trimmed excerpts only | Keeps diffs reviewable and avoids live repo coupling |
| File mix | Include both Python and Markdown in the initial eight-sample minimum | Matches #911 AC and the extraction use case studied in #906 |
| Source scope | Prefer stable repo docs and knowledge-related modules, not scratch or kanban files | Reduces churn in a checked-in benchmark corpus |

No further split of #911 or #912 is needed. The existing RED/GREEN pair is the
right size; the missing piece is simply an explicit corpus contract so later
fixture edits do not silently redefine the benchmark.

## 4. Recommendation (.90 confidence)

Implement the corpus as a checked-in ordered manifest plus a thin loader under
`tests/benchmarks/`. Each sample should carry `source_label`, `source_kind`,
`origin_path`, trimmed `text`, and textual gold entities keyed by
`(normalized_name, entity_type)` using the current `EntityType` strings. The
RED tests in #911 should fail if the sample count drops below eight, either
source kind disappears, labels are duplicated, order changes, or loading the
corpus requires a real model call.

This keeps the corpus deterministic, reviewable, and aligned with both local
benchmark patterns and external extraction-evaluation prior art. Real extractor
execution remains an opt-in concern for #913 and #914, not for the corpus
contract tests.

## 5. Follow-up Tasks

1. **Build EntityExtractor benchmark corpus and gold schema** - Priority:
   nice-to-have. Dependencies: #911. One-line AC: implement the ordered checked-
   in corpus loader and manifest with stable source labels and textual gold
   keys. Existing task: #912.

2. **Document EntityExtractor benchmark corpus authoring contract** - Priority:
   nice-to-have. Dependencies: #912. One-line AC: add a short authoring note for
   future corpus updates covering source-label rules, allowed source kinds, and
   gold-key conventions. Created: #922.

   ```powershell
   kanban\kanban-md.exe create "Document EntityExtractor benchmark corpus authoring contract" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,docs,type:docs,phase-research" --parent 906 --depends-on 912
   ```
