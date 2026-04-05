# Thread CancelSignal from IngestPipeline to GraphEnricher Schedule Calls

> **Owning task:** #999 — Thread CancelSignal from IngestPipeline to GraphEnricher schedule calls
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #997 (archived) added `cancel: CancelSignal | None = None` to both `GraphEnricher.schedule_graph_enrichment()` and `schedule_inter_doc_enrichment()`. However, the sole production call site in `IngestPipeline._ingest_from_intake()` (ingest.py:288-289) was **not updated** to pass `cancel` through. The `cancel` parameter already exists on `_ingest_from_intake` and is used upstream for `_run_extract`, but stops short of the enricher calls.

**Question:** What is needed to thread `cancel` through to the enricher, and are there other call sites or patterns affected?

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| OwlBear `ingest.py` — `_ingest_from_intake` | Internal: `src/owlbear/memory/knowledge/ingest.py:247-300` | 1.0 | `cancel` param exists but is not forwarded to enricher calls at lines 288-289 |
| OwlBear `enrichment.py` — `GraphEnricher` | Internal: `src/owlbear/memory/knowledge/enrichment.py:65-120` | 1.0 | Both `schedule_*` methods accept `cancel` kwarg and check `cancel.is_set()` |
| OwlBear `test_enrichment_cancellation.py` | Internal: `tests/test_enrichment_cancellation.py` | .90 | Tests exist for enricher-level cancel no-ops; no test covers cancel threading from pipeline |
| #997 task (archived) | Internal: kanban task #997 | .95 | Confirms enricher-side cancel support is implemented and verified |
| #871 research doc | Internal: `docs/research/graphenricher-cancellation-draining.md` | .95 | Original recommendation: "IngestPipeline._ingest_from_intake passes its cancel through" |
| Python asyncio cooperative cancellation | `docs.python.org/3/library/asyncio-task.html` | .85 | Established pattern: check signal before scheduling new async work |

## 3. Analysis

### 3.1 Call-site audit

| Call site | File:Line | Passes `cancel`? | Fix needed? |
|-----------|-----------|-------------------|-------------|
| `_ingest_from_intake` → `schedule_graph_enrichment` | `ingest.py:288` | No | Yes — add `cancel=cancel` |
| `_ingest_from_intake` → `schedule_inter_doc_enrichment` | `ingest.py:289` | No | Yes — add `cancel=cancel` |
| `test_inter_doc_pipeline_integration` (mock) | `test_inter_doc_pipeline_integration.py:405` | N/A (assertion) | No |

These are the **only** production call sites. No other file calls `_enricher.schedule_*`.

### 3.2 Risk assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking existing callers that omit cancel | None | `cancel` is keyword-only with default `None`; no positional change |
| Enrichment silently skipped when cancel set | Intended behavior | Same as `_run_extract` cancelation upstream |
| Missing test for pipeline-to-enricher threading | Medium | New integration test needed |

### 3.3 Complexity

This is a **trivial two-line change** — adding `cancel=cancel` to two existing calls. The parameter already flows into `_ingest_from_intake` and the receiver already accepts it. No new imports, no signature changes, no architectural decisions.

## 4. Recommendation (.95 confidence)

Add `cancel=cancel` to both enricher calls in `_ingest_from_intake`. Add one integration test verifying that when `cancel.is_set()` is `True`, the enricher receives `cancel` and creates no background tasks.

This completes the cancellation chain: caller → `_ingest_from_intake(cancel=...)` → `_run_extract(cancel=...)` + `enricher.schedule_*(cancel=...)`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Thread CancelSignal to enricher in _ingest_from_intake" --priority nice-to-have --status ideation --tags "scope:core,type:build" --body "Source: #999 research (docs/research/ingestpipeline-cancel-threading-to-enricher.md).\n\nAC:\n1. _ingest_from_intake passes cancel=cancel to enricher.schedule_graph_enrichment (ingest.py:288).\n2. _ingest_from_intake passes cancel=cancel to enricher.schedule_inter_doc_enrichment (ingest.py:289).\n3. When cancel is set, enricher schedule calls create no background tasks.\n4. Callers that omit cancel continue to work unchanged.\n5. Integration test: ingest with cancel set verifies enricher receives the signal."
```
