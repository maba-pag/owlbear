# Frontier Serialization Contract Baseline

> **Owning change:** `frontier-serialization-contract` — issue #215
> **Date:** 2026-09-07
> **Question:** Why did the 2026-09-05 Delivery audit report strict frontier round-trip failures while the current runtime-file test command passes?

## 1. Context and Question

The Delivery audit reported a 35-failure Pydantic validation family across runtime, portfolio application, Delivery state, and checkpoint regression tests. Current execution of `serve/delivery/tests/test_delivery_runtime.py` passes. This note records the evidence needed to prevent the current green result from being mistaken for proof that the frontier contract was repaired.

## 2. Sources Studied

| Source | Evidence | Limit |
| --- | --- | --- |
| `.owlbear/research/delivery-system-audit-2026-09-05.md` | Reports 35 failures: runtime 8, portfolio application 13, Delivery state 13, checkpoint regression 1 | Historical observed result; this session did not reproduce the old failing checkout |
| Audit baseline `5ba3d49aeb91f7b3fd8ddc4a9efaebb07596e8c9` and current `uv.lock` | Both record Pydantic 2.13.5 | Dependency parity does not prove complete environment parity |
| Audit-baseline and current `serve/delivery/tests/test_delivery_runtime.py` diff | Multiple direct `DeliveryFrontier.model_validate_json(...)` calls now pass `strict=False`, including publication-history coverage | Establishes test-contract relaxation, not why each of the 35 failures occurred |
| Current source inventory | Direct typed frontier parsing remains in loader, `_portable_frontier()`, portfolio admission response, and nested `DeliveryStateSnapshot` reads | Source evidence, not implemented correction |
| Current focused execution | Runtime file: 62 passed; runtime + state + portfolio baseline: 313 passed | Current feasibility baseline; direct permissive test reads make it non-independent proof of canonical parser ownership |

## 3. Analysis

The locked Pydantic version did not change between the audit baseline and current checkout. The current runtime test file changed several strict-default frontier reads to `strict=False`, including the audit's representative publication-history assertion. Therefore the current 62-pass result is compatible with test-side acceptance of the permissive JSON mode and cannot independently establish one canonical parser boundary.

The audit's 35 failures were one family, not 35 separately diagnosed defects. Current source still contains consumer-selected parsing in typed Delivery paths. The maintained repair target is consequently parser ownership and proof locality: typed consumers should cross `parse_delivery_frontier()` or an owning frontier-bearing-document wrapper, while model and runtime-relative rejection tests remain at their actual owners.

`parse_delivery_frontier()` owns JSON object shape, frontier schema version, Pydantic model validation, and canonical bytes. `DeliveryRuntime._validate_frontier()` separately owns contract-relative bindings and lifecycle consistency. Tests and design authority must not attribute those runtime-relative checks to the parser.

## 4. Recommendation, Confidence, And Limits

**Recommendation:** Treat the current green suite as a feasibility baseline, not evidence that issue #215 is already resolved. Restore tests to the canonical parser boundary, centralize typed production readers, preserve direct model/runtime rejection tests at their owning layers, and rerun the four affected suites.

**Confidence:** High that test-side `strict=False` changes explain why the current runtime-file result is not independent proof. Medium on the complete historical cause of all 35 failures because this session did not recreate the audit checkout and environment.

**Limits:** This note does not claim a Pydantic regression, production outage, persisted-data corruption, or complete environment equivalence. The shallow `serve/tools` target-branch blocker scan is intentionally outside typed authority parsing.
