---
id: 758
title: 'P1-04: Impl — Edge launcher + CDP connection manager'
status: archived
priority: medium
created: '2026-04-10T10:55:57.179743+00:00'
updated: '2026-04-10T16:42:09.868675+00:00'
tags:
- phase-1
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. `serve/browser/` package:

- launcher.py: find Edge binary, launch with CDP args
- cdp_manager.py: connect/disconnect lifecycle, login redirect detection
- CDP binds exclusively to 127.0.0.1

All P1-03 (#755) tests pass. Depends on CDP spike go-ahead (#753).

Parent: #751

[[2026-04-10]]

## Research

- Research doc: .owlbear/research/edge-launcher-cdp-impl-758.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Block until prerequisites clear; Approach A (subprocess + connect_over_cdp) confirmed as correct implementation pattern (confidence: .82)
- Follow-up tasks created: none (prerequisite chain already exists: #776 → #753 → #755 → #758)
- Decision requests: none (T1 — implementation of approved architecture)

## Challenge Results

- Challenger: FALLBACK — no controversial recommendation; binary dependency-chain assessment
- Confidence in original: .82
- Key challenges: N/A
- Researcher response: N/A

## Key Findings

1. Dependency chain incomplete: #776 (spike script, research) → #753 (spike execution, blocked) → #755 (RED tests, backlog) → #758 (this task)
2. Package structure validated: `serve/browser/src/owlbear_browser/` with launcher.py + cdp.py + _errors.py
3. Approach A (subprocess launch + Playwright connect_over_cdp) confirmed — matches spike design, maximizes diagnostic control, tests designed against this API
4. Security constraints documented: 127.0.0.1 binding, no wildcard origins, mandatory --user-data-dir (Chrome 136), async context manager cleanup
5. Workspace integration checklist: ruff src, coverage source_pkgs, package boundary ALLOWED_IMPORTS all need updates
6. No new tasks needed — prerequisite chain is correctly sequenced
[[2026-04-10]]

## Architecture Review

### AC Refinement

Original body has vague descriptions, not testable AC. Module naming inconsistency (`cdp_manager.py` in body vs `cdp.py` in all research and #755 test spec). Missing `depends_on` encoding. Refined AC below supersedes original bullet points for the builder.

**Refined AC (builder-binding):**

1. `serve/browser/pyproject.toml` exists — `name = "owlbear-browser"`, dependency on `playwright`, hatchling build, `packages = ["src/owlbear_browser"]`
2. `serve/browser/src/owlbear_browser/launcher.py` — exports `find_edge_binary()`, `launch_edge()`, `build_launch_args()`
3. `serve/browser/src/owlbear_browser/cdp.py` — exports `CDPConnectionManager` (async context manager with `__aenter__`/`__aexit__`)
4. `serve/browser/src/owlbear_browser/_errors.py` — exports `EdgeNotFoundError`, `CDPConnectionError`, `AuthenticationRequired`
5. `serve/browser/src/owlbear_browser/__init__.py` — re-exports public API from launcher, cdp, _errors
6. All #755 RED-phase tests pass (`tests/test_edge_launcher_cdp_755.py`)
7. Root `pyproject.toml` `tool.ruff.src` includes `"serve/browser/src"`
8. Root `pyproject.toml` `tool.coverage.run.source_pkgs` includes `"owlbear_browser"`
9. `tests/test_package_boundary.py` `ALLOWED_IMPORTS` includes `"owlbear_browser": set()` (zero owlbear-namespace deps)
10. Security: CDP binds to `127.0.0.1` only (`--remote-allow-origins=http://127.0.0.1:{port}`), `--user-data-dir` always present in launch args (Chrome 136), no wildcard origins
11. All exit paths clean up Edge subprocess via async context manager `__aexit__`

**CORRECTION**: Body says `cdp_manager.py` — builder MUST use `cdp.py` per #755 test imports and research doc §3.2.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Launcher + CDP manager are tightly coupled (launcher starts Edge, CDP connects to it). Cohesive scope. |
| Interface clarity | PASS | Refined AC above specifies module paths, function names, error types. #755 tests define exact expected behavior. |
| Dependency correctness | FLAG | `depends_on: []` must be corrected to `[755]`. #755 (RED tests) must complete before GREEN phase. **Manual fix required — edit_task not available in this session.** |
| Module layering | PASS | `owlbear_browser` has zero owlbear-namespace deps. Follows `serve/knowledge/` naming convention. Package boundary test entry: `set()`. |
| TDD compliance | PASS | #755 (RED, at todo) precedes this GREEN task. |
| KISS/YAGNI | PASS | Minimal scope: launcher + CDP connection + 3 error types. No speculative features. |
| Premise challenge | PASS | No existing browser/CDP capability in codebase. `serve/browser/` confirmed absent. |
| Pattern consistency | PASS | Follows `ProcessSupervisor` pattern (async CM, subprocess lifecycle, `FileNotFoundError` on missing binary). `_errors.py` follows error taxonomy convention. |
| Security surface | PASS | All security constraints from Brief HR#4 encoded in refined AC lines 10-11 and verified by #755 tests (TestFromAC_CDPLaunchArgs). |
| Single domain | PASS | Browser domain only. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Edge binary search | Binary not found at any path | `EdgeNotFoundError` | Yes (AC#4, #755 tests) | Clear "install Edge" error |
| CDP launch | Port already in use | subprocess error | Yes (builder wraps as `CDPConnectionError`) | Retry or clear error |
| CDP connect | Timeout (30s) | `TimeoutError` | Yes (#755 tests ConnLifecycle) | Retry with clear message |
| CDP connect | Connection refused | `ConnectionRefusedError` | Yes (#755 tests ConnLifecycle) | Clear error |
| SSO detection | Redirect to IdP | `AuthenticationRequired` | Yes (AC#4, #755 tests SSODetection) | "Re-login in Edge" message |
| Process cleanup | Edge subprocess leak on error | zombie process | Yes (AC#11 async CM `__aexit__`) | None if cleanup works |

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Self-challenge on two points:
  1. Should this APPROVE despite broken `depends_on`? Yes — the dependency is flagged for manual correction and the pipeline won't dispatch this until #755 completes (orchestrator re-plans from board state; #755 is at todo, #758 would be at todo behind it).
  2. Is the `cdp_manager.py` vs `cdp.py` inconsistency severe enough to REJECT? No — the refined AC explicitly corrects this. Builder reads the architecture review section.

### Codebase Evidence

- `ProcessSupervisor` pattern: `serve/orchestrator/src/owlbear_orchestrator/process_supervisor.py` — async CM, `shutil.which`, `FileNotFoundError` on missing binary
- `pyproject.toml` ruff.src (L38-45): needs `"serve/browser/src"` entry
- `pyproject.toml` coverage.source_pkgs (L130-139): needs `"owlbear_browser"` entry
- `tests/test_package_boundary.py` ALLOWED_IMPORTS (L43-50): needs `"owlbear_browser": set()` entry
- `serve/knowledge/pyproject.toml`: reference for package structure (hatchling build)
- No `serve/browser/` directory exists — confirmed via search

### Action Items

1. **MANDATORY**: `depends_on` must be set to `[755]` before builder picks this up. Orchestrator or human must use `edit_task`.
2. Builder must follow refined AC above (not original body bullets). Module is `cdp.py`, not `cdp_manager.py`.
3. Research doc `.owlbear/research/edge-launcher-cdp-impl-758.md` §3.4-3.5 provides implementation details.

### Verdict: APPROVE (with dependency fix flag)

### Action Taken: Advanced #758 to todo. Refined AC in this note. Flagged mandatory `depends_on: [755]` correction

[[2026-04-10]]

## Test-Writer Notes

- Test file: tests/test_edge_launcher_cdp_758.py
- Classes: TestFromAC_PackagePyproject, TestFromAC_LaunchEdge, TestFromAC_AsyncContextManager, TestFromAC_PublicAPI, TestFromAC_WorkspaceConfig
- Tests per category: happy 9, edge 4, error 6, boundary 2 (config/structural 10)
- Total: 31 tests, all FAIL
- ruff: clean

AC coverage:

| AC# | Description | Tests |
|-----|-------------|-------|
| AC#1 | serve/browser/pyproject.toml structure | TestFromAC_PackagePyproject (5 tests) |
| AC#2 | launch_edge() function exports + behavior | TestFromAC_LaunchEdge (8 tests) |
| AC#3 | CDPConnectionManager async context manager | TestFromAC_AsyncContextManager (7 tests) |
| AC#5 | **init**.py public API re-exports | TestFromAC_PublicAPI (7 tests) |
| AC#6 | Covered by #755 (not duplicated) | — |
| AC#7 | ruff.src includes serve/browser/src | TestFromAC_WorkspaceConfig (1 test) |
| AC#8 | coverage source_pkgs includes owlbear_browser | TestFromAC_WorkspaceConfig (1 test) |
| AC#9 | ALLOWED_IMPORTS includes owlbear_browser: set() | TestFromAC_WorkspaceConfig (2 tests) |
| AC#10 | Covered by #755 CDPLaunchArgs tests | — |
| AC#11 | **aexit** terminates subprocess on all exit paths | TestFromAC_AsyncContextManager (2 tests) |

Failure summary:

- TestFromAC_PackagePyproject: FileNotFoundError (serve/browser/ not yet created)
- TestFromAC_LaunchEdge, AsyncContextManager, PublicAPI: ModuleNotFoundError (owlbear_browser not installed)
- TestFromAC_WorkspaceConfig: AssertionError (config entries missing from pyproject.toml and test_package_boundary.py)

[[2026-04-10]]

## Builder Notes

### Files Changed (7)

- `serve/browser/src/owlbear_browser/_errors.py` — NEW: shared error types (`EdgeNotFoundError`, `CDPConnectionError`, `AuthenticationRequired`)
- `serve/browser/src/owlbear_browser/launcher.py` — NEW `launch_edge()` function; imports from `_errors.py` and `cdp.py`; removed local `EdgeNotFoundError` definition; `subprocess.Popen` call with `S603` noqa
- `serve/browser/src/owlbear_browser/cdp.py` — Added `process` param to `CDPConnectionManager.__init__`; added `__aenter__`/`__aexit__`; imported errors from `_errors.py`; subprocess cleanup via `terminate()` → `wait(timeout=5)` → `kill()` on `TimeoutExpired`
- `serve/browser/src/owlbear_browser/__init__.py` — Full public API re-exports (7 symbols)
- `serve/browser/pyproject.toml` — Added `playwright>=1.40` dependency
- `pyproject.toml` — Added `owlbear_browser` to `tool.coverage.run.source_pkgs`
- `tests/test_edge_launcher_cdp_758.py` — Added `TestBuilderDiscovered::test_aexit_kills_subprocess_when_wait_times_out` (RED→GREEN for TimeoutExpired branch)

### Test Results

- 758 tests: **32 passed** (31 AC tests + 1 builder-discovered)
- 755 regression: **21 passed** (no regressions)
- Combined: **53 passed, 0 failed**

### Coverage

- `owlbear_browser` total: **97%**
  - `_errors.py`: 100%
  - `__init__.py`: 100%
  - `launcher.py`: 100%
  - `cdp.py`: 95% (lines 37–40 uncovered — lazy `playwright` import body, always mocked in tests)

### Lint

- `ruff check serve/browser/src/owlbear_browser/`: **clean** (fixed ANN401 process→`Popen[bytes]`, PYI034 `__aenter__`→`Self`, RUF100 unused noqa, RUF022 sorted `__all__`)

### Commit

`00468f0f` — feat: Edge launcher + CDP connection manager impl (#758, builder)

### Evidence Summary

All AC items satisfied:

- AC#1: `pyproject.toml` name=owlbear-browser, playwright dep, hatchling, packages ✓
- AC#2: `launch_edge()` exported from launcher.py ✓
- AC#3: `CDPConnectionManager.__aenter__`/`__aexit__` ✓
- AC#4: `_errors.py` with all 3 error types ✓
- AC#5: `__init__.py` re-exports 7 public API symbols ✓
- AC#6: #755 tests unmodified, all 21 pass ✓
- AC#7: `serve/browser/src` already in ruff.src (pre-existing) ✓
- AC#8: `owlbear_browser` added to coverage source_pkgs ✓
- AC#9: ALLOWED_IMPORTS entry pre-existing ✓
- AC#10: CDP 127.0.0.1-only binding covered by #755 tests ✓
- AC#11: `__aexit__` terminates subprocess on all exit paths ✓
[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: 53 passed, 0 failed (32 × #758, 21 × #755 regression)

### Lint: clean

### Coverage

- `owlbear_browser` total: 97%
  - `_errors.py`: 100%
  - `__init__.py`: 100%
  - `launcher.py`: 100%
  - `cdp.py`: 95% (lines 37–40 — lazy `playwright` import body, always mocked in tests; acceptable)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC#1: pyproject.toml structure | TestFromAC_PackagePyproject (5 tests) | Yes — reads actual file | COVERED |
| AC#2: launcher.py exports | TestFromAC_LaunchEdge (8 tests) | Yes — imports + mocks behavior | COVERED |
| AC#3: CDPConnectionManager async CM | TestFromAC_AsyncContextManager (7 tests) | Yes — tests **aenter**/**aexit** | COVERED |
| AC#4: _errors.py exports | TestFromAC_PublicAPI (3 tests) | Yes — imports all 3 error classes from top-level; remove any→ImportError | COVERED (indirect) |
| AC#5: **init**.py re-exports | TestFromAC_PublicAPI (7 tests) | Yes | COVERED |
| AC#6: #755 tests pass | 21 passing #755 tests | Yes | COVERED |
| AC#7: ruff.src includes serve/browser/src | TestFromAC_WorkspaceConfig (1 test) | Yes | COVERED |
| AC#8: coverage source_pkgs includes owlbear_browser | TestFromAC_WorkspaceConfig (1 test) | Yes | COVERED |
| AC#9: ALLOWED_IMPORTS entry | TestFromAC_WorkspaceConfig (2 tests) | Yes | COVERED |
| AC#10: 127.0.0.1 only, --user-data-dir mandatory | #755 TestFromAC_CDPLaunchArgs | Yes — string matching on args | COVERED |
| AC#11: **aexit** cleans up subprocess | TestFromAC_AsyncContextManager (2 tests) + TestBuilderDiscovered (1 test) | Yes | COVERED |

Note: AC#4 not listed in test-writer's AC table but is covered transitively — TestFromAC_PublicAPI imports each error class from `owlbear_browser`; removing any from `_errors.py` breaks the import chain. Documentation gap only.

#### Security Review

- Hardcoded secrets: None. Windows path constants are not credentials.
- Subprocess injection: `cmd = [str(binary), *args]` — list-based Popen, not `shell=True`. `S603` noqa is appropriate; args are fully controlled by `build_launch_args()`.
- PATH/origin constraints: `--remote-allow-origins=http://127.0.0.1:{port}` — hardcoded 127.0.0.1, no wildcards (cdp.py confirmed). `endpoint_url = f"http://127.0.0.1:{self._port}"` — localhost-only.
- `EDGE_PATH` env var: used only as a file path, not executed as a shell string. No injection vector.
- No insecure deserialization. No secrets in error messages (only paths).
- `playwright>=1.40`: Microsoft-maintained, well-known library. No known CVEs in scope.
- **No issues found.**

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 31 TestFromAC_* tests | No modification | PRESERVED |
| (none) | Added TestBuilderDiscovered::test_aexit_kills_subprocess_when_wait_times_out | STRENGTHENED |

Builder added one test for a discovered branch (TimeoutExpired → kill path). All TestFromAC_* methods unchanged. ✓

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Specific: `assert result is manager`, `proc.kill.assert_called()`, `assert not manager.is_connected`. One `or` pattern in terminate test is permissive but covered by companion tests. |
| Negative/error-path coverage | STRONG | EdgeNotFoundError propagation, OSError→CDPConnectionError, exception in body, no-subprocess mode, TimeoutExpired→kill all covered. |
| Manual mutation reasoning | ADEQUATE | Removing `self._is_connected = False` in disconnect fails `test_is_disconnected_after_aexit`. Removing `__aenter__` return fails `test_aenter_returns_manager_instance`. TerminateOrKill `or` pattern slightly permissive but supplemented by TestBuilderDiscovered test. |
| Test independence | STRONG | Each test creates fresh mock objects via helpers; no shared mutable state. |
| Descriptive names | STRONG | All names clearly express intent. |

#### Data Safety

- No LLM output or unvalidated external data persisted.
- No shared mutable test state.
- No atomicity concerns.
- No issues found.

#### Implementation-Aware Gaps

- `find_edge_binary()` EDGE_PATH branch: covered by #755 TestFromAC_EdgeDiscovery.
- `CDPConnectionManager.connect()` TimeoutError path: covered by #755 TestFromAC_ConnectionLifecycle.
- `check_sso_redirect()`: covered by #755 TestFromAC_SSODetection.
- `disconnect()` when `_browser is None`: trivial guard, no test required.
- No significant untested paths in #758-scope code.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

- AC#4 omitted from test-writer coverage table (documentation gap only; coverage verified via code trace).
- `build_launch_args(user_data_dir="")` allows empty string; `--user-data-dir=` is still present per AC#10. Edge handles empty user-data-dir with default profile. Informational only.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1 | serve/browser/pyproject.toml L2: name=owlbear-browser, L6-7: playwright>=1.40, L9-10: hatchling, L13: packages | TestFromAC_PackagePyproject | PASS |
| AC#2 | launcher.py L27: find_edge_binary, L48: build_launch_args, L73: launch_edge | TestFromAC_LaunchEdge | PASS |
| AC#3 | cdp.py L68: **aenter**, L73: **aexit** | TestFromAC_AsyncContextManager | PASS |
| AC#4 | _errors.py L7: EdgeNotFoundError, L11: CDPConnectionError, L15: AuthenticationRequired | TestFromAC_PublicAPI (indirect) | PASS |
| AC#5 | **init**.py L9-16: **all** with 8 symbols | TestFromAC_PublicAPI | PASS |
| AC#6 | 21 #755 tests passing | test_edge_launcher_cdp_755.py | PASS |
| AC#7 | pyproject.toml L67: serve/browser/src in ruff.src | TestFromAC_WorkspaceConfig | PASS |
| AC#8 | pyproject.toml L185: owlbear_browser in source_pkgs | TestFromAC_WorkspaceConfig | PASS |
| AC#9 | test_package_boundary.py L46: owlbear_browser: set() | TestFromAC_WorkspaceConfig | PASS |
| AC#10 | launcher.py L63: --remote-allow-origins=<http://127.0.0.1:{port}>, L64: --user-data-dir; cdp.py L95: <http://127.0.0.1:{port}> | #755 TestFromAC_CDPLaunchArgs | PASS |
| AC#11 | cdp.py L79: terminate(), L80: wait(timeout=5), L82-83: TimeoutExpired→kill() | TestFromAC_AsyncContextManager + TestBuilderDiscovered | PASS |

### Confidence: .96

### Verdict: PASS

[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` is 100 lines (Project Identity + Repository Branches only) — no package inventory table. New `owlbear-browser` package does not require an update. |
| 2 | Module docstrings | Yes | Verified | All 4 new modules have module-level docstrings. All public symbols verified: `EdgeNotFoundError`, `CDPConnectionError`, `AuthenticationRequired`, `find_edge_binary()`, `build_launch_args()`, `launch_edge()` (launcher.py); `CDPConnectionManager` + `is_connected`, `__aenter__`, `__aexit__`, `connect()`, `disconnect()`, `check_sso_redirect()`, `playwright_connect_over_cdp()` (cdp.py); `__init__.py` module docstring present. All accurate to implementation. No edits required. |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already contains "Edge Launcher + CDP Implementation (Task #758)" section with 2 rows (Playwright `connect_over_cdp` API, Chrome 136 remote-debugging-port restriction). Researcher populated this. No additions needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/edge-launcher-cdp-impl-758.md` exists and is linked in task body under `## Research`. |

### Files Updated

None — all checklist items verified with no gaps found.

### Scratch Files

No `.owlbear/scratch/758-*` files exist.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1: pyproject.toml structure | serve/browser/pyproject.toml: name=owlbear-browser, playwright>=1.40, hatchling, packages | PASS |
| AC#2: launcher.py exports | find_edge_binary, build_launch_args, launch_edge defined in launcher.py | PASS |
| AC#3: CDPConnectionManager async CM | cdp.py: CDPConnectionManager with **aenter**/**aexit** | PASS |
| AC#4: _errors.py exports | EdgeNotFoundError, CDPConnectionError, AuthenticationRequired in _errors.py | PASS |
| AC#5: **init**.py re-exports | 7 public API symbols in **all** | PASS |
| AC#6: #755 tests pass | 21/21 pass | PASS |
| AC#7: ruff.src | serve/browser/src in root pyproject.toml ruff.src | PASS |
| AC#8: coverage source_pkgs | owlbear_browser in root pyproject.toml source_pkgs | PASS |
| AC#9: ALLOWED_IMPORTS | owlbear_browser: set() in test_package_boundary.py | PASS |
| AC#10: Security constraints | 127.0.0.1 binding + --user-data-dir verified by #755 CDPLaunchArgs tests | PASS |
| AC#11: **aexit** cleanup | terminate/wait/kill chain verified by AsyncContextManager + BuilderDiscovered tests | PASS |

### Test Results

- pytest (#758 scope): 53 passed, 0 failed
- pytest (full suite): 3215 passed, 344 failed, 8 skipped (all 344 failures pre-existing, zero in #758 scope; test_package_boundary failure is owlbear_voice residue from #750)
- ruff: clean (serve/ and tests/)

### Architect Quality: 5/5

Original body had vague bullets and a naming inconsistency (cdp_manager.py vs cdp.py). Architect refined into 11 specific, testable AC lines, caught the naming error, provided failure mode map, and linked to research doc. Exemplary upstream work.

### Deduction Breakdown

- AC lines with no evidence: 0 (-.02 each) = 0
- Lint violations: 0 (-.05) = 0
- AC quality score: 5/5, no deduction
- Missing reviewer evidence: No, detailed and structured
- Full-suite failures in task scope: 0 (-.05) = 0

### Confidence: 1.00

### Action: archive

### Reviewer Evidence Evaluation

Reviewer section is thorough: 11-row AC compliance table with file/line citations, security review (subprocess injection, PATH constraints, no secrets), test integrity matrix, test quality rubric (all STRONG/ADEQUATE), implementation-aware gap analysis. PASS at .96. Trusted.

### Commit Verification

Builder commit 00468f0f confirmed via git log for serve/browser/ and pyproject.toml.
