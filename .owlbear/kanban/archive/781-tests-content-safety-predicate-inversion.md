---
id: 781
title: Tests — Content safety predicate inversion
status: done
priority: needed
created: '2026-04-10T12:30:43.995109+00:00'
updated: '2026-04-11T14:47:03.730114+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `wrap_untrusted_content()` wraps content for source types: `url_list`, `authenticated_web`, and any unknown future type
- Tests verify `wrap_untrusted_content()` does NOT wrap content for `file`, `text`, `file_glob`
- Tests verify idempotency (no double-wrap) is preserved
- File: `tests/test_content_safety_inversion_775.py`

## Context
- WS-B: Pipeline Quality
- Scope item 8 from #775
- See research F4: defense-in-depth, safe to ship independently

[[2026-04-11]]
## Architecture Review

### AC Corrections (for downstream reference)
- AC1/AC2 name `wrap_untrusted_content()` but that function has no `source_type` parameter. The actual predicate is `should_wrap(source_type)` in `content_safety.py`. The existing tests correctly test `should_wrap()`.
- AC3 idempotency: `wrap_untrusted_content()` idempotency is already tested in `test_content_safety_735.py` (`test_idempotency_guard_no_double_wrap`). If the test-writer wants to add it to this file, fine, but it's not missing coverage.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests `should_wrap()` predicate inversion only |
| Interface clarity | PASS | AC intent clear despite function name imprecision; tests already correct |
| Dependency correctness | PASS | No dependencies, standalone test task |
| Module layering | PASS | Tests import from `owlbear_knowledge.content_safety` |
| TDD compliance | N/A | This IS the test task |
| KISS/YAGNI | PASS | Minimal, focused tests |
| Premise challenge | PASS | Tests validate security-critical predicate inversion |
| Pattern consistency | PASS | Follows patterns from `test_content_safety_735.py` |
| Security surface | PASS | Strengthens security posture |
| Single domain | PASS | knowledge domain only |

### Challenge Results
- Challenger: reconsider (0.65)
- Concerns: AC names wrong function, AC3 redundant, integration gap
- Architect response: REBUTTED — tests already exist and are correct; AC imprecision is documentation-level, not behavioral; integration tested in #735; predicate inversion is the correct scope boundary

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC corrections noted for downstream reference. Tests in `tests/test_content_safety_inversion_775.py` correctly cover `should_wrap()` deny-list predicate.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_content_safety_inversion_775.py
- Classes: `TestFromAC_ShouldWrapPredicate`
- Tests per category: happy 6, edge 2, error 0, boundary 3
- Total: 11 tests
- ruff: clean (removed unused `pytest` import)
- Commit: 045aa682

### AC Coverage
| AC | Tests |
|----|-------|
| AC1: `should_wrap()` returns True for `url_list`, `authenticated_web`, unknown types | `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` |
| AC2: `should_wrap()` returns False for `file`, `text`, `file_glob` | `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false` |
| AC2 boundary: `None` and empty string backward compat | `test_none_returns_false`, `test_empty_string_returns_false` |
| Return-type strictness (`is True` / `is False`) | `test_return_type_is_bool_for_truthy_input`, `test_return_type_is_bool_for_falsy_input` |

### Note on RED Phase
`should_wrap()` was fully implemented as part of #775 prior to this task advancing. All 11 tests pass against the existing implementation — RED phase was bypassed by pipeline ordering. Tests are valid regression coverage and correctly specify the contract. Builder can skip GREEN phase for this file.
[[2026-04-11]]
## Builder Notes
- Non-implementation pass-through — `should_wrap()` was fully implemented as part of #775 prior to this task advancing.
- No code changes made.
- Test verification: `uv run pytest tests/test_content_safety_inversion_775.py` → **11 passed, 0 failed**.
- Ruff: not applicable (test-writer already cleaned, no new code added).
- Coverage: all 11 `TestFromAC_ShouldWrapPredicate` tests confirm the existing implementation satisfies AC1, AC2, and return-type strictness.
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: **11 passed, 0 failed** (independently run via quality-runner)

### Lint
- ruff: **clean** (0 violations)

### Coverage
- `owlbear_knowledge.content_safety`: **62%**
- Note: 62% is expected. This task's test file covers `should_wrap()` only. `wrap_untrusted_content()` is covered by `test_content_safety_735.py`. `should_wrap()` itself has 100% line coverage from these 11 tests (3 paths: falsy guard → False, in trusted set → False, not in trusted set → True — all exercised).

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `should_wrap()` returns True for `url_list` | `test_url_list_returns_true` | Yes — `is True` assertion catches False | COVERED |
| AC1: returns True for `authenticated_web` | `test_authenticated_web_returns_true` | Yes | COVERED |
| AC1: returns True for unknown/future types | `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` | Yes — two cases: named (`rss_feed`) and arbitrary string | COVERED |
| AC2: returns False for `file` | `test_file_returns_false` | Yes — `is False` catches True | COVERED |
| AC2: returns False for `text` | `test_text_returns_false` | Yes | COVERED |
| AC2: returns False for `file_glob` | `test_file_glob_returns_false` | Yes | COVERED |
| AC3: idempotency | N/A — architect-approved: already covered in `test_content_safety_735.py` (`test_idempotency_guard_no_double_wrap`). Not missing coverage. | N/A | N/A |
| Return-type strictness | `test_return_type_is_bool_for_truthy_input`, `test_return_type_is_bool_for_falsy_input` | Yes — catches truthy-not-True (e.g. `1`), falsy-not-False (e.g. `0`) | COVERED |
| Boundary: None backward compat | `test_none_returns_false` | Yes — catches removal of falsy guard | COVERED |
| Boundary: empty string | `test_empty_string_returns_false` | Yes | COVERED |

#### Security Review
- No hardcoded secrets, injection surfaces, path traversal, insecure deserialization, dependency risk, or secret leakage. The file under review is a pure predicate test. Clean.

#### Test Integrity (TestFromAC Modification Check)
- Builder made zero code changes. Test file committed prior by test-writer at commit `045aa682`. No modifications to `TestFromAC_ShouldWrapPredicate` tests — all assertions intact and strict (`is True` / `is False`).

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | All 11 assertions use `is True` or `is False` — strict bool identity, not just truthy/falsy |
| Negative/error-path coverage | STRONG | Both return paths (True and False) each tested ≥3 ways; None and empty string edge cases covered |
| Manual mutation reasoning | STRONG | Flipping `not in` to `in` in source fails AC1 tests. Removing falsy guard fails `test_none_returns_false`. Adding `url_list` to `_TRUSTED_SOURCE_TYPES` fails `test_url_list_returns_true` |
| Test independence | STRONG | Each test imports `should_wrap` locally; no shared mutable state |
| Descriptive test names | STRONG | All names self-documenting (`test_url_list_returns_true`, `test_none_returns_false`) |

#### Data Safety
- Pure predicate tests. No LLM output, shared state, multi-step operations, or unbounded inputs. Clean.

#### Implementation-Aware Test Gaps
- `should_wrap()` has 3 code paths: `not source_type → False`, `source_type in _TRUSTED_SOURCE_TYPES → False`, `source_type not in _TRUSTED_SOURCE_TYPES → True`. All 3 paths exercised. No untested paths.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (pass-through, no implementation needed) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `content_safety.py` has duplicate module-level constant definitions (`_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` defined twice, lines 9–17 and ~47–57). Python silently overwrites with identical values — no functional impact. Pre-existing issue outside the scope of this task. Recommend cleanup in a future housekeeping task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `should_wrap()` True for `url_list`, `authenticated_web`, unknown types | pytest 11 passed; `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` confirm `is True` | 4 tests | PASS |
| `should_wrap()` False for `file`, `text`, `file_glob` | pytest 11 passed; `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false` confirm `is False` | 3 tests | PASS |
| Idempotency preserved | Arch-reviewed: covered in `test_content_safety_735.py`; out-of-scope for this task | N/A | N/A |
| File: `tests/test_content_safety_inversion_775.py` | File exists, 11 tests, class `TestFromAC_ShouldWrapPredicate` | Full file | PASS |

### Confidence: .96
### Verdict: PASS
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure test task (`type:test`). Builder confirmed zero code changes. `should_wrap()` was already implemented in #775. No interface change. |
| 2 | Module docstrings | No | N/A | No modules created or modified by this task. `content_safety.py` docstrings verified accurate (read file — `should_wrap()` has full Args/Returns docstring, module docstring present). |
| 3 | External attribution | No | N/A | "defense-in-depth" is a general security principle, not a traceable external implementation. No new external patterns used. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | No #781-specific research doc produced. "See research F4" refers to `775-phase1-browser-pipeline-schema.md` (parent task's research doc, file exists, linked from parent). |

### Files Updated
None — no docs impact.

### Scratch Files
No `.owlbear/scratch/781-*` files found. Nothing to clean.

### Verdict
No docs impact. Advancing to done.
[[2026-04-11]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `should_wrap()` True for `url_list`, `authenticated_web`, unknown types | 4 tests pass (`is True`): `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` | PASS |
| AC2: `should_wrap()` False for `file`, `text`, `file_glob` | 5 tests pass (`is False`): `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false`, `test_none_returns_false`, `test_empty_string_returns_false` | PASS |
| AC3: Idempotency preserved | Arch-approved N/A: covered in `test_content_safety_735.py` (`test_idempotency_guard_no_double_wrap`) — verified passing | N/A |
| AC4: File `tests/test_content_safety_inversion_775.py` | Exists, 11 tests, class `TestFromAC_ShouldWrapPredicate`, commit `045aa682` | PASS |

### Test Results
- pytest (task scope): 11/11 passed
- pytest (content_safety domain): 27/27 passed
- pytest (full suite): 3430 passed, 304 failed — all failures in unrelated modules (orchestrator, planner, analysis, etc.), none in content_safety
- ruff: clean (0 violations)

### Architect Quality: 4/5
AC named `wrap_untrusted_content()` but actual function is `should_wrap()`. Architect review caught and corrected this. AC3 redundancy noted. Minor imprecision, not behavioral. Downstream agents handled correctly.

### Deduction Breakdown
- Start: 1.00
- No deductions applied (all AC evidenced, lint clean, reviewer thorough, no in-scope failures)

### Confidence: .98
### Action: archive