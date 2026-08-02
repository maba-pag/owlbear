---
id: 60
title: Extend classify_error for ACP RequestError codes
status: archived
priority: medium
created: 2026-03-26 19:27:33.303189+01:00
updated: 2026-03-28 00:49:29.198957+01:00
started: 2026-03-28 00:49:24.397867+01:00
completed: 2026-03-28 00:49:24.397867+01:00
tags:
- phase-1
- scope:orchestrator
- type:build
depends_on:
- 71
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add ACP-specific error classification to classify_error() in v1/src/owlbear/core/errors.py.

## Acceptance Criteria
- [ ] Conditional import of acp.exceptions.RequestError following the existing openai pattern (try/except ImportError; set sentinel to None when absent)
- [ ] Module-level _ACP_ERROR_CODES: dict[int, ErrorCategory] mapping JSON-RPC codes to categories
- [ ] Code -32700 (Parse error) maps to PERMANENT
- [ ] Code -32600 (Invalid Request) maps to PERMANENT
- [ ] Code -32601 (Method not found) maps to PERMANENT
- [ ] Code -32602 (Invalid params) maps to PERMANENT
- [ ] Code -32603 (Internal error) maps to TRANSIENT
- [ ] Code -32000 (Auth required) maps to AUTH
- [ ] Code -32002 (Resource not found) maps to TOOL_SEMANTIC
- [ ] Unknown ACP error codes (not in dict) default to PERMANENT
- [ ] RequestError isinstance branch inserted after HTTPStatusError and before transient network block in classify_error()
- [ ] When acp is not installed, RequestError branch is skipped with no import error and no behavior change
- [ ] No code change for BrokenPipeError (already TRANSIENT via ConnectionError inheritance; test-only verification in test task)

## Context
See docs/research/classify-error-acp-extension.md and docs/research/acp-error-handling-strategy.md SS3.1, SS3.5.

## Architecture Notes
- Follow existing openai conditional import pattern in errors.py (try/except ImportError)
- Follow existing _TRANSIENT_HTTP_CODES / _AUTH_HTTP_CODES pattern for the code lookup dict
- Dict lookup + .get(code, PERMANENT) for the default
- ~30 LOC change; single isinstance branch + dict

[[2026-03-26]] Thu 20:18
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Conditional import of RequestError | Sound; follows existing openai pattern in errors.py L26-28 | Keep |
| _ACP_ERROR_CODES dict | Follows _TRANSIENT_HTTP_CODES/_AUTH_HTTP_CODES pattern | Keep |
| -32700: PERMANENT | Correct per JSON-RPC spec | Keep |
| -32600: PERMANENT | Added (was missing from original AC); correct per spec | Added |
| -32601: PERMANENT | Correct | Keep |
| -32602: PERMANENT | Correct | Keep |
| -32603: TRANSIENT | Correct; agent internal failure may recover | Keep |
| -32000: AUTH | Correct; maps to Copilot re-auth flow | Keep |
| -32002: TOOL_SEMANTIC | Correct; stale session, model can retry | Keep |
| Unknown codes: PERMANENT | Safe default; don't retry undefined errors | Keep |
| Branch position after HTTPStatusError | Correct priority order | Keep |
| acp not installed: no behavior change | Conditional import with None sentinel handles this | Keep |
| BrokenPipeError: test-only | Already TRANSIENT via ConnectionError (verified in errors.py L100) | Clarified |

### Architecture Notes
- Module layering: core/errors.py is the correct location per architecture-standards (error taxonomy lives in core/)
- No upward imports: acp.exceptions is a third-party dep, not an OwlBear layer violation
- Pattern: conditional import matches openai pattern (L26-28); dict lookup matches HTTP code sets (L62-63)
- Single isinstance branch + dict.get() gives ~30 LOC change with no structural disruption
- Research found -32600 gap in original AC; now included

### Changes Made
- Refined AC: added -32600 mapping, specified conditional import approach, clarified BrokenPipeError is test-only, specified unknown-code default, added architecture notes
- Created test task #71 (Test: Extend classify_error for ACP RequestError codes) at todo
- Added dependency: #60 depends on #71

### Dependencies
- Added: #71 (test task, TDD RED) must complete before #60
- Verified: no other task dependencies needed; errors.py has no pending changes

[[2026-03-27]] Fri 13:45
## Test-Writer Notes
- RED phase BLOCKED: implementation pre-committed in 7356422 before RED phase ran.
- All AC items covered by TestFromAC_AcpErrors + TestBuilderDiscovered in v1/tests/test_error_classification.py (51 tests, all PASS, ruff clean).
- No new tests written; no source files touched.
- Recommend: advance #60 directly to review (builder commit already GREEN).

[[2026-03-27]] Fri 16:34
## Builder Notes
- Files changed: None. ACP RequestError mapping was already implemented in v1 src owlbear core errors.py before this builder pass.
- Tests: 51 passed. Coverage on src owlbear core errors.py is 86 percent.
- Lint: ruff clean on scoped files.
- Evidence: Scoped pytest on v1 tests test_error_classification.py reports 51 passed. Scoped coverage reports errors.py 74 statements and 10 misses. Scoped ruff check reports all checks passed.
- Fixes applied: None. This pass validated existing behavior against AC and verified no regression for BrokenPipeError handling.

[[2026-03-27]] Fri 18:51
## Review Evidence
### Review
Task 60: Extend classify_error for ACP RequestError codes

### Test Results
- Scoped pytest in v1: 51 passed, 0 failed, 0 skipped in 1.67s.
- ACP import was available in the v1 environment, so the ACP RequestError cases executed rather than skipping.

### Lint Results
- Task-scoped ruff on v1/src/owlbear/core/errors.py and v1/tests/test_error_classification.py was clean.

### Coverage
- v1/src/owlbear/core/errors.py: 86 percent in the scoped run.
- This scoped whole-file percentage includes unrelated branches; ACP-specific behavior was verified by exact tests and code inspection.

### Pass 1 Critical
#### Test-Writer AC Coverage
- Conditional import of RequestError: v1/src/owlbear/core/errors.py L32-L35 and TestBuilderDiscovered::test_module_reloads_without_acp_installed; would fail if the optional import or sentinel handling broke; COVERED.
- Module-level ACP code map: v1/src/owlbear/core/errors.py L91-L99; ACP code-specific tests below exercise the lookup table; COVERED.
- Code -32700 maps to PERMANENT: TestFromAC_AcpErrors::test_parse_error_is_permanent; COVERED.
- Code -32600 maps to PERMANENT: TestFromAC_AcpErrors::test_invalid_request_is_permanent; COVERED.
- Code -32601 maps to PERMANENT: TestFromAC_AcpErrors::test_method_not_found_is_permanent; COVERED.
- Code -32602 maps to PERMANENT: TestFromAC_AcpErrors::test_invalid_params_is_permanent; COVERED.
- Code -32603 maps to TRANSIENT: TestFromAC_AcpErrors::test_internal_error_is_transient; COVERED.
- Code -32000 maps to AUTH: TestFromAC_AcpErrors::test_auth_required_is_auth; COVERED.
- Code -32002 maps to TOOL_SEMANTIC: TestFromAC_AcpErrors::test_resource_not_found_is_tool_semantic; COVERED.
- Unknown ACP codes default to PERMANENT: TestFromAC_AcpErrors::test_unknown_code_is_permanent; COVERED.
- RequestError branch sits after HTTPStatusError and before transient network handling: v1/src/owlbear/core/errors.py L121-L129; structural code inspection confirms the required order; COVERED.
- When acp is not installed, the branch is skipped with no import error and no behavior change: TestFromAC_AcpErrors::test_acp_not_installed_graceful_degradation plus TestBuilderDiscovered::test_module_reloads_without_acp_installed; COVERED.
- BrokenPipeError behavior remains unchanged: v1/src/owlbear/core/errors.py L129-L130 and TestFromAC_AcpErrors::test_broken_pipe_is_transient; COVERED.

#### Security Review
- No security issues found. The change is limited to an optional import, a constant dict, and a pure in-memory classifier branch.

#### Test Integrity
- Compared HEAD against commit 4f3361837a6be07add190147f02c8b77d28313dc, which introduced TestFromAC_AcpErrors.
- Preserved unchanged: test_parse_error_is_permanent, test_invalid_request_is_permanent, test_method_not_found_is_permanent, test_invalid_params_is_permanent, test_internal_error_is_transient, test_auth_required_is_auth, test_resource_not_found_is_tool_semantic, test_unknown_code_is_permanent, test_broken_pipe_is_transient, test_acp_not_installed_graceful_degradation.
- Strengthened later by commit 86baf42d451297769cdcf4973ab0cb6e73918f53 adding TestBuilderDiscovered::test_module_reloads_without_acp_installed.
- No weakened or removed TestFromAC coverage.

#### Test Quality
- Assertion specificity: STRONG. Each ACP test asserts the exact ErrorCategory value.
- Negative and error paths: STRONG. Unknown code, no-ACP graceful degradation, and BrokenPipeError regression coverage are present.
- Mutation reasoning: STRONG. Changing any ACP mapping or the default classification would fail a named ACP test.
- Test independence: STRONG. Tests create fresh exceptions and use local patch scopes only.
- Descriptive names: STRONG. Test names describe the scenario and expected category.

#### Data Safety
- No data safety issues found. No persistence, concurrency, or unbounded-input behavior changed.

#### Implementation-Aware Test Gaps
- No significant untested paths. The implementation adds one optional import, one code map, one ACP branch, and the no-ACP reload path is explicitly tested.

### Pass 2 Informational
- No informational findings.

### AC Compliance
- All 13 acceptance criteria pass. The Test-Writer AC Coverage section above contains the exact evidence mapping.

### Verdict
- PASS. Confidence .96.

### Action Taken
- Appended review evidence, moved the task to docs, and released the reviewer claim.

[[2026-03-28]] Sat 00:49
## Audit
### AC Verification
- Conditional import of AcpRequestError: L32-L35, try/except ImportError with None sentinel. PASS
- _ACP_ERROR_CODES dict: L91-L99, 7 entries. PASS
- -32700 PERMANENT: L92. PASS
- -32600 PERMANENT: L93. PASS
- -32601 PERMANENT: L94. PASS
- -32602 PERMANENT: L95. PASS
- -32603 TRANSIENT: L96. PASS
- -32000 AUTH: L97. PASS
- -32002 TOOL_SEMANTIC: L98. PASS
- Unknown codes default PERMANENT: L129 .get(exc.code, ErrorCategory.PERMANENT). PASS
- Branch after HTTPStatusError, before transient network: L128-L129 between L126 and L131. PASS
- acp not installed graceful degradation: L128 guard AcpRequestError is not None. PASS
- BrokenPipeError unchanged: L131 ConnectionError inheritance. PASS

### Test Results
- pytest: 51 passed, 0 failed (v1/tests/test_error_classification.py, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 --noconftest)
- ruff: all checks passed (v1/src/owlbear/core/errors.py, v1/tests/test_error_classification.py)

### Upstream Commits
- 4f33618 test: add failing tests for ACP RequestError classification (#71, test-writer)
- 7356422 feat: classify ACP RequestError codes (#71, builder)
- 86baf42 test: harden no-acp reload coverage (#71, builder)

### AC Quality Score: 5/5
AC was specific, complete, and led to a clean implementation. Architect added missing -32600 code and provided clear design direction.

### Confidence: .97
### Action: archive
