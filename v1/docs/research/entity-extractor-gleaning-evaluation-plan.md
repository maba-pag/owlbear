# EntityExtractor Gleaning Evaluation Plan

> **Owning task:** #908 - Evaluate EntityExtractor gleaning recall and cost delta
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #891 already established the product question: keep gleaning benchmark-first
and default-off until OwlBear has code-corpus evidence. Tasks #906 and #907 cover
the missing benchmark harness and the feature-flagged gleaning prototype. Task #908
needs the execution plan that turns those dependencies into a repeatable go or
no-go decision instead of a one-off experiment.

Current constraint: the final comparison cannot run yet because #906 and #907 are
still upstream dependencies. The useful research outcome here is the evaluation
shape, metrics, reporting format, and rollout gate that the later implementation
must follow.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | .90 | Optional glean step, quality claim, and benchmark-driven rollout precedent |
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | .90 | `max_gleanings` as a configurable extraction knob instead of default behavior |
| scikit-learn `recall_score` docs | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | .90 | Definition of micro recall and per-label recall views |
| spaCy `Scorer` docs | <https://spacy.io/api/scorer> | .80 | Per-type PRF reporting conventions for extraction evaluation |
| PydanticAI agents docs | <https://ai.pydantic.dev/agents/> | .80 | Run-result usage access for token and request accounting |
| Python `time` docs | <https://docs.python.org/3/library/time.html> | .75 | `time.perf_counter()` as a monotonic high-resolution elapsed-time clock |
| Existing benchmark helpers | `tests/benchmarks/evaluate.py`; `tests/benchmarks/harness.py` | .95 | Existing latency-summary and benchmark-doc shape in OwlBear |
| Benchmark markers | `pyproject.toml` | .90 | `benchmark` and `api` markers already separate opt-in live runs from default tests |
| EntityExtractor + usage wiring | `src/owlbear/memory/knowledge/extractor.py`; `src/owlbear/memory/usage.py` | .95 | Existing seams for per-run usage, cost enrichment, and extractor invocation |
| Prior gleaning benchmark research | `docs/research/entity-extractor-gleaning-benchmark.md` | .95 | Stable entity keys, >10% recall gate, and dependency split across #906 and #907 |

## 3. Analysis

### 3.1 Evaluation Shape

| Option | Repeatable | Default-test safety | Decision quality | Verdict |
|--------|------------|---------------------|------------------|---------|
| Ad hoc scratch script | Low | High | Low | Reject |
| Reusable runner in `tests/benchmarks/` | High | High with opt-in markers | High | Best fit |
| Live benchmark inside normal unit tests | Medium | Low | Medium | Reject |

OwlBear already keeps benchmark-specific helpers under `tests/benchmarks/`, and
`pyproject.toml` already reserves `benchmark` and `api` markers for opt-in runs.
The clean fit is a reusable runner that can be invoked deliberately, not a one-off
script and not a default-path unit test.

### 3.2 Metrics That Match the Task

| Metric | Why it belongs | Source pairing |
|--------|----------------|----------------|
| Micro recall | Primary gate from the task and the right global tp/fn view for "did gleaning find more gold entities?" | scikit-learn + `docs/research/entity-extractor-gleaning-benchmark.md` |
| Per-type recall | Detects whether gains are concentrated in one entity class while another regresses | spaCy + task AC |
| Token, request, and estimated-cost totals | Gleaning adds extra model passes, so cost must be measured from usage records instead of guessed | PydanticAI + `src/owlbear/memory/usage.py` |
| Runtime delta | Rollout needs wall-clock impact, not CPU-only timing | Python `time.perf_counter()` + `tests/benchmarks/evaluate.py` |

Stable scoring key remains `(normalized_name, entity_type)`, not `Entity.id`,
because entity IDs are random UUIDs and therefore not comparable across runs.

### 3.3 Architecture Fit

| Concern | Recommended seam | Why |
|---------|------------------|-----|
| Corpus and gold labels | #906 harness in `tests/benchmarks/` | Keeps the same curated samples and scorer for both variants |
| Baseline vs gleaning toggle | #907 feature flag or constructor option | Changes only one variable between runs |
| Cost capture | Dedicated `UsageTracker` path per benchmark variant | Reuses existing enrichment and aggregation logic |
| Timing | `time.perf_counter()` around each full corpus pass | High-resolution monotonic elapsed-time measurement |
| Results artifact | `docs/research/entity-extractor-gleaning-evaluation-results.md` | Matches existing benchmark write-up patterns |

The comparison should run both variants against the exact same corpus, scorer,
and model settings. Changing prompts, corpus samples, or scoring rules between
variants would make the recall delta uninterpretable.

### 3.4 Decision Gate

| Outcome | Decision | Follow-up |
|---------|----------|-----------|
| Micro recall gain `> 10%` and no severe per-type collapse | Create integration follow-up | Keep gleaning default-off initially and document rollout guidance |
| Micro recall gain `<= 10%` | Keep single-pass as the default | Publish rejection rationale in the results doc |
| Recall gain clears the gate but cost or runtime is materially worse than expected | Keep gleaning experimental | Create optimization or limited-rollout follow-up instead of flipping behavior |

GraphRAG and EdgeQuake both treat gleaning as optional tuning, not mandatory
default behavior. OwlBear should follow the same posture even if the benchmark is
positive: measured value first, rollout second.

## 4. Recommendation (.89 confidence)

Split #908 into two downstream implementation tasks: first, a reusable benchmark
runner that compares baseline and gleaning on the same corpus with recall, cost,
and runtime reporting; second, a results document that publishes the measured
delta and only creates rollout work if the micro recall gain exceeds 10 percent.

This keeps the final decision auditable, rerunnable after prompt or model changes,
and aligned with OwlBear's existing benchmark layout. Even on a positive result,
the first integration step should preserve default-off behavior and add rollout
guidance instead of immediately changing production defaults.

## 5. Follow-up Tasks

1. **Build EntityExtractor baseline-vs-gleaning benchmark runner** - Priority:
   nice-to-have. Dependencies: #906, #907. One-line AC: add an opt-in benchmark
   runner that executes both variants on the same gold corpus and reports micro
   recall, per-type recall, token or cost totals, and runtime deltas. Created:
   #915.

   ```powershell
   kanban\kanban-md.exe create "Build EntityExtractor baseline-vs-gleaning benchmark runner" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,test,type:test,phase-research" --parent 908 --depends-on 906,907
   ```

2. **Publish EntityExtractor gleaning results and rollout recommendation** -
   Priority: nice-to-have. Dependencies: follow-up task 1. One-line AC: run the
   benchmark runner, publish a side-by-side results doc, and create integration
   rollout work only if the measured micro recall gain exceeds 10 percent.
   Created: #916.

   ```powershell
   kanban\kanban-md.exe create "Publish EntityExtractor gleaning results and rollout recommendation" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,docs,type:docs,phase-research" --parent 908 --depends-on 915
   ```
