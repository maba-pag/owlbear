# make_completed_process Duplicate-Guard Research

> **Owning task:** #975 — Add make_completed_process duplicate-guard to test_conftest_helpers.py
> **Date:** 2026-03-24  **Status:** Complete

## 1. Context and Question

Task #975 asks whether a duplicate-guard for `make_completed_process` belongs in `TestFromAC_ZeroDuplicates`. The parent research (`docs/research/completedprocess-factory-implementation-gate.md`, #927) identified this as a gap — the factory is shared via `conftest.py` but has no guard preventing consumer files from redefining it inline.

## 2. Sources Studied

| # | Source | What | Relevance |
|---|--------|------|-----------|
| S1 | `tests/test_conftest_helpers.py:324-381` | Three existing duplicate-guards in `TestFromAC_ZeroDuplicates` | .95 |
| S2 | `tests/conftest.py:126-139` | Single definition of `make_completed_process` factory | .95 |
| S3 | `tests/test_cli_chat.py:305-350` | 4 import-only usages of `make_completed_process` | .90 |
| S4 | `tests/test_cli_board.py:409-435` | 2 import-only usages inside router helpers | .90 |
| S5 | `docs/research/completedprocess-factory-implementation-gate.md` §4 | Parent recommendation (.92 confidence) to add this guard | .85 |
| S6 | pytest "factories as fixtures" pattern (Python Testing with pytest, ch. 4) | Factory-function sharing pattern that duplicate-guards protect | .80 |

## 3. Analysis

| Criterion | Assessment |
|-----------|-----------|
| Theoretical validity | Sound — guards prevent copy-paste drift when multiple test files consume a shared factory [S1, S6] |
| Prior art | Three identical guards already exist in the same class [S1] |
| Technical feasibility | Trivial — `_has_func_def()` helper exists; ~10 LOC parametrized method [S1] |
| Architecture fit | Fits into existing `TestFromAC_ZeroDuplicates` class, no new files [S1] |
| KISS/YAGNI | Passes both — follows established pattern, protects 2 active consumers [S3, S4] |
| Risk | Near-zero — pure additive test, cannot break existing behavior |

**Current state:** `make_completed_process` is defined only in `conftest.py:126` [S2]. Both `test_cli_chat.py` [S3] and `test_cli_board.py` [S4] import it. No file redefines it. The guard prevents regression.

## 4. Recommendation (.92 confidence)

Add a parametrized `test_no_duplicate_make_completed_process` method in `TestFromAC_ZeroDuplicates` covering `test_cli_chat.py` and `test_cli_board.py`. Pattern copied directly from the `_make_settings` guard [S1].

No decision request needed — single clear approach, no trade-offs.

## 5. Follow-up Tasks

No new tasks — #975 itself is the implementation task. AC is validated as feasible; advance to `backlog` for architect gate.
