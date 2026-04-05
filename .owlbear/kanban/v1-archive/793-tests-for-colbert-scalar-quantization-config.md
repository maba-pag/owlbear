---
id: 793
title: Tests for ColBERT scalar quantization config
status: archived
priority: nice-to-have
created: 2026-03-14T02:04:51.0774149+01:00
updated: 2026-03-22T18:59:28.929771+01:00
started: 2026-03-15T05:01:57.1268718+01:00
completed: 2026-03-15T05:01:57.1268718+01:00
tags:
    - phase-10
    - knowledge-graph
    - embedding
    - type:test
class: standard
---

Preceding test task for #792. Write failing tests that verify ColBERT quantization config on the Qdrant collection.

## AC
- [ ] New test class TestFromAC_ColBERTQuantizationConfig in test_qdrant_vector_store.py
- [ ] Test: after _ensure_collection(), collection info colbert vector has ScalarQuantization with type=INT8, quantile=0.99, always_ram=True
- [ ] Test: collection info dense vector has quantization_config=None
- [ ] All existing test_qdrant_vector_store.py tests still pass
- [ ] New tests FAIL on current code (TDD RED)
- [ ] ruff clean

## Deferred
Defer alongside #792 until corpus approaches 5K+ chunks.

[[2026-03-14]] Sat 04:27
## Test-Writer Notes
- Test file: tests/test_qdrant_vector_store.py
- Classes: TestFromAC_ColBERTQuantizationConfig
- Tests: 5 total (3 FAIL, 2 regression guards)
- ruff: clean

[[2026-03-14]] Sat 05:07
## Builder Notes
- Files changed: src/owlbear/memory/knowledge/qdrant.py (quantization_config added to colbert VectorParams in _ensure_collection)
- Implementation already committed in 79e30e1 (test-writer bundled it with #803 commit)
- Tests: 34 passed (5 TestFromAC_ColBERTQuantizationConfig + 29 existing)
- Coverage: qdrant.py 96% (misses are pre-existing: ImportError guard, Windows path branch)
- Lint: ruff clean
- No new commit needed  working tree already matches HEAD

[[2026-03-14]] Sat 12:56
## Review Evidence

### Test Results
- pytest: 34 passed, 0 failed (tests/test_qdrant_vector_store.py)
- 5 TestFromAC_ColBERTQuantizationConfig + 29 existing tests

### Lint Results
- ruff: All checks passed!

### Coverage
- qdrant.py: 96% (5 misses: L22-24 ImportError guard, L122 Windows path, L239 -- all pre-existing)

### Pass 1 -- CRITICAL

#### Security Review
- No security issues. Pure configuration change (7 lines). No user input, no secrets, no injection surface.

#### Test Integrity
- Test file: 1 commit (8b1a69f, test-writer). Builder never touched it.
- git diff 8b1a69f..HEAD: empty -- test file unmodified.
- All 5 TestFromAC methods: PRESERVED

#### Test Quality
- Assertion specificity: STRONG (checks type==INT8, quantile==0.99 approx, always_ram is True, dense quantization_config is None)
- Negative/error paths: ADEQUATE (test_dense_has_no_quantization verifies dense not affected; roundtrip test confirms store ops work)
- Mutation reasoning: STRONG (would catch: missing quantization_config, wrong type, wrong quantile, wrong always_ram, accidentally adding quantization to dense)
- Test independence: STRONG (each test creates own store via fixture)
- Descriptive names: STRONG (e.g. test_colbert_quantization_always_ram)

#### Data Safety
- No data safety issues. Pure config, no persistence changes, no shared state.

### Pass 2 -- INFORMATIONAL
- Implementation was bundled into test-writer commit for #803 (79e30e1). Unusual provenance but code is correct.

### AC Compliance
- AC1 TestFromAC_ColBERTQuantizationConfig class: PASS (test file L495)
- AC2 ScalarQuantization INT8 + quantile=0.99 + always_ram=True: PASS (3 tests: test_colbert_has_scalar_quantization, test_colbert_quantization_quantile, test_colbert_quantization_always_ram)
- AC3 Dense has quantization_config=None: PASS (test_dense_has_no_quantization)
- AC4 Existing tests pass: PASS (29 pre-existing tests all pass)
- AC5 TDD RED confirmed: PASS (test-writer notes: 3 FAIL, 2 pass)
- AC6 Ruff clean: PASS (All checks passed!)

### Verdict: PASS
### Confidence: .93

[[2026-03-15]] Sun 04:41
## Docs Gate
No docs impact. Config-only change with tests. Checklist: all 5 items N/A (internal config change, private method, sources already logged, no CLI, test task).

[[2026-03-15]] Sun 05:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_ColBERTQuantizationConfig class | Class at test_qdrant_vector_store.py:495, 5 methods | PASS |
| ScalarQuantization INT8/quantile/always_ram | 3 tests (L500, L513, L522) verify each field | PASS |
| Dense quantization_config=None | test_dense_has_no_quantization (L531) | PASS |
| All existing tests pass | 34 passed, 0 failed | PASS |
| TDD RED confirmed | Test-writer notes: 3 FAIL, 2 guards | PASS |
| ruff clean | All checks passed on task files | PASS |

### Test Results
- pytest: 34 passed, 63 w/ embeddings. 0 failures.
- ruff: clean on task files.

### Confidence: .96
### Action: archive
