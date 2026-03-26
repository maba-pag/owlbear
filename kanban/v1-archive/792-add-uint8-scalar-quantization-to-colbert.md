---
id: 792
title: Add uint8 scalar quantization to ColBERT multivector config
status: archived
priority: nice-to-have
created: 2026-03-13T23:48:12.9147942+01:00
updated: 2026-03-22T18:59:28.218326+01:00
started: 2026-03-16T05:08:08.4950768+01:00
completed: 2026-03-16T05:08:08.4950768+01:00
tags:
    - phase-10
    - knowledge-graph
    - embedding
depends_on:
    - 793
class: standard
---

Add ScalarQuantization(INT8, quantile=0.99, always_ram=True) to ColBERT VectorParams in QdrantVectorStore._ensure_collection(). See docs/research/colbert-scalar-quantization.md.

## AC
- [ ] _ensure_collection() adds quantization_config=qmodels.ScalarQuantization(scalar=qmodels.ScalarQuantizationConfig(type=qmodels.ScalarType.INT8, quantile=0.99, always_ram=True)) to the colbert VectorParams
- [ ] Dense VectorParams remains unchanged (no quantization_config)
- [ ] All existing test_qdrant_vector_store.py tests still pass
- [ ] New test (from #793) passes: collection info confirms ScalarQuantization(INT8) on colbert vector and None on dense vector
- [ ] Migration of existing unquantized collections is out of scope
- [ ] ruff clean

## Deferred
Defer until corpus approaches 5K+ chunks. At current scale, YAGNI.

[[2026-03-14]] Sat 02:08
## Architecture Review
**Verdict:** APPROVED (blocked per YAGNI)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| quantization_config on colbert VectorParams | Precise: exact qmodels call specified | Keep |
| Dense VectorParams unchanged | Clear negative assertion | Keep |
| Existing tests pass | Standard regression check | Keep |
| New test from #793 confirms config | Verifiable via get_collection() API | Keep |
| Migration out of scope | Correct: _ensure_collection skips existing collections | Keep |
| ruff clean | Standard | Keep |

### Architecture Notes
- Single-param addition to _ensure_collection() ColBERT VectorParams (qdrant.py L142)
- Per-vector quantization_config supported since qdrant-client v1.1.1
- Dense vector intentionally left unquantized (different precision needs)
- Follows existing VectorParams pattern in _ensure_collection()
- No new interfaces, no new modules, no layering changes
- Research doc (docs/research/colbert-scalar-quantization.md) validates <1% quality loss

### Changes Made
- Created #793 (test task, TDD RED) at todo, blocked
- Refined #792 AC with precise qmodels call, migration scope, ruff clause
- Added depends_on: [793]
- Blocked both tasks: corpus below 5K chunks per YAGNI
- Moved #792 to todo (blocked)

### Dependencies
- Added: #793 (preceding test task)
- Verified: no other deps needed (single module change)

[[2026-03-15]] Sun 14:18
## Test-Writer Notes
- Paired test task #793 already archived  TestFromAC_ColBERTQuantizationConfig exists in tests/test_qdrant_vector_store.py (L495, 5 tests)
- Implementation committed in 79e30e1
- Cannot write RED tests: all AC lines already covered and passing
- AC coverage from #793:
| AC Line | Test(s) | Status |
|---------|---------|--------|
| quantization_config on colbert VectorParams | test_colbert_has_scalar_quantization | Covered |
| Dense VectorParams unchanged | test_dense_has_no_quantization | Covered |
| Existing tests pass | 29 pre-existing tests pass | Covered |
| New test from #793 passes | 5 TestFromAC tests pass | Covered |
| ruff clean | ruff: All checks passed | Covered |
- Pass-through: tests already exist from completed #793

[[2026-03-15]] Sun 18:51
## Builder Notes
- Pass-through: implementation and tests already exist from completed #793 (commit 79e30e1)
- Tests: 34 passed (5 TestFromAC + 29 existing), ruff clean
- No code changes needed  all AC lines already satisfied
- Evidence: all 5 TestFromAC_ColBERTQuantizationConfig tests PASSED

[[2026-03-15]] Sun 20:51
## Review Evidence
PASS - confidence .95. All 34 tests pass (5 TestFromAC + 29 existing). ruff clean. Coverage 96%. All 5 TestFromAC tests PRESERVED (no modification). Security clean. All 6 AC lines verified with specific evidence.

INFO: Commit 79e30e1 bundled qdrant.py impl with unrelated #803 commit (minor discipline note, not blocking).

[[2026-03-15]] Sun 20:51
## Review Evidence
PASS - confidence .95. 34/34 tests pass. ruff clean. Coverage qdrant.py 96%. All 5 TestFromAC PRESERVED. Security clean. 6/6 AC lines verified.
INFO: 79e30e1 bundled qdrant.py with unrelated #803 (minor, not blocking).

[[2026-03-16]] Mon 05:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _ensure_collection() adds ScalarQuantization(INT8, quantile=0.99, always_ram=True) to colbert VectorParams | qdrant.py L151-156: exact match to AC spec | PASS |
| Dense VectorParams unchanged (no quantization_config) | qdrant.py L143-147: dense VectorParams has only size + distance | PASS |
| All existing test_qdrant_vector_store.py tests still pass | Upstream: builder 34 passed, reviewer PASS .95; ruff clean; no code changes since; pytest environment-wide hang prevents independent run | PASS (upstream) |
| New test from #793 passes (ScalarQuantization(INT8) on colbert, None on dense) | tests/test_qdrant_vector_store.py L495-548: 5 TestFromAC_ColBERTQuantizationConfig tests covering all quantization params + dense=None + roundtrip | PASS (upstream) |
| Migration out of scope | _ensure_collection() guarded by collection_exists() check - existing collections untouched | PASS |
| ruff clean | uv run ruff check qdrant.py + test file: All checks passed | PASS |

### Test Results
- pytest: environment-wide hang (getwindowsversion KeyboardInterrupt); upstream: builder 34 passed, reviewer PASS .95
- ruff: All checks passed (qdrant.py + test_qdrant_vector_store.py)

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 79e30e1 | impl | src/owlbear/memory/knowledge/qdrant.py (+7 lines) | #792 |
| 8b1a69f | test | tests/test_qdrant_vector_store.py (+5 TestFromAC tests) | #793 |

Note: 79e30e1 bundles qdrant.py with test_slack_send_file.py (#803) - minor discipline (noted by reviewer, not blocking).

### Confidence: .95
### Action: archive
