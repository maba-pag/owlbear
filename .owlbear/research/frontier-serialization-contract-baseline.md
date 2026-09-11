# Frontier Serialization Contract Baseline

> **Owning task:** `frontier-serialization-contract` / `TASK-001`
> **Date:** 2026-09-11
> **Question:** Which typed Delivery readers must cross the canonical frontier JSON boundary, and what evidence distinguishes the historical audit from current proof?

## 1. Context and Question

The Delivery audit reported a 35-failure frontier validation family across runtime, portfolio, Delivery state, and checkpoint regression paths. The source head for this task still allowed consumer-selected JSON parsing in the loader, portable-state projection, portfolio projection, and nested snapshot reads. This note records the source and test baseline for the parser-ownership repair.

## 2. Sources Studied

| Source | Evidence | Limit |
| --- | --- | --- |
| `.owlbear/research/delivery-system-audit-2026-09-05.md` | Historical report of 35 failures: runtime 8, portfolio 13, Delivery state 13, checkpoint 1 | Reported historical result; not reproduced here |
| Audit baseline `5ba3d49aeb91f7b3fd8ddc4a9efaebb07596e8c9` and current `uv.lock` | Pydantic 2.13.5 appears in both dependency records | Lock parity does not establish complete environment parity |
| `serve/delivery/src/owlbear_delivery/delivery_runtime.py` | `parse_delivery_frontier()` checks JSON object shape and schema 17, validates in JSON mode, and returns canonical bytes; `_validate_frontier()` owns contract-relative checks | Source ownership evidence, not standalone runtime proof |
| `serve/delivery/src/owlbear_delivery/delivery_state.py` | Snapshot readers and `_portable_frontier()` are routed through the canonical parser or owning snapshot wrapper; snapshot identity and quarantine remain envelope-owned | Focused tests cover the maintained boundaries; unrelated models are out of scope |
| `serve/delivery/tests/test_delivery_runtime.py`, `test_delivery_state.py`, `test_portfolio_application.py`, `test_checkpoint_publication_regressions.py` | Candidate proof boundary for parser, recovery, portfolio, and checkpoint behavior | Exact outcomes are recorded by the Builder's candidate observations |

## 3. Analysis

The canonical frontier parser is the single standalone JSON boundary. Its `strict=False` use is confined to JSON-to-model conversion, while the model remains frozen, extra-forbid, schema-bound, and validator-backed. `DeliveryRuntime._validate_frontier()` remains separate so parsing does not acquire admitted-contract authority.

Frontier-bearing snapshots require an owning wrapper: the outer payload must be an object with an object `frontier`; that embedded value is parsed and canonicalized before snapshot-envelope validation. Equivalent encodings therefore preserve semantic state and `snapshot_id`, while absent or non-object frontiers remain in the existing inventory quarantine path. The loader validates through the parser but retains original bytes for exact remote drift comparison and maps `TypeError` through `_bootstrap_failure`.

The current task baseline is historical context rather than proof that all 35 audit failures were reproduced. Candidate proof must be run against the exact committed candidate and must include the two assembled recovery scenarios.

## 4. Recommendation, Confidence, And Limits

**Recommendation:** Keep typed Delivery readers on `parse_delivery_frontier()` or the owning snapshot wrapper, preserve runtime-relative validation and raw-byte comparison, and use the four maintained test files plus source inventory as the proof boundary.

**Confidence:** High for parser ownership and snapshot-envelope routing because the owning source paths are direct and testable. Medium for the historical failure-family explanation because the audit checkout was not recreated.

**Limits:** This note does not claim a Pydantic regression, production outage, persisted-data corruption, or complete historical reproduction. The shallow `serve/tools/src/owlbear_tools/delivery_config.py` blocker scan remains intentionally outside typed authority parsing.