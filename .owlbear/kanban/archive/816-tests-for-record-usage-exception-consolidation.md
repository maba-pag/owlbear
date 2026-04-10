---
id: 816
title: Tests for _record_usage exception consolidation
status: archived
priority: nice-to-have
created: 2026-03-15T07:49:17.8914678+01:00
updated: 2026-03-15T12:31:51.1958104+01:00
started: 2026-03-15T12:31:46.6265169+01:00
completed: 2026-03-15T12:31:46.6265169+01:00
tags:
    - test
    - scope:core
depends_on:
    - 528
class: standard
---

- Test that when calc_estimated_cost raises, record is still created with estimated_cost_usd=None AND premium_requests=None (enrichment block fails as unit)
- Test that when get_premium_requests raises (but cost succeeds), record is still created with cost set and premium_requests=None
- Test that both enrichment failures log at WARNING (not DEBUG) with exc_info=True
- Test that outer handler (result.usage() failure) logs at WARNING
- Existing tests (test_record_includes_estimated_cost, test_record_includes_premium_requests_for_copilot, test_no_premium_requests_for_non_copilot_provider, test_cost_import_error_returns_none) still pass after refactor
- All new tests FAIL before implementation (TDD RED)

[[2026-03-15]] Sun 09:15
## Test-Writer Notes
- Test file: tests/test_record_usage_consolidation.py (extended)
- New classes: TestFromACPremiumFailureCostPreserved, TestFromACPremiumFailureLogging
- Pre-existing classes: TestFromACEnrichmentFailsAsUnit, TestFromACLogLevelWarning, TestFromACStructuralConstraints
- Tests added: 3 new (happy 2, error 0, edge 0, boundary 1)
- Total: 9 tests (6 pre-existing + 3 new), all PASS
- ruff: clean
- NOTE: #528 implementation already at review -- TDD order inverted. All tests pass against current code.
- AC coverage:
  AC1 (cost raises both None): test_cost_raises_both_fields_none [pre-existing]
  AC2 (premium raises cost preserved): test_premium_raises_cost_preserved_premium_none, test_premium_failure_core_record_still_appended [NEW]
  AC3 (WARNING logging): test_enrichment_failure_logs_warning [pre-existing], test_premium_failure_logs_warning_with_exc_info [NEW]
  AC4 (outer handler WARNING): test_outer_usage_failure_logs_warning [pre-existing]
  AC5 (existing tests pass): 7/7 in TestUsageRecordCostAndPremium PASS

[[2026-03-15]] Sun 11:18
## Builder Notes
- Non-implementation task (TDD order inverted: #528 impl already at review)
- Tests: 9 passed, 0 failed in test_record_usage_consolidation.py
- ruff: clean
- No code changes needed  all TestFromAC classes pass against existing implementation
- Passing through to review.

[[2026-03-15]] Sun 11:58
## Review Evidence
### Test Results
- pytest (scoped): 9 passed, 0 failed (test_record_usage_consolidation.py)
- ruff: All checks passed
- Coverage: agent.py 73% overall; _record_usage (L185-236) fully covered

### TestFromAC Comparison
Builder made NO changes to any TestFromAC class. Single commit 5148b67 from #528 auditor batch. All 5 classes PRESERVED.

### Test Quality
| Dimension | Rating |
|-----------|--------|
| Assertion specificity | STRONG |
| Negative/error-path | ADEQUATE |
| Mutation detection | STRONG |
| Test independence | STRONG |
| Descriptive names | STRONG |

### Security Review
N/A (test-only task, no source code changes)

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cost raises -> both None | test_cost_raises_both_fields_none L88-92 | PASS |
| AC2: premium raises, cost preserved | test_premium_raises_cost_preserved_premium_none L186-196 + test_premium_failure_core_record_still_appended L198-215 | PASS |
| AC3: WARNING with exc_info | test_enrichment_failure_logs_warning L99-119 + test_premium_failure_logs_warning_with_exc_info L224-248 | PASS |
| AC4: outer handler WARNING | test_outer_usage_failure_logs_warning L121-145 | PASS |
| AC5: existing tests still pass | 9/9 pass | PASS |
| AC6: TDD RED | Infeasible (TDD inverted, #528 impl preceded). Acknowledged by test-writer. | N/A |

### Verdict: PASS
### Confidence: .92
### Action: move to docs

[[2026-03-15]] Sun 12:05
## Docs Gate

[[2026-03-15]] Sun 12:05
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task, no behavior/API change |
| 2 | Docstrings complete | No | N/A | Only test file added; has module docstring. No source modules changed |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | Yes | Pass | Test-only task with no documentation implications |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/816-* files found)

[[2026-03-15]] Sun 12:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cost raises both None | test_cost_raises_both_fields_none L76-92 | PASS |
| AC2: premium raises cost preserved | test_premium_raises_cost_preserved_premium_none L217-240 + test_premium_failure_core_record_still_appended L242-264 | PASS |
| AC3: WARNING with exc_info | test_enrichment_failure_logs_warning L96-119 + test_premium_failure_logs_warning_with_exc_info L269-297 | PASS |
| AC4: outer handler WARNING | test_outer_usage_failure_logs_warning L121-148 | PASS |
| AC5: existing tests pass | 9/9 scoped pass | PASS |
| AC6: TDD RED | Infeasible (TDD inverted, #528 impl preceded) | N/A |

### Test Results
- pytest (scoped): 9 passed, 0 failed (test_record_usage_consolidation.py)
- pytest (full): 3470 passed, 51 failed (pre-existing: regex env, bootstrap sig, e2e imports, role policy)
- ruff: All checks passed

### Upstream Commits
- 5148b67 refactor: consolidate _record_usage exception handlers + tests (#528, auditor)

### Confidence: .97
### Action: archive
