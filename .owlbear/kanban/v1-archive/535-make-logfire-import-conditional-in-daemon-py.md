---
id: 535
title: Make logfire import conditional in daemon.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:40.4014439+01:00
updated: 2026-03-23T12:40:05.4574914+01:00
started: 2026-03-07T00:29:36.874959+01:00
completed: 2026-03-23T12:40:04.8733044+01:00
tags:
    - audit
    - config
    - scope:core
depends_on:
    - 853
class: standard
---

F-25: src/owlbear/daemon.py imports logfire at module import time even though OTel is optional. When logfire is not installed, importing owlbear.daemon must still succeed and only OTel configuration should fail. See docs/code-quality-audit.md F-25.

## Acceptance Criteria

- [ ] src/owlbear/daemon.py wraps the module-level import logfire in try/except ImportError and assigns logfire = None on the missing-dependency path
- [ ] With sys.modules['logfire'] = None, import owlbear.daemon succeeds and the module exposes logfire is None
- [ ] configure_otel(http://localhost:4318) raises RuntimeError mentioning logfire when logfire is unavailable
- [ ] When logfire is available, configure_otel() preserves the existing happy path: sets OTEL_EXPORTER_OTLP_ENDPOINT and calls logfire.configure(send_to_logfire=False, additional_span_processors=[])
- [ ] Existing OTel startup behavior remains unchanged when no otel_endpoint is provided
- [ ] Scope stays within src/owlbear/daemon.py; no new config fields, wrappers, or cross-module imports are added

## Notes

- TDD prerequisite: implementation depends on #853
- Existing optional-dependency precedents: src/owlbear/core/errors.py and src/owlbear/tools/browser/content_extractor.py
- Existing OTel regression coverage lives in tests/test_otel_config.py; missing-logfire coverage belongs there rather than in tests/test_daemon.py

[[2026-03-21]] Sat 05:06
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| daemon importable without logfire | Correct root outcome, but too vague for downstream implementation and review. The original wording did not define the module-level fallback shape, the configure_otel() failure contract, the happy-path behavior that must remain unchanged, or the TDD prerequisite. | Rewrote the task body into explicit acceptance criteria and added dependency on #853. |

### Architecture Notes
This is a single-domain core change confined to src/owlbear/daemon.py. It follows the existing optional-dependency pattern already used in src/owlbear/core/errors.py, where a module-level import is guarded and the missing dependency degrades gracefully, and it matches src/owlbear/tools/browser/content_extractor.py, where the optional dependency is only required when the feature is exercised.

The cited audit finding in docs/code-quality-audit.md F-25 is specifically about import-time failure. tests/test_otel_config.py already covers the existing happy-path OTel startup behavior, so the implementation contract must preserve configure_otel() and no-endpoint behavior in addition to making import succeed without logfire. The missing-logfire regression belongs in #853, which is the correct RED prerequisite for this implementation task.

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| import owlbear.daemon | optional logfire package missing at import time | ImportError or ModuleNotFoundError | Yes - guarded import falls back to logfire = None | daemon remains importable when OTel is unused |
| configure_otel() | user requests OTel with no logfire installed | RuntimeError | Yes - explicit guard raises early with actionable context | startup fails clearly instead of later AttributeError or NameError |

### Changes Made
- Claimed task #535 as mace-light
- Rewrote the task body with precise acceptance criteria for optional import fallback, configure_otel() failure behavior, happy-path preservation, and scope
- Added dependency on #853 so the RED task gates implementation
- Appended this architecture review
- Advanced task #535 from backlog to todo and released the claim

### Dependencies
- Added/Removed/Verified: added #853; verified docs/code-quality-audit.md, src/owlbear/core/errors.py, src/owlbear/tools/browser/content_extractor.py, src/owlbear/daemon.py, and tests/test_otel_config.py

[[2026-03-23]] Mon 07:20
## Test-Writer Notes
- Test file: tests/test_otel_config.py
- Classes added: TestFromAC_ConfigureOtelHappyPath, TestFromAC_NoEndpointBehavior, TestFromAC_ScopeConstraint
- Tests per category: happy 2, edge 0, error 0, boundary 2
- Total: 4 new tests added; pre-existing 2 tests from #853 (TestFromAC_LogfireOptionalImport) = 6 TestFromAC_ tests total
- ruff: clean
- NOTE: All 4 new tests PASS immediately. The implementation in daemon.py was pre-built before this test-writer dispatch. Task #853 wrote the failing RED tests for AC 1-3; those tests also pass as the build is complete. Builder should confirm all AC tests pass and advance to review.
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| daemon.py wraps import logfire in try/except; logfire=None fallback | TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire (#853) | happy |
| sys.modules logfire=None -> import succeeds, logfire is None | TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire (#853) | boundary |
| configure_otel raises RuntimeError mentioning logfire when absent | TestFromAC_LogfireOptionalImport::test_configure_otel_raises_runtime_error_without_logfire (#853) | error |
| configure_otel sets OTEL_EXPORTER_OTLP_ENDPOINT | TestFromAC_ConfigureOtelHappyPath::test_configure_otel_sets_otel_exporter_endpoint_var | happy |
| configure_otel calls logfire.configure(send_to_logfire=False, additional_span_processors=[]) | TestFromAC_ConfigureOtelHappyPath::test_configure_otel_calls_logfire_configure_with_exact_kwargs | happy |
| No otel_endpoint -> OTEL env var not set | TestFromAC_NoEndpointBehavior::test_run_daemon_does_not_set_otel_env_without_endpoint | boundary |
| Scope: no new OTel/logfire fields in OwlBearSettings | TestFromAC_ScopeConstraint::test_no_unexpected_otel_logfire_config_fields_in_settings | boundary |

[[2026-03-23]] Mon 08:07
## Builder Notes
- Files changed: none (implementation pre-built in src/owlbear/daemon.py; tests pre-written in tests/test_otel_config.py)
- Tests: 17 passed (all TestFromAC_ classes verified pass), coverage 30% on daemon.py (module is 394 stmts; OTel-related lines well covered)
- Lint: ruff clean
- Evidence: uv run pytest tests/test_otel_config.py -q = 17 passed; uv run ruff check src/owlbear/daemon.py tests/test_otel_config.py = All checks passed
- Fixes applied: None — implementation already satisfied all AC; builder confirmed test-writer pass-through note

[[2026-03-23]] Mon 08:57
## Review Evidence
## Review: #535 - Make logfire import conditional in daemon.py

### Test Results
- pytest: 17 passed, 0 failed, 2 warnings
- command: `uv run pytest tests/test_otel_config.py -q --tb=short`
- warnings: optional `qdrant_client` dependency not installed (pre-existing optional-dependency warning from `tests/conftest.py`)

### Lint Results
- repo-wide ruff: fails with pre-existing unrelated `RUF100` findings across many other test files
- command: `uv run ruff check src/ tests/`
- task-scoped ruff: All checks passed
- command: `uv run ruff check src/owlbear/daemon.py tests/test_otel_config.py`

### Coverage
- command: `uv run pytest tests/test_otel_config.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/daemon.py`: 30%
- Note: coverage is reported at whole-repo scope because this project only supports bare `--cov`; #535-specific OTel/logfire paths are exercised by targeted tests while unrelated daemon branches remain uncovered.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| daemon.py wraps module-level `import logfire` in try/except ImportError and sets `logfire=None` fallback | `TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire` (`tests/test_otel_config.py:287`) + code at `src/owlbear/daemon.py:32-34` | Yes - direct import or missing `None` fallback breaks import or assertion | COVERED |
| With `sys.modules['logfire']=None`, importing `owlbear.daemon` succeeds and exposes `logfire is None` | `TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire` (`tests/test_otel_config.py:287`) | Yes - asserts import success and `mod.logfire is None` | COVERED |
| `configure_otel(http://localhost:4318)` raises RuntimeError mentioning logfire when unavailable | `TestFromAC_LogfireOptionalImport::test_configure_otel_raises_runtime_error_without_logfire` (`tests/test_otel_config.py:292`) + guard at `src/owlbear/daemon.py:262-264` | Yes - test asserts RuntimeError with `match=logfire` | COVERED |
| Happy path sets `OTEL_EXPORTER_OTLP_ENDPOINT` and calls `logfire.configure(send_to_logfire=False, additional_span_processors=[])` | `TestFromAC_ConfigureOtelHappyPath::test_configure_otel_sets_otel_exporter_endpoint_var` (`tests/test_otel_config.py:307`) and `TestFromAC_ConfigureOtelHappyPath::test_configure_otel_calls_logfire_configure_with_exact_kwargs` (`tests/test_otel_config.py:322`) + code at `src/owlbear/daemon.py:265-266` | Yes - exact env value and exact kwargs asserted | COVERED |
| Existing startup behavior unchanged when no `otel_endpoint` provided | `TestFromAC_NoEndpointBehavior::test_run_daemon_does_not_set_otel_env_without_endpoint` (`tests/test_otel_config.py:349`) and pre-existing `test_no_logfire_configure_when_endpoint_none` (`tests/test_otel_config.py:200`) + branch at `src/owlbear/daemon.py:923` | Yes - env remains unset and no configure call without endpoint | COVERED |
| Scope limited to `src/owlbear/daemon.py`; no new config fields/wrappers/cross-module imports | `TestFromAC_ScopeConstraint::test_no_unexpected_otel_logfire_config_fields_in_settings` (`tests/test_otel_config.py:382`) + `src/owlbear/config.py:279` + only local `configure_otel` definition/use in `src/owlbear/daemon.py:246` and `src/owlbear/daemon.py:924` | Yes - asserts only `otel_endpoint` field and no cross-module `configure_otel` usage | COVERED |

#### Security Review
- Hardcoded secrets: none found in reviewed files.
- Injection/deserialization/eval risks: none introduced.
- Path traversal: none.
- Input validation: missing-logfire guard is explicit and fails fast with actionable RuntimeError message (`src/owlbear/daemon.py:262-264`).
- Secret leakage in logs: none.
- Result: No security issues found.

#### Test Integrity (TestFromAC comparison)
- Commit evidence: `git show --name-only 4986f3d` shows only `tests/test_otel_config.py` for #535 test-writer commit.
- Post-commit history: `git log 4986f3d..HEAD -- src/owlbear/daemon.py tests/test_otel_config.py` shows no subsequent commits touching these files for #535.

| Original Test Group | Change Made in Builder Phase | Assessment |
|---------------------|------------------------------|------------|
| `TestFromAC_LogfireOptionalImport` | No change | PRESERVED |
| `TestFromAC_ConfigureOtelHappyPath` | No change | PRESERVED |
| `TestFromAC_NoEndpointBehavior` | No change | PRESERVED |
| `TestFromAC_ScopeConstraint` | No change | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests assert exact env var value, exact `logfire.configure` kwargs, exact exception type/message match, and exact expected OTel field set. |
| Negative/error paths | STRONG | Missing dependency import path and RuntimeError path are explicitly tested. |
| Mutation reasoning | STRONG | Removing fallback import guard, weakening RuntimeError behavior, changing configure kwargs, or moving no-endpoint branch behavior would fail targeted assertions. |
| Test independence | STRONG | Each test creates fresh mocks/fixtures; logfire-absence tests isolate module import and restore state in teardown. |
| Descriptive names | STRONG | Test names encode scenario and expected behavior (e.g., `test_configure_otel_calls_logfire_configure_with_exact_kwargs`). |

#### Data Safety
- No data-integrity risks introduced by #535.
- Behavior is limited to guarded optional import and environment-variable assignment in existing OTel path.

#### Implementation-Aware Test Gaps
- Reviewed implementation at `src/owlbear/daemon.py:32-34`, `src/owlbear/daemon.py:246-267`, and `src/owlbear/daemon.py:923-925`.
- No significant untested behavioral path identified for the #535 contract.

### Pass 2 - INFORMATIONAL
- `get_errors` reports no diagnostics in `src/owlbear/daemon.py` or `tests/test_otel_config.py`.
- No additional informational findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Wrap `import logfire` with fallback `logfire=None` | `src/owlbear/daemon.py:32-34` | `TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire` | PASS |
| `sys.modules['logfire']=None` import succeeds, `logfire is None` | `tests/test_otel_config.py:287` | `TestFromAC_LogfireOptionalImport::test_daemon_import_succeeds_without_logfire` | PASS |
| `configure_otel` raises RuntimeError mentioning logfire when unavailable | `src/owlbear/daemon.py:262-264`, `tests/test_otel_config.py:292` | `TestFromAC_LogfireOptionalImport::test_configure_otel_raises_runtime_error_without_logfire` | PASS |
| Happy path env var + exact `logfire.configure(...)` call | `src/owlbear/daemon.py:265-266`, `tests/test_otel_config.py:307`, `tests/test_otel_config.py:322` | `TestFromAC_ConfigureOtelHappyPath::*` | PASS |
| No-endpoint startup behavior unchanged | `src/owlbear/daemon.py:923`, `tests/test_otel_config.py:349`, `tests/test_otel_config.py:200` | `TestFromAC_NoEndpointBehavior::test_run_daemon_does_not_set_otel_env_without_endpoint` (+ regression test) | PASS |
| Scope remains in daemon.py without new config/wrapper/cross-module imports | `src/owlbear/config.py:279`, `src/owlbear/daemon.py:246`, `src/owlbear/daemon.py:924`, cross-file usage search shows only daemon references | `TestFromAC_ScopeConstraint::test_no_unexpected_otel_logfire_config_fields_in_settings` | PASS |

### Verdict: PASS
### Confidence: .93

[[2026-03-23]] Mon 12:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal implementation detail (conditional import guard in daemon.py). No behavior, API, or convention change visible to agents or users. logfire/OTel not mentioned in copilot-instructions.md and does not need to be. |
| 2 | Docstrings complete | Yes | Pass | `configure_otel` at `src/owlbear/daemon.py:246` has accurate docstring covering parameters and the new `Raises: RuntimeError` when logfire not installed. Module-level guard at line 31-34 is self-documenting with inline comment. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used. Pattern mirrors existing internal precedents (src/owlbear/core/errors.py, src/owlbear/tools/browser/content_extractor.py). |
| 4 | README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc produced | No | N/A | No dedicated research doc. Architecture review cites existing docs/code-quality-audit.md F-25. No follow-up kanban tasks needed from research phase. |
| 6 | No impact summary | -- | -- | Items 1,3,4,5 all N/A. Item 2 already correct in code. No files require updates. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/535-* files found)

[[2026-03-23]] Mon 12:40
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Wrap import logfire in try/except, logfire=None fallback | src/owlbear/daemon.py:31-34 guarded import confirmed | PASS |
| sys.modules logfire=None import succeeds, logfire is None | 17 passed in test_otel_config.py; TestFromAC_LogfireOptionalImport | PASS |
| configure_otel raises RuntimeError mentioning logfire when unavailable | src/owlbear/daemon.py:262-264 guard + TestFromAC_LogfireOptionalImport::test_configure_otel_raises_runtime_error_without_logfire | PASS |
| Happy path sets OTEL_EXPORTER_OTLP_ENDPOINT and calls logfire.configure(send_to_logfire=False, additional_span_processors=[]) | src/owlbear/daemon.py:265-266 + TestFromAC_ConfigureOtelHappyPath (2 tests) | PASS |
| No-endpoint startup behavior unchanged | TestFromAC_NoEndpointBehavior::test_run_daemon_does_not_set_otel_env_without_endpoint | PASS |
| Scope stays within daemon.py; no new config fields/wrappers/cross-module imports | TestFromAC_ScopeConstraint::test_no_unexpected_otel_logfire_config_fields_in_settings | PASS |

### Test Results
- pytest (task-scoped): 17 passed, 0 failed
- pytest (full suite): 3918 passed, 94 failed, 20 skipped. All 94 failures are pre-existing baseline (numpy compat, other-task RED tests, bootstrap return-value changes). No test_otel_config.py failures.
- ruff (task-scoped): All checks passed

### Upstream Commits
- 4986f3d test: add AC 4-6 coverage for #535 optional logfire import (#535, test-writer) [tests/test_otel_config.py]
- 344313e feat: make logfire an optional import in daemon.py (#853, builder) [src/owlbear/daemon.py]
- No uncommitted leftovers for #535

### Architect Quality
- AC specificity: 5/5 - precise, verifiable criteria
- Edge case coverage: complete (happy, error, no-endpoint, scope)
- Design direction: effective (cited existing precedents, correct test file)
- AC quality score: 5

### Reviewer Evidence
- Reviewer PASS at .93 confidence with detailed AC mapping table
- All TestFromAC_ tests preserved (no builder modifications)

### Confidence: .97
### Action: archive
