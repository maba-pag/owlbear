# EntityExtractor Gleaning Prototype Research

> **Owning task:** #907 - Prototype feature-flagged EntityExtractor gleaning
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #907 asks for a default-off gleaning prototype inside `EntityExtractor` so
OwlBear can compare the current single-pass extractor against a second
"missed entities" pass without changing normal production behavior.

The design has to satisfy four constraints at once: keep today's single-pass
path as the default, preserve Pass 1 results when Pass 2 fails, make token and
cost deltas visible to the benchmark work, and merge duplicate entities without
depending on unstable UUID-based entity ids.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| Upstream benchmark research | `docs/research/entity-extractor-gleaning-benchmark.md` | .95 | Benchmark-first recommendation, prototype contract deltas, and dependency on #906 / #908 |
| EntityExtractor | `src/owlbear/memory/knowledge/extractor.py` | .95 | Current single-pass flow, exception contract, tracker/provider seam |
| Knowledge bootstrap | `src/owlbear/bootstrap/knowledge.py` | .90 | Sole production constructor call site for `EntityExtractor`; tracker/provider are not wired here today |
| OwlBear settings | `src/owlbear/config.py` | .80 | Existing pattern for default-off knowledge feature flags |
| Usage wiring tests | `tests/test_usage_wiring.py` | .80 | Existing assertions around `record_agent_usage()` and extractor usage tracking |
| Microsoft GraphRAG config docs | <https://microsoft.github.io/graphrag/config/yaml/> | .90 | `extract_graph.max_gleanings` as a tunable extraction knob and built-in metrics hooks |
| Microsoft GraphRAG dataflow docs | <https://microsoft.github.io/graphrag/index/default_dataflow/> | .90 | Merge semantics: entities with the same title and type are merged after extraction |
| Microsoft GraphRAG manual prompt tuning docs | <https://microsoft.github.io/graphrag/prompt_tuning/manual_prompt_tuning/> | .80 | Extraction prompt is an overridable seam, supporting a dedicated missed-entities prompt |
| EdgeQuake README | <https://github.com/raphaelmansuy/edgequake> | .85 | Optional glean stage, recall-improvement claim, and post-glean normalization step |

## 3. Analysis

### 3.1 Toggle Surface

| Option | Fits AC | Blast Radius | Benchmark Fit | Verdict |
|--------|---------|--------------|---------------|---------|
| Constructor option on `EntityExtractor` | High | Low | High | Best fit |
| New top-level OwlBear setting now | Medium | Medium | Medium | Defer |
| Benchmark-only wrapper outside extractor | Low | Low | Low | Reject |

- GraphRAG exposes gleaning as a workflow knob (`max_gleanings`) instead of a
  permanent default, and EdgeQuake documents gleaning as an optional pipeline
  step.
- OwlBear currently constructs `EntityExtractor` in exactly one production path,
  so a constructor-level option is the smallest reversible seam.
- OwlBear already uses default-off booleans for experimental knowledge behavior
  such as `inter_doc_graph_building`, but promoting gleaning to settings before
  #908 would widen surface area without benchmark evidence.

### 3.2 Two-Pass Execution Shape

| Shape | Failure Isolation | Code Churn | Usage Visibility | Verdict |
|-------|-------------------|------------|------------------|---------|
| Shared internal single-pass helper called twice | High | Medium | High | Recommend |
| Recursive call back into `extract()` | Medium | Low | Low | Avoid |
| Second pass handled only in benchmark code | Low | Medium | Medium | Reject |

- Today's `extract()` returns an empty `ExtractionResult()` on any exception, so
  Pass 2 must be isolated from Pass 1 rather than wrapped around the entire
  method.
- Prior art treats gleaning as an extra extraction cycle after the base pass,
  not as a separate benchmark-only abstraction.
- A shared helper keeps Pass 1 identical to current behavior and gives the
  implementation one place to record per-pass usage.

### 3.3 Merge and Edge Repair

| Strategy | Stable Dedup Key | Edge Safety | Coupling | Verdict |
|----------|------------------|-------------|----------|---------|
| In-memory canonical map keyed by `(name.casefold(), entity_type)` | High | High | Low | Best fit |
| Persist both passes and call `GraphStore.merge_entities()` | High | High | High | Too coupled |
| Concatenate outputs without merge | None | None | Low | Reject |

- GraphRAG merges entities with the same title and type after per-text-unit
  extraction, and EdgeQuake follows gleaning with a normalization step.
- OwlBear entity ids are UUID-derived, so the merge key must use stable fields.
- OwlBear's persisted graph merge already redirects edges to canonical ids;
  the extractor prototype should mirror that behavior in memory before returning
  an `ExtractionResult`.

### 3.4 Usage and Benchmark Visibility

| Option | Benchmark Ready | Schema Churn | Verdict |
|--------|-----------------|--------------|---------|
| One `UsageRecord` per pass with distinct `operation` labels | High | None | Recommend |
| One aggregated record for both passes | Low | None | Reject |
| Extend `UsageRecord` schema before prototype | Medium | High | Defer |

- OwlBear already stores tokens, request count, estimated cost, and operation in
  `UsageRecord`; two records are enough for #908 to compute deltas.
- `EntityExtractor` already accepts `tracker` and `provider`, and tests already
  cover the usage-recording seam.
- `_build_knowledge_infra()` still constructs `EntityExtractor(model=chat_model)`
  without tracker/provider, so normal ingest-path measurement is a separate
  integration concern and should not be folded into the core prototype.

## 4. Recommendation (.88 confidence)

Implement gleaning as a constructor-level default-off option on
`EntityExtractor`, run Pass 1 and Pass 2 through a shared internal single-pass
helper, record each pass separately, and merge results in memory on
`(name.casefold(), entity_type)` before returning.

Do not add a top-level OwlBear setting yet. The benchmark work in #906 and #908
needs a controlled prototype seam first; promoting gleaning to broader product
configuration only makes sense if the measured recall gain justifies the extra
cost and latency.

Architecturally, #907 is better treated as an umbrella for three smaller work
slices: execution/fallback, merge semantics, and usage visibility.

## 5. Follow-up Tasks

1. **#917 Add default-off two-pass flow to EntityExtractor**

Priority rationale: this is the smallest contract seam and unlocks the rest of
the prototype without widening product configuration yet.

Dependencies: #906.

One-line AC: add a constructor-level default-off gleaning option, keep current
single-pass behavior as the default, and preserve Pass 1 output when Pass 2
fails.

Created:

```powershell
kanban\kanban-md.exe create "Add default-off two-pass flow to EntityExtractor" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,type:build,phase-research" --parent 907 --depends-on 906
```

2. **#918 Add in-memory merge and edge repair helper for EntityExtractor gleaning**

Priority rationale: gleaning only produces usable benchmark data if duplicate
entities collapse onto stable keys and edges are remapped safely.

Dependencies: #906.

One-line AC: merge pass outputs by `(normalized name, entity_type)`, prefer the
higher-importance canonical entity, and rewrite edges to canonical ids before
returning the result.

Created:

```powershell
kanban\kanban-md.exe create "Add in-memory merge and edge repair helper for EntityExtractor gleaning" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,type:build,phase-research" --parent 907 --depends-on 906
```

3. **#919 Expose per-pass EntityExtractor usage records for gleaning benchmarks**

Priority rationale: #908 cannot justify or reject gleaning without separate pass
records for token and estimated-cost deltas.

Dependencies: #906.

One-line AC: when a tracker/provider are supplied, record Pass 1 and Pass 2
separately so benchmark runs can compare token and estimated-cost deltas.

Created:

```powershell
kanban\kanban-md.exe create "Expose per-pass EntityExtractor usage records for gleaning benchmarks" --priority nice-to-have --status ideation --tags "scope:core,knowledge,benchmark,type:build,phase-research" --parent 907 --depends-on 906
```
