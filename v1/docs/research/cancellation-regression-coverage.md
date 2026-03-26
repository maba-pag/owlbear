# Cooperative Cancellation Regression Coverage — Gap Analysis

> **Owning task:** #872 — Add cooperative cancellation regression coverage for knowledge pipelines
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Tasks #870 (CancelSignal/LinkedCancelSignal), #871 (GraphEnricher drain/shutdown), #880 (pipeline cancel seams), and #1006 (enricher cancel threading) implemented cooperative cancellation across the knowledge pipelines. Task #872 asks: **what regression tests are needed to prevent these cancellation contracts from breaking silently?**

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | .95 | `CancelledError` propagation semantics; `gather(return_exceptions=True)` must re-raise if extraction is cancelled |
| .NET CancellationToken cooperative pattern | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .90 | Linked tokens compose parent+child cancel; regression tests should verify linked signal propagation across call chain boundaries |
| OwlBear existing test suite (8 files) | Internal codebase | .95 | Mapped per-module coverage; identified cross-module gaps |
| OwlBear cooperative-cancellation research | `docs/research/cooperative-cancellation.md` | .90 | Original design; lists every cancel seam to test |
| OwlBear graphenricher-cancellation research | `docs/research/graphenricher-cancellation-draining.md` | .85 | Enricher shutdown/drain design; bootstrap cleanup wiring |

## 3. Analysis

### 3.1 Existing Coverage Map

| Area | Test file | Task | Status |
|------|-----------|------|--------|
| CancelSignal/LinkedCancelSignal primitives | test_cancellation.py | #870 | GREEN |
| RefreshOrchestrator.refresh\_all + \_ingest\_items | test_refresh_orchestrator.py | #880 | GREEN |
| IngestPipeline.\_run\_extract chunk boundary | test_knowledge_ingest.py | #880 | GREEN |
| BookmarkPipeline.process stage boundaries | test_bookmark_pipeline.py | #880 | GREEN |
| crawl_and_ingest page boundary | test_crawl_integration.py | #880 | GREEN |
| GraphEnricher shutdown/drain/cancel param | test_enrichment_cancellation.py | #1000 | GREEN |
| GraphEnricher drain sets \_shutdown | test\_871\_graphenricher\_drain\_noop.py | #871 | GREEN |
| IngestPipeline to enricher cancel threading | test\_1006\_ingest\_cancel\_threading.py | #1006 | RED (pending) |
| Bootstrap LinkedCancelSignal -> RetrospectiveHook | test_bootstrap.py | #870 | GREEN |
| RetrospectiveHook live-linked cancel | test_retrospective_hook.py | #870 | GREEN |

### 3.2 Gap Analysis (mapped to #872 AC)

| Gap | AC | Risk | Description |
|-----|----|------|-------------|
| G1: refresh\_all pre-set cancel | AC1 | Medium | No test with cancel already set before refresh\_all starts — should process zero sources |
| G2: \_ingest\_from\_intake gather + partial cancel | AC2 | High | asyncio.gather with return\_exceptions=True and explicit CancelledError re-raise is subtle; no test isolates gather interaction when cancel fires mid-extraction |
| G3: BookmarkPipeline.\_ingest\_text cancel passthrough | AC2 | Medium | No test verifies cancel is threaded from BookmarkPipeline to IngestPipeline.ingest\_text via \_ingest\_text helper |
| G4: Linked cancel signal across pipeline chain | AC3 | High | No test wires `LinkedCancelSignal(operation_event, shutdown_event)` through a pipeline call (refresh or bookmark) and verifies that setting `shutdown_event` mid-operation stops the pipeline |
| G5: Partial document state on mid-extraction cancel | AC4 | Medium | No test verifies that document\_status records remain consistent when cancel fires during \_ingest\_from\_intake (between chunking and extraction completion) |
| G6: Enricher has no orphaned tasks after pipeline cancel | AC4 | High | No test combines: ingest with cancel, cancel fires mid-extraction, enricher.shutdown empties task set, verify no orphaned tasks |

### 3.3 Risk Prioritization

| Priority | Gaps | Rationale |
|----------|------|-----------|
| Critical | G2, G4, G6 | Cross-module seams are where regressions hide; the gather interaction is the most fragile code pattern |
| Important | G1, G3, G5 | Defense-in-depth for boundary conditions; lower regression probability but easy to write |

## 4. Recommendation (.85 confidence)

Create a single regression test file `tests/test_cancellation_regression.py` with 4 test classes covering all 6 gaps. Tests should be integration-style (wiring real or thin-mock pipeline stages) rather than pure unit tests, since the gaps are at call-chain boundaries.

**Testing strategy:**

- Use `asyncio.Event` as the CancelSignal (structurally compatible per CancelSignal protocol)
- Use `LinkedCancelSignal` for AC3 daemon-composition test
- Mock LLM/embedding calls but use real pipeline wiring where possible
- Verify partial result counts, document store state, and enricher task set emptiness

**File structure:**

- `TestRefreshAllPresetCancel` — G1 (AC1)
- `TestIngestGatherCancelInteraction` — G2, G5 (AC2, AC4)
- `TestLinkedCancelSignalPipelineComposition` — G4, G3 (AC3, AC2)
- `TestCancelToEnricherLifecycleIntegration` — G6 (AC4)

Max ~200 lines. KISS: no over-mocking, no test helpers that obscure intent.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Write cancellation regression tests for knowledge pipelines" --priority nice-to-have --status ideation --tags "scope:core,type:test" --body "Source: #872 research (docs/research/cancellation-regression-coverage.md).\nDepends on: #1006 (cancel threading to enricher).\n\nAC:\n1. Test refresh_all with cancel pre-set returns zero results (G1).\n2. Test _ingest_from_intake gather interaction when cancel fires mid-extraction: partial extraction result preserved, CancelledError from _run_extract re-raised through gather, document status consistent (G2, G5).\n3. Test LinkedCancelSignal(op_event, shutdown_event) through a pipeline call: setting shutdown_event mid-operation stops processing; verify BookmarkPipeline._ingest_text threads cancel to IngestPipeline.ingest_text (G3, G4).\n4. Test cancel mid-ingest followed by enricher.shutdown: enricher._background_tasks is empty, no orphaned tasks remain (G6).\n5. All tests in a single file tests/test_cancellation_regression.py, max ~200 lines." --depends-on 1006
```
