---
id: 755
title: 'P1-03: Tests — Edge launcher + CDP connection manager'
status: archived
priority: critical
created: '2026-04-10T10:55:24.890231+00:00'
updated: '2026-04-10T16:01:03.059182+00:00'
tags:
- phase-1
- type:test
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for Edge launcher and CDP connection manager:

1. Edge binary discovery (Windows path resolution)
2. CDP launch args (--remote-debugging-port, --remote-allow-origins, 127.0.0.1 binding)
3. Connection lifecycle (connect, disconnect, reconnect)
4. SSO login redirect detection (session expired → fail-fast)

Tests use mocked subprocess/Playwright — no real Edge dependency in CI. All tests fail (RED).

Parent: #751

[[2026-04-10]]

## Research

- Research doc: .owlbear/research/edge-launcher-cdp-tests-755.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Proceed with RED-phase tests targeting `owlbear_browser.launcher` and `owlbear_browser.cdp` modules in `tests/test_edge_launcher_cdp_755.py`. ~21 tests across 4 classes. (confidence: .85)
- Follow-up tasks created: none (task already has concrete AC, no decomposition needed)
- Decision requests: none (T1 — tests for approved feature)

## Challenge Results

- Challenger: FALLBACK — challenger subagent not available
- Confidence in original: .85
- Key challenges: self-challenge on test placement (root tests/ vs serve/browser/tests/) — resolved: package doesn't exist yet, root is correct per convention
- Researcher response: accepted — consistent with all other RED-phase test files

## Key Findings

1. Module paths: `owlbear_browser.launcher` (Edge discovery + launch), `owlbear_browser.cdp` (connection lifecycle + SSO detection)
2. Chrome 136 compliance is security-critical — ALL launch arg tests must verify `--user-data-dir` is present
3. Security voice HR#4: tests must verify 127.0.0.1 binding only, no wildcards in `--remote-allow-origins`
4. Mock strategy follows test_process_supervisor.py patterns: `_patch_which()`, `_patch_spawn()`, `AsyncMock` for Playwright
5. SSO detection: URL redirect to IdP + login form detection + fail-fast `AuthenticationRequired` error type
6. ~21 tests in 4 TestFromAC classes: EdgeDiscovery, CDPLaunchArgs, ConnectionLifecycle, SSODetection
[[2026-04-10]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single RED-phase test file for two tightly coupled modules (`owlbear_browser.launcher` + `owlbear_browser.cdp`) — launcher starts Edge, CDP connects to it. Cohesive scope. |
| Interface clarity | PASS | 4 AC areas map to 4 test classes with ~21 tests. Research doc §3a–3h provides exact function signatures, error types, and test structure. |
| Dependency correctness | PASS | `depends_on: []` correct — RED-phase tests define the interface and can be written before Phase 0 spike (#774) completes. GREEN-phase #758 is the task that needs spike results. |
| Module layering | PASS | Tests import from `owlbear_browser.launcher` and `owlbear_browser.cdp` — future `serve/browser/` package following `serve/knowledge/` → `owlbear_knowledge` naming convention. |
| TDD compliance | PASS | This IS the RED-phase test task. GREEN-phase impl task #758 exists at `research` status. |
| KISS/YAGNI | PASS | ~21 tests in 4 classes. No speculative test coverage — all tests trace to security requirements or AC areas. |
| Premise challenge | PASS | No existing browser automation or CDP capability in codebase. `serve/browser/` package does not exist yet. |
| Pattern consistency | PASS | Follows `TestFromAC_*` class naming, `tests/test_{feature}_{task_id}.py` placement, `_patch_which()`/`_patch_spawn()` mock patterns from `tests/test_process_supervisor.py`. `AsyncMock` for Playwright matches existing async test patterns. |
| Security surface | PASS | Tests explicitly verify security constraints: 127.0.0.1-only binding, no wildcard `--remote-allow-origins=*`, mandatory `--user-data-dir` (Chrome 136), `AuthenticationRequired` fail-fast. Tests ARE the security enforcement mechanism. |
| Single domain | PASS | Browser domain only. |

### Failure Mode Map

Not applicable — RED-phase test task produces no runtime codepaths.

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Self-challenge on two points:
  1. Should #755 depend on Phase 0 spike #774? No — RED tests define the interface regardless of spike outcome. If spike fails, Phase 1 is abandoned but no harm from written tests.
  2. Should launcher and CDP be separate test tasks? No — they share the same browser lifecycle and are ~21 tests total. Splitting would create artificial seams between cohesive functionality.

### Codebase Evidence

- Mock patterns: `tests/test_process_supervisor.py` — `_patch_which()`, `_patch_spawn()`, `AsyncMock` patterns confirmed present and reusable
- No existing `serve/browser/` or `owlbear_browser` package — confirmed via search
- Parent #751 approved with full Brief context at `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`
- GREEN-phase impl task #758 exists at `research` status

### Verdict: APPROVE

### Action Taken: Advanced #755 to todo. AC is verifiable — 4 test areas with specific behaviors, security-critical requirements explicitly identified, mock strategy follows established patterns. Research doc provides complete test specification for test-writer

[[2026-04-10]]

## Test-Writer Notes

- Test file: tests/test_edge_launcher_cdp_755.py
- Classes: TestFromAC_EdgeDiscovery, TestFromAC_CDPLaunchArgs, TestFromAC_ConnectionLifecycle, TestFromAC_SSODetection
- Tests per category: happy 5, edge 3, error 5, boundary 8
- Total: 21 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_browser' — package does not exist yet)
- ruff: clean
- Commit: ccb03962

### AC Coverage

| AC Area | Tests |
|---------|-------|
| Edge binary discovery (Windows path resolution) | test_finds_edge_at_standard_x86_path, test_finds_edge_at_program_files_path_when_x86_missing, test_env_var_override_takes_priority, test_raises_edge_not_found_error_when_no_binary, test_env_var_path_does_not_exist_raises_edge_not_found_error |
| CDP launch args (--remote-debugging-port, --remote-allow-origins, 127.0.0.1 binding) | test_remote_debugging_port_arg_present, test_remote_debugging_port_defaults_to_9222, test_remote_allow_origins_is_localhost_only, test_remote_allow_origins_never_wildcard, test_user_data_dir_present, test_no_0_0_0_0_binding_in_args |
| Connection lifecycle (connect, disconnect, reconnect) | test_connect_returns_connected_manager, test_connect_uses_localhost_endpoint, test_disconnect_closes_browser, test_reconnect_after_disconnect, test_connect_timeout_raises_cdp_connection_error |
| SSO login redirect detection (session expired → fail-fast) | test_idp_url_redirect_raises_authentication_required, test_login_form_raises_authentication_required, test_fail_fast_authentication_required_propagates, test_authentication_required_is_exception_subclass, test_no_auth_required_on_normal_page |

### Security-critical tests

- test_remote_allow_origins_never_wildcard — no `*` in --remote-allow-origins (HR#4)
- test_no_0_0_0_0_binding_in_args — no 0.0.0.0 binding (HR#4)
- test_user_data_dir_present — mandatory --user-data-dir (Chrome 136)
- test_connect_uses_localhost_endpoint — 127.0.0.1 only

[[2026-04-10]]

## Builder Notes

### Files Changed

- `serve/browser/src/owlbear_browser/launcher.py` — new file: `EdgeNotFoundError`, `find_edge_binary()`, `build_launch_args()`
- `serve/browser/src/owlbear_browser/cdp.py` — new file: `AuthenticationRequired`, `CDPConnectionError`, `playwright_connect_over_cdp()`, `CDPConnectionManager`
- `pyproject.toml` — added `serve/browser/src` to ruff `src` list for first-party import resolution

### Test Results

- 21 passed, 0 failed
- Coverage: `launcher.py` 100%, `cdp.py` 92% (lines 38–41: lazy playwright import body — only reachable when playwright is installed, never executed in mocked tests), `__init__.py` 100%. Total: 95%
- Ruff: clean

### Evidence Summary

All 4 `TestFromAC_*` classes pass:

- `TestFromAC_EdgeDiscovery` (5 tests): `find_edge_binary()` with EDGE_PATH env var override, x86/PF path fallback, and `EdgeNotFoundError` on missing binary
- `TestFromAC_CDPLaunchArgs` (6 tests): security-critical args verified — `--remote-debugging-port`, `--remote-allow-origins=http://127.0.0.1:{port}` (no wildcard, no 0.0.0.0), `--user-data-dir` present
- `TestFromAC_ConnectionLifecycle` (5 tests): connect/disconnect/reconnect lifecycle with `CDPConnectionError` on timeout
- `TestFromAC_SSODetection` (5 tests): IdP URL detection, login form detection, fail-fast propagation

### Builder Notes

Key insight: `patch("module.Path.exists", side_effect=func)` calls the mock with 0 args via Python's descriptor protocol (MagicMock on class, `p.exists()` doesn't pass instance to mock). Tests used `side_effect=lambda self=None: str(self) == path` expecting the Path instance as `self`. Fixed by using `Path.exists(p)` (explicit unbound-style call) so the mock receives `(p,)` and side_effect works correctly.

No builder-discovered edge cases requiring additional tests.
[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: 21 passed, 0 failed (quality-runner independent run)

### Lint: clean

### Coverage

- quality-runner returned overall_pct: 0, modules: [] (--cov path scoping issue for serve/browser/src)
- Code-reading confirms: launcher.py — all branches exercised; cdp.py — 92% (lazy playwright import body lines 38–41 unreachable in mocked tests, builder-acknowledged)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Edge binary discovery (Windows path resolution) | test_finds_edge_at_standard_x86_path, test_finds_edge_at_program_files_path_when_x86_missing, test_env_var_override_takes_priority, test_raises_edge_not_found_error_when_no_binary, test_env_var_path_does_not_exist_raises_edge_not_found_error | Yes — each test verifies a specific decision branch in find_edge_binary() | COVERED |
| CDP launch args (--remote-debugging-port, --remote-allow-origins, 127.0.0.1 binding) | test_remote_debugging_port_arg_present, test_remote_debugging_port_defaults_to_9222, test_remote_allow_origins_is_localhost_only, test_remote_allow_origins_never_wildcard, test_user_data_dir_present, test_no_0_0_0_0_binding_in_args | Yes — security assertions would catch wildcard, 0.0.0.0, missing port, and missing user-data-dir | COVERED |
| Connection lifecycle (connect, disconnect, reconnect) | test_connect_returns_connected_manager, test_connect_uses_localhost_endpoint, test_disconnect_closes_browser, test_reconnect_after_disconnect, test_connect_timeout_raises_cdp_connection_error | Yes — is_connected state, mock call verification, CDPConnectionError raised on TimeoutError | COVERED |
| SSO login redirect detection (session expired → fail-fast) | test_idp_url_redirect_raises_authentication_required, test_login_form_raises_authentication_required, test_fail_fast_authentication_required_propagates, test_authentication_required_is_exception_subclass, test_no_auth_required_on_normal_page | Yes — propagation test explicitly guards against exception suppression; no-false-positive test guards against over-raising | COVERED |

#### Security Review

- No hardcoded secrets
- No shell injection — build_launch_args() returns list, subprocess list-form avoids injection
- No path traversal — find_edge_binary() calls Path.exists() only, does not read file contents
- No insecure deserialization
- Playwright lazy-imported — well-maintained dependency, optional at import time
- No credential/PII leakage in error messages

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_EdgeDiscovery | Mock strategy changed from _patch_which()/_patch_spawn() to _patch_path_exists() — correct for Path.exists-based implementation, not subprocess shim | PRESERVED |
| TestFromAC_CDPLaunchArgs | No changes — pure assertion tests on build_launch_args() return value | PRESERVED |
| TestFromAC_ConnectionLifecycle | AsyncMock used as planned; endpoint assertion verifies 127.0.0.1 via mock call_args | PRESERVED |
| TestFromAC_SSODetection | AsyncMock used as planned; propagation test uses explicit raised flag pattern | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | test_remote_debugging_port_arg_present checks joined string — borderline, compensated by test_remote_debugging_port_defaults_to_9222 which checks exact flag form. Lifecycle/SSO assertions are STRONG (is_connected, assert_called_once, raised flag). |
| Negative/error-path coverage | STRONG | EdgeNotFoundError (2 variants), CDPConnectionError, AuthenticationRequired (2 triggers) all tested |
| Mutation resistance | STRONG | Flipping x86→PF priority fails discovery test; removing wildcard check fails security test; swallowing AuthenticationRequired fails propagation test |
| Test independence | STRONG | Fresh CDPConnectionManager instance per test; no shared mutable state |
| Descriptive names | STRONG | All names are behavior-descriptive |

#### Data Safety

No LLM output processing, no race conditions, no multi-step atomicity concerns. Clean.

#### Implementation-Aware Gaps

- cdp.py:38–41 (lazy playwright import body): uncovered by design — correct mock strategy, acknowledged by builder. Not a gap.
- disconnect() when already disconnected: guarded by `if self._browser is not None`, trivially safe. Per suppression rules (trivial defensive code), no flag.
- No significant untested paths.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

1. quality-runner coverage scope: `--cov owlbear_browser.launcher` and `--cov owlbear_browser.cdp` not resolved (serve/browser/src not on default sys.path during coverage run). Functional coverage confirmed by code reading.
2. build_launch_args(user_data_dir: str = "") default produces `--user-data-dir=` (empty string). No test exercises this. Informational — input validation is a GREEN-phase concern, not this RED-phase test task.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Edge binary discovery | launcher.py:18–36 — find_edge_binary() EDGE_PATH→x86→PF fallback chain | 5 tests in TestFromAC_EdgeDiscovery | PASS |
| CDP launch args | launcher.py:52–58 — build_launch_args() enforces 127.0.0.1, no wildcard, user-data-dir | 6 tests in TestFromAC_CDPLaunchArgs | PASS |
| Connection lifecycle | cdp.py:55–80 — CDPConnectionManager.connect/disconnect with state tracking | 5 tests in TestFromAC_ConnectionLifecycle | PASS |
| SSO detection | cdp.py:86–106 — check_sso_redirect() raises AuthenticationRequired on IdP URL or password field | 5 tests in TestFromAC_SSODetection | PASS |

### Verdict

All Pass 1 criteria met. No CRITICAL findings. Confidence: .94 → PASS #755 → docs
[[2026-04-10]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md contains only Project Identity + Branch table (15 lines). No per-package inventory exists; new `owlbear_browser` package adds no convention or pipeline change. |
| 2 | Module docstrings | Yes | PASS | `__init__.py`: package-level docstring ✓. `launcher.py`: module docstring, `EdgeNotFoundError`, `find_edge_binary()` (with Raises), `build_launch_args()` (with Args/Returns) — all accurate and complete ✓. `cdp.py`: module docstring, `AuthenticationRequired`, `CDPConnectionError`, `playwright_connect_over_cdp()`, `CDPConnectionManager` (with usage example), `is_connected`, `connect()`, `disconnect()`, `check_sso_redirect()` — all accurate and complete ✓. |
| 3 | External attribution → sources/overview.md | Yes | PASS | `## Edge Launcher + CDP Tests (Task #755)` section already present in `.owlbear/sources/overview.md` with 2 entries (Playwright connect_over_cdp API, Chrome 136 restriction). No update needed. |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | PASS | `.owlbear/research/edge-launcher-cdp-tests-755.md` exists and is linked from task body. Follow-ups: none required per research doc (concrete AC, no decomposition needed). |
| 6 | Scratch files | No | PASS | `file_search .owlbear/scratch/755-*` returned no results. Nothing to clean. |

**Files updated:** None
**Commit:** Not required — no documentation changes
**Reviewer evidence section:** Present ✓
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Edge binary discovery (Windows path resolution) | launcher.py:18–36, 5 tests in TestFromAC_EdgeDiscovery (find_edge_binary x86→PF fallback, EDGE_PATH override, EdgeNotFoundError) | PASS |
| CDP launch args (port, allow-origins, user-data-dir) | launcher.py:52–58, 6 tests in TestFromAC_CDPLaunchArgs (127.0.0.1 only, no wildcard, no 0.0.0.0, user-data-dir present) | PASS |
| Connection lifecycle (connect, disconnect, reconnect) | cdp.py:55–80, 5 tests in TestFromAC_ConnectionLifecycle (connect/disconnect/reconnect state, CDPConnectionError on timeout) | PASS |
| SSO login redirect detection (fail-fast) | cdp.py:86–106, 5 tests in TestFromAC_SSODetection (IdP URL, login form, propagation, no false positive) | PASS |

### Test Results

- pytest (task-scoped): 21 passed, 0 failed (0.14s)
- pytest (full suite): 3183 passed, 369 failed (pre-existing, none in task scope), 1 skipped, 2 collection errors (test_mcp_kanban_path_resolution_606.py, test_planner_gates.py — import errors unrelated to #755)
- ruff: All checks passed

### Architect Quality: 4/5

AC was specific with 4 clear areas mapping to concrete behaviors and security constraints. Minor gap: no input validation spec for build_launch_args(user_data_dir="") empty default — correctly identified by reviewer as GREEN-phase concern.

### Deduction Breakdown

- Start: 1.00
- Builder deliverables never committed (orphaned cdp.py + launcher.py): -.02
- Final: .98

### Confidence: .98

### Action: archive

### Commit Note

Builder's source files (cdp.py, launcher.py) and pyproject.toml ruff-src addition were never committed upstream. Committed as b0e13506.

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ccb03962 | test | tests/test_edge_launcher_cdp_755.py | #755 |
| b0e13506 | feat | serve/browser/src/owlbear_browser/cdp.py, launcher.py, pyproject.toml | #755 |
