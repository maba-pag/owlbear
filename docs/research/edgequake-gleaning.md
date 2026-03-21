# EdgeQuake Gleaning — Evaluation Against Current LLM Extraction Paths

> **Owning task:** #734 — Research: Evaluate EdgeQuake gleaning for current LLM extraction paths
> **Date:** 2026-03-21
> **Status:** Complete

## 1. Context and Question

Task #597 filed EdgeQuake's gleaning pattern as a future bookmark with the note
"not applicable today — no LLM extraction beyond `InterDocGraphBuilder`." Since
then, OwlBear has gained two additional LLM extraction seams:

- `EntityExtractor.extract()` — per-chunk structured-output extraction
- `IngestPipeline._run_extract()` — coordination loop over chunks

This task re-evaluates gleaning against all three current paths under the
premise that the precondition for applicability has now been met.

**What is gleaning?** EdgeQuake's gleaning is an iterative multi-pass LLM
extraction strategy. After a first extraction pass the model is re-prompted
with both the original text and the already-found results: "Given these
entities already found, what additional entities are present that were
missed?" EdgeQuake reports +18-25% entity recall improvement over a
single-pass baseline.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|-----------|-----------|------|
| Original EdgeQuake research | docs/research/edgequake.md | .90 | S3.2 gleaning analysis, +18-25% recall figure, applicability rating |
| EntityExtractor | src/owlbear/memory/knowledge/extractor.py | .95 | Single-pass PydanticAI Agent, ExtractionResult schema, UsageTracker wiring |
| IngestPipeline | src/owlbear/memory/knowledge/ingest.py | .90 | _run_extract() loop, cooperative cancellation via asyncio.Event, chunk provenance |
| InterDocGraphBuilder | src/owlbear/memory/knowledge/inter_doc_graph_builder.py | .85 | Batched LLM inference, cosine_threshold=0.70, top_k=10, _BATCH_SIZE=40 |
| Entity / Edge models | src/owlbear/memory/knowledge/models.py | .80 | Frozen Pydantic models, id = uuid4().hex, name-based identity |

## 3. Current-State Catalog

### 3.1 EntityExtractor.extract() — single-pass

```text
Flow: text → EXTRACTION_PROMPT system prompt → PydanticAI Agent.run(prompt)
                                                 → ExtractionResult
```

- **Pass type:** Single-pass — one LLM call per chunk.
- **Schema:** `ExtractionResult(entities: list[Entity], edges: list[Edge])`. Frozen.
- **Failure:** Returns empty `ExtractionResult()` on exception; no retry logic.
- **Cost tracking:** Optional `UsageTracker` wired at construction time.
  `record_agent_usage()` is called for each successful run.
- **Cancellation:** None. The call is a single awaitable; no internal checkpoints.
- **Provenance:** Chunk metadata injected into the prompt as context prefix.

### 3.2 IngestPipeline._run_extract() — sequential per-chunk loop

```text
Flow: chunks[] → for chunk in chunks:
                     if cancel.is_set(): break
                     await extractor.extract(chunk.text, chunk.metadata)
                 → list[ExtractionResult]
```

- **Pass type:** Sequential, single pass per chunk. Multiple chunks ≠ gleaning.
- **Cancellation:** Cooperative via `asyncio.Event`. Checks before each chunk.
- **Error model:** Exceptions bubble up as `BaseException` via `asyncio.gather`
  into `_process_results`, which degrades gracefully (embeddings OR entities can
  fail independently).
- **Provenance:** Each `ExtractionResult` is later stored with `document_id` and
  `chunk_id` linkage in `_store.store_extractions()`.

This is a **coordination layer**, not an extraction algorithm. The extraction
logic lives entirely in `EntityExtractor.extract()`.

### 3.3 InterDocGraphBuilder.build() — batched LLM inference

```text
Flow: entities[] → _find_candidate_pairs (vector similarity, cosine ≥ 0.70)
                 → pairs → _batch_pairs (_BATCH_SIZE=40)
                 → for batch in batches: agent.run(prompt) → ExtractionResult.edges
```

- **Pass type:** Batched. One LLM call per 40-pair batch. Single pass through the
  candidate set.
- **Output restriction:** Entities list is expected empty — only edges are returned.
- **Pre-filter:** Vector similarity with `cosine_threshold=0.70` and `top_k=10`
  excludes structurally ineligible pairs before any LLM call is made.
- **Error model:** Per-batch exception handling; failures continue to next batch.
- **No cost tracking:** `self._tracker` is not present on `InterDocGraphBuilder`.

## 4. Gleaning Applicability Evaluation

### 4.1 EntityExtractor.extract()

**Applicability: Medium (.55)** · Confidence .80

**How gleaning would work:**

```python
Pass 1: await self._agent.run(text)          → ExtractionResult (initial)
Pass 2: await self._agent.run(glean_prompt)  → ExtractionResult (incremental)
Merge:  dedupe entities by name, merge edges by (source_id, target_id, relation)
```

**Schema compatibility (ExtractionResult):** ✓ Same frozen Pydantic model used
for both passes. Merging requires only `{e.name: e for e in entities}` dedup with
importance-weighted selection for conflicts. No schema changes needed.

**Per-chunk storage/provenance:** ✓ Both passes produce results from the same
chunk. The merged result is stored once with the existing `document_id`/`chunk_id`
linkage. No provenance changes required.

**Partial-failure behavior:** The second gleaning pass may fail while the first
succeeds. The existing exception swallowing (`return ExtractionResult()` on any
failure) makes this safe: if Pass 2 raises, the caller silently returns Pass 1's
result. This degrades gracefully by design.

**Cancellation:** ✗ `extract()` has no internal cancellation. Adding a gleaning
pass adds a second LLM call, doubling the non-interruptible window per chunk.
The outer `_run_extract()` loop checks cancellation between chunks, not within a
single `extract()` call. This worsens responsiveness for long chunks but does not
break correctness.

**Usage/cost tracking:** ✓ `record_agent_usage()` is called for each `Agent.run()`
result. Both Pass 1 and Pass 2 are tracked independently. Total cost per chunk
doubles (minus the "what did I miss?" prompt, which is short). The `UsageTracker`
correctly accumulates both.

**Open question — recall on code documents:** The +18-25% recall figure is from
EdgeQuake's generic document benchmark. OwlBear's extraction targets code-oriented
text (Python source files, markdown docs). Code entities have stable names and
predictable structure; a well-prompted single pass may already achieve high recall.
If Pass 1 already captures 95%+ of entities in code files, the improvement is
marginal at 2x cost. Measurement required before committing.

### 4.2 IngestPipeline._run_extract()

#### Applicability: N/A — wrong layer

Gleaning is an extraction-algorithm concern, not a coordination concern.
`_run_extract()` is a loop that calls `EntityExtractor.extract()` per chunk.
Applying gleaning at this layer would mean running the entire chunk list twice,
which is structurally equivalent to calling `extract()` twice per chunk from the
extractor's perspective — but with worse cohesion. The correct seam is inside
`EntityExtractor.extract()` itself (§4.1). This codepath requires no changes
regardless of what is decided for the extractor.

**Verdict: Keep single-pass. Gleaning does not apply at this coordination layer.**

### 4.3 InterDocGraphBuilder.build()

**Applicability: Low (.20)** · Confidence .85

Gleaning targets recall of **entities within text**. `InterDocGraphBuilder` does
not extract entities from text — it infers edges between already-extracted entity
pairs across document boundaries. The semantic unit is different.

An "edge gleaning" pass would ask: "Given these pairs and the edges inferred so
far, what additional edges did I miss?" Three structural problems make this
ineffective:

1. **Candidates are pre-filtered by cosine threshold.** Pairs below 0.70 cosine
   similarity are excluded before the LLM is invoked. A second gleaning prompt
   cannot recover structurally excluded pairs — the model would need the excluded
   pairs as input, which defeats the purpose of the pre-filter.
2. **The model already sees all candidate pairs per batch.** The INTER_DOC_PROMPT
   says "only propose relationships that are strongly implied … when in doubt,
   omit." A re-prompt for "what did I miss?" on the same batch would likely
   hallucinate low-confidence edges that the original prompt deliberately omitted.
3. **The right levers are threshold and batch size.** To improve recall here,
   lower `cosine_threshold` (e.g. 0.60) or increase `top_k`. These are
   tunable without adding LLM calls.

**Verdict: Keep single-pass batched. Gleaning is the wrong tool here.**

## 5. Summary Verdict Table

| Codepath | Pass Type | Gleaning Applicable | Verdict |
|----------|-----------|---------------------|---------|
| `EntityExtractor.extract()` | Single-pass | Medium (.55) | Create prototype task — measure recall delta on code documents before committing |
| `IngestPipeline._run_extract()` | Sequential loop | N/A | Keep single-pass — wrong layer; gleaning belongs in the extractor |
| `InterDocGraphBuilder.build()` | Batched inference | Low (.20) | Keep single-pass — tuning thresholds and batch size is the correct lever |

## 6. Recommendation

**For `EntityExtractor.extract()`:** Do not implement gleaning speculatively. The
+18-25% recall improvement is measured on generic document benchmarks. OwlBear's
code-oriented corpus may already achieve high single-pass recall, making the 2x
LLM cost unjustified. The path forward is:

1. Build a benchmark harness that measures entity recall on a representative set
   of OwlBear source files and documentation.
2. Establish a single-pass recall baseline.
3. Implement gleaning in a feature-flagged prototype.
4. Measure the delta.
5. Only integrate into the main pipeline if delta > 10% at reasonable cost.

**For `IngestPipeline._run_extract()` and `InterDocGraphBuilder.build()`:** No
action needed. The gleaning pattern does not apply, and the existing designs are
appropriate for their responsibilities.

## 7. Follow-up Tasks

One task is warranted (evaluation harness + prototype). Implementation tasks
for `_run_extract()` and `InterDocGraphBuilder` are explicitly not created.
