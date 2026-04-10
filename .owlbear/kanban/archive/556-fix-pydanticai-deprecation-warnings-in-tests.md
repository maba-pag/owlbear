---
id: 556
title: Fix PydanticAI deprecation warnings in tests
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:58.5656888+01:00
updated: 2026-03-23T12:45:43.4343173+01:00
started: 2026-03-07T01:05:39.6945136+01:00
completed: 2026-03-23T12:45:42.8649426+01:00
tags:
    - audit
    - test
class: standard
---

L3: 77 warnings about model name without provider prefix. Bootstrap tests pass MagicMock as model. Not failures but noisy. Fix model references. AC: zero deprecation warnings in test output. See docs/test-quality-audit.md.

## Research (2026-03-07)

See docs/research/pydanticai-deprecation-warnings.md for full analysis.

**Root cause:** PydanticAI v0.8.1 deprecated bare model names in infer_model(). 77 warnings from 2 categories: 43 bare 'gpt-4o' string (build_toolsets fallback to settings.chat_model) + 34 MagicMock (bootstrap tests pass MagicMock without spec=Model).

**Fix (test-only, zero source changes):**

1. Change MagicMock() to MagicMock(spec=Model) in 17 bootstrap integration tests
2. Pass chat_model='test' to build_toolsets() in ~28 test calls + 1 expansion test
3. Verify with: uv run pytest -W error::DeprecationWarning

Related: #551 (remove hardcoded gpt-4o defaults from source  separate task).

[[2026-03-20]] Fri 17:31

## Test-Writer Notes

- Test files: tests/test_bootstrap.py, tests/test_knowledge_query_service_expansion.py
- RED gate tests written by task #861 (archived) — already present in test files
- Classes: TestFromAC_BuildToolsetsNoBareModelDeprecation (in test_bootstrap.py)
- Standalone test: test_build_toolsets_expansion_path_no_bare_model_deprecation (in test_knowledge_query_service_expansion.py)
- Tests per category: happy 0, edge 0, error 0, boundary 4 (all at the chat_model fallback boundary)
- Total: 4 tests, all FAIL (verified)
- ruff: clean on both files
- AC coverage:
  - AC: zero deprecation warnings in test output
  - test_knowledge_infra_receives_model_not_bare_string — verifies_build_knowledge_infra receives Model not bare string (boundary)
  - test_knowledge_toolset_receives_model_not_bare_string — verifies_build_knowledge_toolset receives Model not bare string (boundary)
  - test_bookmark_toolset_receives_model_not_bare_string — verifies_build_bookmark_toolset receives Model not bare string (boundary)
  - test_build_toolsets_expansion_path_no_bare_model_deprecation — verifies expansion path receives Model not bare string (boundary)
- Note: MagicMock-without-spec warning path (from original research) is no longer active — bootstrap() now creates OpenAIChatModel inline after create_copilot_client(), not via create_copilot_model. Remaining warning surface is the chat_model or settings.chat_model fallback in src/owlbear/bootstrap/toolsets.py.
- Builder fix required: update toolsets.py so the chat_model fallback passes a Model instance (not bare string) to all knowledge builder functions.

[[2026-03-20]] Fri 18:26

## Builder Notes

- Files changed: src/owlbear/bootstrap/toolsets.py, tests/test_bootstrap.py
- Tests: 6 passed (4 TestFromAC + 2 updated companion tests), ruff clean
- Fix: _wire_knowledge_toolsets() resolves str/None chat_model to OpenAIChatModel(name, provider=OpenAIProvider(api_key='placeholder')) before passing to all knowledge builders. Production bootstrap always passes a Model instance.
- Companion tests updated: chat_model='gpt-4o' replaced with ANY (focus was project_id/max_tokens, not model type)

[[2026-03-20]] Fri 19:08

## Review Evidence

- smoke append test
- reviewer syntax check

[[2026-03-20]] Fri 19:08

## Review Evidence

### Test Results

- uv run pytest tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py -q --tb=short -W error::DeprecationWarning => 48 failed, 131 passed (baseline/environment failures in this workspace snapshot).
- uv run pytest tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py -q --tb=short -W error::DeprecationWarning -k TestFromAC_BuildToolsetsNoBareModelDeprecation or test_build_toolsets_expansion_path_no_bare_model_deprecation => 4 passed, 175 deselected.
- uv run pytest tests/test_bootstrap.py::TestBuildToolsetsProjectScope::test_project_id_forwarded_to_knowledge_toolset tests/test_bootstrap.py::TestBuildToolsetsKnowledgeService::test_settings_max_tokens_forwarded -q --tb=short -W error::DeprecationWarning => 2 passed.

### Lint Results

- uv run ruff check src/owlbear/bootstrap/toolsets.py tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py => FAIL (6x RUF100 in tests/test_bootstrap.py lines 1975, 1996, 2017, 2675, 2767, 2869).

### Coverage

- pytest --cov unavailable in this environment (unrecognized --cov args).
- Fallback with coverage run + coverage report -m src/owlbear/bootstrap/toolsets.py => 56 percent (below 90 percent target).

### Pass 1 - Critical Checks

- Security review: no security issues found in reviewed diff.
- Test integrity: TestFromAC_BuildToolsetsNoBareModelDeprecation (3 tests) and test_build_toolsets_expansion_path_no_bare_model_deprecation are preserved (no changes in f1e3aa4..982062b).
- Test quality: assertion specificity STRONG, negative/error paths ADEQUATE, mutation reasoning ADEQUATE, independence STRONG, naming STRONG.
- Data safety: no data safety issues found.

### AC Compliance

- AC: zero deprecation warnings in test output.
- Evidence: AC-mapped run passed under -W error::DeprecationWarning (4 passed). Source fallback resolves str/None to Model and forwards resolved_model to infra/toolset/bookmark calls in src/owlbear/bootstrap/toolsets.py lines 88, 92, 102, 124, 149.
- Status: PASS.

### Verdict

- FAIL. Confidence .84 (below .90 threshold).
- Blocking reasons: lint gate failing (6 RUF100) and touched-module coverage measured at 56 percent (<90).

### Action Taken

- Returning task to todo with block reason for lint + coverage gaps.

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about code quality (6x RUF100 in tests/test_bootstrap.py) and weak test coverage (56% on toolsets.py) — not missing AC tests.
- Existing TestFromAC_BuildToolsetsNoBareModelDeprecation (3 tests) fully cover AC: zero deprecation warnings in test output.
- Existing tests preserved. Builder must fix RUF100 lint in tests/test_bootstrap.py and add TestBuilderDiscovered tests to bring toolsets.py coverage to >=90%.

[[2026-03-23]] Mon 04:26
## Builder Notes
- Files changed: tests/test_bootstrap.py (6 lines changed)
- Tests: 4 passed (TestFromAC_BuildToolsetsNoBareModelDeprecation x3 + test_build_toolsets_expansion_path_no_bare_model_deprecation x1), -W error::DeprecationWarning, 175 deselected
- Lint: ruff PASS (all checks passed on src/owlbear/bootstrap/toolsets.py tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py)
- Coverage: 99% on src/owlbear/bootstrap/toolsets.py (lines 218, 342 are minor edge branches)
- Fix applied: Removed 6 unused '#  noqa: N801' directives from TestFromAC_* class declarations in tests/test_bootstrap.py. N801 is already suppressed project-wide for tests via per-file-ignores, making the inline noqa redundant (RUF100).
- No src/ changes needed; toolsets.py implementation from prior builder pass is correct.

[[2026-03-23]] Mon 05:20
## Review Evidence
## Review: #556 - Fix PydanticAI deprecation warnings in tests

### Test Results
- Command: uv run pytest tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation tests/test_bootstrap.py::TestBuildToolsetsProjectScope::test_project_id_forwarded_to_knowledge_toolset tests/test_bootstrap.py::TestBuildToolsetsKnowledgeService::test_settings_max_tokens_forwarded -q --tb=short -W error::DeprecationWarning
- Result: 6 passed, 0 failed, 2 warnings (optional dependency skips in tests/conftest.py).
- Additional branch run: uv run pytest tests/test_bootstrap.py::TestBuildToolsets tests/test_bootstrap.py::TestBuildToolsetsEdgeCases tests/test_bootstrap.py::TestBuildToolsetsProjectScope tests/test_bootstrap.py::TestBuildToolsetsKnowledgeService tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_bootstrap.py::TestSharedKnowledgeInfra tests/test_knowledge_query_service_expansion.py::TestBootstrapRetrieverWiring tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation -q --tb=short -W error::DeprecationWarning
- Additional run result: 26 passed, 2 failed, 2 warnings; failures at tests/test_knowledge_query_service_expansion.py:593 and :624 (ValueError: too many values to unpack (expected 3)).

### Lint Results
- Command: uv run ruff check src/owlbear/bootstrap/toolsets.py tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py
- Result: All checks passed.

### Coverage
- Command: uv run pytest tests/test_bootstrap.py::TestBuildToolsets tests/test_bootstrap.py::TestBuildToolsetsEdgeCases tests/test_bootstrap.py::TestBuildToolsetsProjectScope tests/test_bootstrap.py::TestBuildToolsetsKnowledgeService tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_bootstrap.py::TestSharedKnowledgeInfra tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -W error::DeprecationWarning
- Result: src/owlbear/bootstrap/toolsets.py = 74%.
- Additional coverage run over nearby TestFromAC classes: src/owlbear/bootstrap/toolsets.py = 66%.
- Gate impact: touched implementation module remains below 90% target.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| Zero deprecation warnings in test output | tests/test_bootstrap.py:2885, 2906, 2941 (TestFromAC_BuildToolsetsNoBareModelDeprecation) + tests/test_knowledge_query_service_expansion.py:665 | Yes. Bare-string regression causes isinstance(Model) assertions to fail; targeted -W error::DeprecationWarning run also fails on warning regression. | COVERED |

#### Security Review
- No security vulnerabilities found in reviewed scope.

#### Test Integrity (TestFromAC comparison)
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_infra_receives_model_not_bare_string | No assertion/body change in f1e3aa4..f19b4ea; class-level noqa removed only | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_toolset_receives_model_not_bare_string | No assertion/body change in f1e3aa4..f19b4ea; class-level noqa removed only | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_bookmark_toolset_receives_model_not_bare_string | No assertion/body change in f1e3aa4..f19b4ea; class-level noqa removed only | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AC tests assert captured argument count and concrete Model type (tests/test_bootstrap.py:2901, 2936, 2970; tests/test_knowledge_query_service_expansion.py:715). |
| Negative/error paths | ADEQUATE | Existing file includes error-path TestFromAC classes for knowledge-toolset exception wiring; AC tests specifically guard deprecation regression path. |
| Mutation reasoning | ADEQUATE | Reverting to bare string would fail isinstance(Model) checks and deprecation-as-error run. |
| Test independence | STRONG | Tests use local patch contexts and isolated tmp_path fixtures. |
| Descriptive names | STRONG | Test names explicitly describe model-type/deprecation contract intent. |

#### Data Safety
- No data safety issues found in this task scope.

#### Implementation-Aware Test Gaps
- CRITICAL: Coverage for touched implementation module src/owlbear/bootstrap/toolsets.py remains 66-74% across focused coverage runs, below the 90% gate.
- Missing coverage spans multiple behavioral branches (example missing ranges from term-missing output: 49-63, 118, 133-135, 174, 204-206, 217-218, 321-328, 333-346, 381-398).
- Latest retry commit f19b4ea only removes unused noqa directives in tests/test_bootstrap.py and adds no new tests to close the module-level gap.

### Pass 2 - INFORMATIONAL
- Broader subset run surfaced two failures in tests/test_knowledge_query_service_expansion.py:593 and :624 (tuple unpack arity mismatch). These were not modified by retry commit f19b4ea but are relevant residual test debt in adjacent coverage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Zero deprecation warnings in test output | Targeted deprecation-as-error pytest command passes (6 passed, 0 failed) and AC tests assert Model instance routing in tests/test_bootstrap.py:2901, 2936, 2970 and tests/test_knowledge_query_service_expansion.py:715 | TestFromAC_BuildToolsetsNoBareModelDeprecation::* + test_build_toolsets_expansion_path_no_bare_model_deprecation | PASS |

### Verdict: FAIL
- Confidence: .94

### Action Taken
- kanban\kanban-md.exe edit 556 --status todo --release

[[2026-03-23]] Mon 06:17
## Test-Writer Notes (retry-2)
- Retry reason: second retry cycle — builder fixed RUF100 lint and coverage after first retry pass-through.
- Verified: 4 AC-mapped tests pass under -W error::DeprecationWarning.
- Verified: ruff clean on test files and toolsets.py.
- No new tests needed. Passing through to builder.

[[2026-03-23]] Mon 07:57
## Builder Notes (retry-3)
- Files changed: none — all implementation committed in prior passes (982062b, f19b4ea)
- Tests: 4 AC tests passed under -W error::DeprecationWarning (TestFromAC_BuildToolsetsNoBareModelDeprecation x3 + test_build_toolsets_expansion_path_no_bare_model_deprecation x1)
- Coverage: 99% on src/owlbear/bootstrap/toolsets.py (full tests/test_bootstrap.py run; only lines 218 and 342 uncovered - minor else-branches)
- Lint: ruff PASS on src/owlbear/bootstrap/toolsets.py, tests/test_bootstrap.py, tests/test_knowledge_query_service_expansion.py
- Note: prior reviewer saw 66-74% because they ran a narrow subset; the canonical measurement with the full test_bootstrap.py suite is 99%, exceeding the 90% gate
- Test-writer (retry-2) confirmed: no new tests needed, all AC covered

[[2026-03-23]] Mon 09:16
## Review Evidence
## Review: #556 - Fix PydanticAI deprecation warnings in tests

### Test Results
- Isolated AC run: `uv run pytest tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation tests/test_bootstrap.py::TestBuildToolsetsProjectScope::test_project_id_forwarded_to_knowledge_toolset tests/test_bootstrap.py::TestBuildToolsetsKnowledgeService::test_settings_max_tokens_forwarded -q --tb=short -W error::DeprecationWarning`
- Result: 6 passed, 0 failed, 2 warnings (optional dependency skips from tests/conftest.py).
- Isolated broad coverage run: `uv run pytest tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -W error::DeprecationWarning`
- Broad run result: 170 passed, 5 failed, 2 warnings. Failing tests are unrelated to #556 scope (slack extra missing + RED tests for #966 HookWorkerSupervisor seam).

### Lint Results
- Command: `uv run ruff check src/owlbear/bootstrap/toolsets.py tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py`
- Result: All checks passed.

### Coverage
- Broad run reports: `src/owlbear/bootstrap/toolsets.py` = 99% (missing lines 218, 342).
- Focused subset run for build_toolsets-related tests reports 74%; this is expected from narrower selection and excludes many existing toolsets branches.
- Gate decision for touched implementation uses broad run metric: PASS (>=90%).

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| Zero deprecation warnings in test output | tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation::{test_knowledge_infra_receives_model_not_bare_string,test_knowledge_toolset_receives_model_not_bare_string,test_bookmark_toolset_receives_model_not_bare_string}; tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation | Yes. Reintroducing bare string path fails `isinstance(Model)` assertions and fails with `-W error::DeprecationWarning`. | COVERED |

#### Security Review
- No hardcoded real secrets found (only literal placeholder API key for synthetic provider construction in test/edge path).
- No injection, traversal, unsafe deserialization, or sensitive log leakage found in changed logic (`src/owlbear/bootstrap/toolsets.py`).

#### Test Integrity (TestFromAC comparison)
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_infra_receives_model_not_bare_string | No assertion/body change; only class-level `# noqa: N801` removed in `f19b4ea` | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_toolset_receives_model_not_bare_string | No assertion/body change; only class-level `# noqa: N801` removed in `f19b4ea` | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_bookmark_toolset_receives_model_not_bare_string | No assertion/body change; only class-level `# noqa: N801` removed in `f19b4ea` | PRESERVED |
| test_build_toolsets_expansion_path_no_bare_model_deprecation | No change in `git diff f1e3aa4..f19b4ea -- tests/test_knowledge_query_service_expansion.py` | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AC tests assert concrete Model type and call-count expectations, not truthy/non-null checks. |
| Negative/error paths | ADEQUATE | AC is regression-focused on deprecation path; tests explicitly exercise fallback route that previously emitted warnings. |
| Mutation reasoning | STRONG | Reverting to `chat_model or settings.chat_model` bare string forwarding causes immediate assertion/deprecation failures. |
| Test independence | STRONG | Tests use local fixtures/mocks and isolated patch contexts. |
| Descriptive names | STRONG | Test names directly encode expected non-bare-model behavior. |

#### Data Safety
- No data integrity issues in reviewed change. The new `resolved_model` branch is in-memory wiring only and does not persist user input.

#### Implementation-Aware Test Gaps
- No significant untested paths found in changed block.
- Implementation diff (`982062b`) introduces `resolved_model` then routes it to `_build_knowledge_infra`, `_build_knowledge_toolset`, and `_build_bookmark_toolset` (`src/owlbear/bootstrap/toolsets.py`:102, 124, 149), all covered by AC-mapped tests.

### Pass 2 - INFORMATIONAL
- Broad bootstrap coverage run currently includes out-of-scope failures in other active workstreams:
  - `TestCreateChannelSlackSuccess::test_slack_channel_created` (missing optional `slack_sdk` extra).
  - `TestFromAC_BootstrapHookWorkerSupervisorWiring::*` failures from #966 RED state.
- These do not invalidate #556 AC evidence but remain residual suite noise outside this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Zero deprecation warnings in test output | Isolated deprecation-as-error run passed (6/6); implementation resolves fallback to Model and forwards `resolved_model` at `src/owlbear/bootstrap/toolsets.py`:66, 92, 102, 124, 149 | TestFromAC_BuildToolsetsNoBareModelDeprecation::* + test_build_toolsets_expansion_path_no_bare_model_deprecation | PASS |

### Verdict: PASS
- Confidence: .92

### Action Taken
- Advancing task to docs.

[[2026-03-23]] Mon 11:48
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal fix to private _wire_knowledge_toolsets(); no behavior/API/convention change visible to agents |
| 2 | Docstrings | Yes | Pass | _wire_knowledge_toolsets() has existing docstring + inline comment explaining model resolution; build_toolsets() public API signature unchanged |
| 3 | sources/overview.md | No | N/A | Fix uses PydanticAI's own OpenAIChatModel/OpenAIProvider classes; no new external code patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/pydanticai-deprecation-warnings.md exists and linked from task body |
| 6 | No impact | Yes | Pass | All items N/A or already accurate; no docs edits required |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/556-* files found)

[[2026-03-23]] Mon 12:45
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Zero deprecation warnings in test output | 4 AC tests pass with `-W error::DeprecationWarning` (4/4 PASSED); `resolved_model` at toolsets.py:92-97 converts bare string/None to `OpenAIChatModel`; forwarded at L102, L124, L149 | PASS |

### Test Results
- pytest (AC-scoped): `uv run pytest ... -W error::DeprecationWarning` -> 4 passed, 0 failed
- pytest (full suite): 3918 passed, 94 failed (pre-existing: numpy compat, slack_sdk, RED tests from #966 and other active tasks). No #556-related failures.
- ruff: all checks passed on src/owlbear/bootstrap/toolsets.py, tests/test_bootstrap.py, tests/test_knowledge_query_service_expansion.py

### Upstream Commits
- `982062b` fix: resolve chat_model fallback to Model instance in toolsets (#556, builder)
- `f19b4ea` fix: remove unused noqa:N801 directives from TestFromAC classes (#556, builder)
- Uncommitted diff in tests/test_bootstrap.py is formatting in #966 scope, not #556.

### Architect Quality
- AC specificity: measurable single criterion, testable via -W flag
- Edge case coverage: research notes filled gaps (MagicMock path, bare-string categories)
- Design direction: research doc guided builder accurately
- AC quality score: 4/5

### Reviewer Evidence
- Reviewer PASS at .92 confidence. Detailed AC compliance table, test integrity checks, security review, full coverage analysis (99% on toolsets.py with broad run). Evidence is thorough.

### Confidence: .96
### Action: archive
