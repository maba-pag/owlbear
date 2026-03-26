# EntityExtractor Gleaning Benchmark Plan

> **Owning task:** #891 - Research: EntityExtractor gleaning prototype and recall benchmark
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #734 ended with a benchmark-first recommendation for `EntityExtractor.extract()`:
measure on OwlBear's corpus before integrating gleaning into the default path.
The open question is not whether gleaning helps generic GraphRAG pipelines; it is
whether a second extraction pass improves recall enough on OwlBear's code-heavy
corpus to justify extra Copilot latency and cost.

Important correction: current OwlBear contracts do not already provide safe
two-pass degradation. `EntityExtractor.extract()` returns `ExtractionResult()` on
any exception, and `record_agent_usage()` is called once per successful
`extract()` invocation. A gleaning prototype must add pass-2 fallback and
per-pass usage visibility explicitly.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | .90 | Optional glean step, 15-25% recall claim, benchmark-first precedent |
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | .90 | `extract_graph.max_gleanings` and `extract_claims.max_gleanings` as tunable multi-pass knobs |
| Microsoft GraphRAG dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | .85 | TextUnit provenance, per-chunk extraction, merge-by-title/type semantics |
| Microsoft GraphRAG manual prompt tuning | <https://microsoft.github.io/graphrag/prompt_tuning/manual_prompt_tuning/> | .75 | Extraction prompt is a separable seam, supporting a default-off prototype |
| scikit-learn `recall_score` | <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html> | .80 | Recall definition and micro/macro options for gold-vs-pred evaluation |
| spaCy `Scorer` | <https://spacy.io/api/scorer> | .70 | Gold annotation scoring conventions and per-type PRF framing |
| EntityExtractor | `src/owlbear/memory/knowledge/extractor.py` | .95 | Single-pass flow, failure contract, usage-recording seam |
| UsageTracker | `src/owlbear/memory/usage.py` | .90 | Token, estimated-cost, and per-operation record fields |
| Existing benchmark helpers | `tests/benchmarks/harness.py`; `tests/benchmarks/evaluate.py` | .85 | Current harness is retrieval-oriented (`Qrels`, `Run`, latency tables), not extraction recall |
| Entity model | `src/owlbear/memory/knowledge/models.py` | .80 | `Entity.id` is uuid4-based, so benchmark keys must use stable fields |

## 3. Analysis

### 3.1 Strategy Options

| Option | Decision Quality | Code Risk | Reusable Output | Verdict |
|--------|------------------|-----------|-----------------|---------|
| Implement gleaning directly | Low | Medium | Low | Reject |
| Benchmark-first prototype behind default-off flag | High | Medium | High | Best fit |
| Keep single-pass and do nothing | Medium | Low | None | Too little evidence |

Prior art treats gleaning as a tuning knob, not a default assumption. OwlBear
has no benchmark data for code-oriented extraction today, so direct integration
would be guesswork.

### 3.2 Benchmark Design

| Corpus Design | Fidelity | Maintenance | Repeatability | Verdict |
|---------------|----------|-------------|---------------|---------|
| Synthetic snippets only | Low | Low | High | Reject |
| Curated OwlBear sample with gold annotations | High | Medium | High | Recommend |
| Full-repo sweep | Highest | High | Low | Too expensive for iteration |

- Sample 20-40 chunks across `src/owlbear/`, `src/bearclaw/`, and selected
  Markdown docs so the benchmark covers file, function, class, pattern,
  decision, and concept entities.
- Score entities by canonical key `(normalized_name, entity_type)`, not
  `Entity.id`, because ids are random UUIDs and GraphRAG-style merging is title
  or type based.
- Primary metric: micro recall. Secondary metrics: per-type recall and predicted
  entity count.
- Keep edge scoring out of scope for this experiment. Task #891 is about whether
  entity recall improves enough to justify cost.
- Do not retrofit the existing `ranx` wrappers. They model query-to-document
  relevance, not entity-set extraction, so a small custom scorer in
  `tests/benchmarks/` is the cleaner seam.

### 3.3 Prototype Contract Deltas

| Concern | Current OwlBear Behavior | Prototype Requirement |
|---------|--------------------------|-----------------------|
| Failure fallback | Any exception returns empty result | Catch pass 2 separately and return pass 1 if pass 2 fails |
| Usage accounting | One `record_agent_usage()` call per successful `extract()` | Record each LLM pass so token and cost deltas are observable |
| Entity merge key | `Entity.id` is unstable | Dedup by `(name, entity_type)` and keep the higher-importance entity |
| Edge integrity | Edges point at per-pass entity ids | Re-map edges to merged entity ids before returning |
| Rollout safety | No flag | Default-off feature flag or constructor option |

The cost delta is directionally close to 2x because gleaning adds a second model
request, but the exact multiplier still needs measurement because the second
prompt is smaller than the original chunk prompt.

## 4. Recommendation (.86 confidence)

Use a three-step benchmark-first path: build a curated code-corpus recall
harness, add a default-off gleaning prototype that explicitly preserves pass-1
output on pass-2 failure and records both calls, then run a go or no-go
evaluation. Integrate only if micro recall improves by more than 10 percent with
acceptable latency and cost on OwlBear data.

Reasoning: prior art shows gleaning as an optional quality knob, but OwlBear's
current contracts and benchmark tooling do not yet support a trustworthy product
decision. The benchmark harness is still useful even if gleaning is rejected.

## 5. Follow-up Tasks

1. **Build EntityExtractor code-corpus recall benchmark harness** - Priority:
   nice-to-have. Dependencies: none. One-line AC: curate OwlBear source and docs
   samples plus gold entity annotations and report micro plus per-type recall
   for the current extractor. Created: #906.

   ```powershell
   kanban\kanban-md.exe create "Build EntityExtractor code-corpus recall benchmark harness" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,test,type:test,phase-research" --parent 891
   ```

2. **Prototype feature-flagged EntityExtractor gleaning** - Priority:
   nice-to-have. Dependencies: #906. One-line AC: add a default-off two-pass
   extractor that falls back to pass 1, records both passes, and merges
   duplicate entities safely. Created: #907.

   ```powershell
   kanban\kanban-md.exe create "Prototype feature-flagged EntityExtractor gleaning" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,type:build,phase-research" --parent 891
   ```

3. **Evaluate EntityExtractor gleaning recall and cost delta** - Priority:
   nice-to-have. Dependencies: #906, #907. One-line AC: run baseline versus
   gleaning on the same corpus, report recall, token, cost, and runtime deltas,
   and create integration work only if recall gain exceeds 10 percent. Created:
   #908.

   ```powershell
   kanban\kanban-md.exe create "Evaluate EntityExtractor gleaning recall and cost delta" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,docs,type:docs,phase-research" --parent 891
   ```
