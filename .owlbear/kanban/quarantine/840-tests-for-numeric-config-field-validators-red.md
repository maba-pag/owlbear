---
id: 840
title: Tests for numeric config field validators (RED)
status: archived
priority: nice-to-have
created: 2026-03-16T12:40:18.3359337+01:00
updated: 2026-03-16T21:39:47.0635362+01:00
started: 2026-03-16T21:39:25.1154767+01:00
completed: 2026-03-16T21:39:25.1154767+01:00
tags:
    - config
    - type:test
    - rigor:lean
class: standard
---

Preceding test task for #547.

Write failing tests in tests/test_config.py that verify:

- temporal_decay_rate rejects values < 0 and > 1 (ValidationError)
- temporal_recency_weight rejects values < 0 and > 1 (ValidationError)
- embedding_idle_timeout rejects values < 0 (ValidationError), accepts 0
- approval_timeout rejects values <= 0 (ValidationError)
- All four fields accept their default values without error

Pattern: follow existing test classes in test_config.py (e.g. TestTemporalSettingsDefaults).
Use pytest.raises(ValidationError) for rejection cases.
File: tests/test_config.py

[[2026-03-16]] Mon 14:43

## Test-Writer Notes

- Test file: tests/test_config.py (appended)
- Classes: TestFromAC_TemporalDecayRateValidator, TestFromAC_TemporalRecencyWeightValidator, TestFromAC_EmbeddingIdleTimeoutValidator, TestFromAC_ApprovalTimeoutValidator
- Total: 12 tests, all FAIL verified (FFFFFFFFFFFF)
- ruff: clean

[[2026-03-16]] Mon 20:29

## Builder Notes

- Files changed: src/owlbear/config.py
- Tests: 12 passed (TestFromAC), 71 passed in tests/test_config.py
- Coverage: src/owlbear/config.py 85% (scoped run on tests/test_config.py)
- Lint: ruff check src/owlbear/config.py tests/test_config.py passed
- Evidence: RED before fix (12 failed: missing ge/le/gt constraints); GREEN after fix (12 passed)
- Fixes applied: Added Field constraints: temporal_decay_rate ge=0.0 le=1.0; temporal_recency_weight ge=0.0 le=1.0; embedding_idle_timeout ge=0; approval_timeout gt=0.0
- Notes: repo-wide ruff check has unrelated pre-existing failures outside this task scope

[[2026-03-16]] Mon 20:47

## Review Evidence

### Test Results

- pytest: 71 passed, 0 failed (tests/test_config.py)
- 12 TestFromAC tests all pass

### Lint Results

- ruff: All checks passed (src/owlbear/config.py, tests/test_config.py)

### Coverage

- src/owlbear/config.py: 85% (uncovered lines 401-549 are unrelated to this task's changes at L162-219)

### Pass 1 -- CRITICAL

#### Security Review

- No security issues. Changes are declarative Field() constraint additions (ge, le, gt). No input handling, no secrets, no injection surface.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_TemporalDecayRateValidator::test_below_zero_raises | No change | PRESERVED |
| TestFromAC_TemporalDecayRateValidator::test_above_one_raises | No change | PRESERVED |
| TestFromAC_TemporalDecayRateValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_below_zero_raises | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_above_one_raises | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_negative_raises | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_zero_accepted | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_zero_raises | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_negative_raises | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_default_accepted | No change | PRESERVED |

Builder only changed src/owlbear/config.py. All 12 TestFromAC tests are intact.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | pytest.raises(ValidationError, match=field_name) for rejections; exact value checks for defaults (0.001, 0.1, 600, 120.0); field.metadata assertions prove constraints exist |
| Negative/error paths | STRONG | Each field has rejection tests for out-of-range values plus default acceptance |
| Mutation reasoning | STRONG | Removing any ge/le/gt constraint causes the corresponding test to fail |
| Test independence | STRONG | monkeypatch env vars + default_settings fixture; no shared mutable state |
| Descriptive names | STRONG | test_temporal_decay_rate_below_zero_raises, test_approval_timeout_zero_raises, etc. |

#### Data Safety

- No data safety issues. Purely declarative Pydantic Field constraints.

### Pass 2 -- INFORMATIONAL

- No informational findings. Implementation is minimal (4 constraint additions) and clean.
- Note: both test-writer and builder changes are uncommitted (process gap, auditor concern).

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| temporal_decay_rate rejects < 0 and > 1 | config.py L188-189: ge=0.0, le=1.0 | test_temporal_decay_rate_below_zero_raises, _above_one_raises | PASS |
| temporal_recency_weight rejects < 0 and > 1 | config.py L195-196: ge=0.0, le=1.0 | test_temporal_recency_weight_below_zero_raises, _above_one_raises | PASS |
| embedding_idle_timeout rejects < 0, accepts 0 | config.py L164: ge=0 | test_embedding_idle_timeout_negative_raises,_zero_accepted | PASS |
| approval_timeout rejects <= 0 | config.py L219: gt=0.0 | test_approval_timeout_zero_raises, _negative_raises | PASS |
| All four fields accept defaults | Constraints compatible with defaults | test_*_default_accepted (4 tests) | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-16]] Mon 20:47

## Review Evidence

### Test Results

- pytest: 71 passed, 0 failed (tests/test_config.py)
- 12 TestFromAC tests all pass

### Lint Results

- ruff: All checks passed (src/owlbear/config.py, tests/test_config.py)

### Coverage

- src/owlbear/config.py: 85% (uncovered lines 401-549 are unrelated to this task's changes at L162-219)

### Pass 1 -- CRITICAL

#### Security Review

- No security issues. Changes are declarative Field() constraint additions (ge, le, gt). No input handling, no secrets, no injection surface.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_TemporalDecayRateValidator::test_below_zero_raises | No change | PRESERVED |
| TestFromAC_TemporalDecayRateValidator::test_above_one_raises | No change | PRESERVED |
| TestFromAC_TemporalDecayRateValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_below_zero_raises | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_above_one_raises | No change | PRESERVED |
| TestFromAC_TemporalRecencyWeightValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_negative_raises | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_zero_accepted | No change | PRESERVED |
| TestFromAC_EmbeddingIdleTimeoutValidator::test_default_accepted | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_zero_raises | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_negative_raises | No change | PRESERVED |
| TestFromAC_ApprovalTimeoutValidator::test_default_accepted | No change | PRESERVED |

Builder only changed src/owlbear/config.py. All 12 TestFromAC tests are intact.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | pytest.raises(ValidationError, match=field_name) for rejections; exact value checks for defaults (0.001, 0.1, 600, 120.0); field.metadata assertions prove constraints exist |
| Negative/error paths | STRONG | Each field has rejection tests for out-of-range values plus default acceptance |
| Mutation reasoning | STRONG | Removing any ge/le/gt constraint causes the corresponding test to fail |
| Test independence | STRONG | monkeypatch env vars + default_settings fixture; no shared mutable state |
| Descriptive names | STRONG | test_temporal_decay_rate_below_zero_raises, test_approval_timeout_zero_raises, etc. |

#### Data Safety

- No data safety issues. Purely declarative Pydantic Field constraints.

### Pass 2 -- INFORMATIONAL

- No informational findings. Implementation is minimal (4 constraint additions) and clean.
- Note: both test-writer and builder changes are uncommitted (process gap, auditor concern).

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| temporal_decay_rate rejects < 0 and > 1 | config.py L188-189: ge=0.0, le=1.0 | test_temporal_decay_rate_below_zero_raises, _above_one_raises | PASS |
| temporal_recency_weight rejects < 0 and > 1 | config.py L195-196: ge=0.0, le=1.0 | test_temporal_recency_weight_below_zero_raises, _above_one_raises | PASS |
| embedding_idle_timeout rejects < 0, accepts 0 | config.py L164: ge=0 | test_embedding_idle_timeout_negative_raises,_zero_accepted | PASS |
| approval_timeout rejects <= 0 | config.py L219: gt=0.0 | test_approval_timeout_zero_raises, _negative_raises | PASS |
| All four fields accept defaults | Constraints compatible with defaults | test_*_default_accepted (4 tests) | PASS |

### Verdict: PASS (confidence .95)
