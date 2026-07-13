---
id: 782
title: Tests — owlbear_browser package scaffold and CDP launcher
status: archived
priority: medium
created: '2026-04-10T12:30:44.020270+00:00'
updated: '2026-04-14T01:13:00.839947+00:00'
tags:
- phase-1
- scope:browser
- type:test
- archived
- superseded
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `import owlbear_browser` succeeds
- Tests verify CDP launcher class exists with `launch()`, `connect()`, `close()` async methods
- Tests verify Edge binary path resolution (Windows)
- Tests use mocked subprocess/CDP — no real browser launch in unit tests
- File: `tests/test_browser_cdp_775.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 1) from #775
- See research F5: owlbear_browser has no cross-namespace deps

[[2026-04-11]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task targeting `EdgeCDPLauncher` + package import |
| Interface clarity | PASS | AC specifies methods (`launch`, `connect`, `close`), mock constraint, and target file. AC#2 "CDP launcher class" = `EdgeCDPLauncher` (only class with all three methods) |
| Dependency correctness | PASS | No `depends_on`; `owlbear_browser` package already exists at `serve/browser/src/owlbear_browser/` |
| Module layering | PASS | Test file imports from `owlbear_browser` — no layering violation |
| TDD compliance | PASS | This IS the test task (`type:test`) |
| KISS/YAGNI | PASS | 4 AC items, minimal scope |
| Premise challenge | PASS | `EdgeCDPLauncher` has zero test coverage — existing tests (#755, #758) cover `CDPConnectionManager`, `find_edge_binary()`, `launch_edge()` but NOT `EdgeCDPLauncher` |
| Pattern consistency | PASS | File naming `test_{desc}_{parent_id}.py` matches `test_browser_content_775.py`; `TestFromAC_*` class pattern expected |
| Security surface | PASS | Test file only — no new system boundaries |
| Single domain | PASS | Browser domain |

### Builder Guidance
- **AC#2 class name:** "CDP launcher class" refers to `EdgeCDPLauncher` in `owlbear_browser.edge_launcher` — the only class with `launch()`, `connect()`, `close()` async methods.
- **AC#3 overlap:** `find_edge_binary()` is already tested in `test_edge_launcher_cdp_755.py::TestFromAC_EdgeDiscovery`. For this task, test Edge binary resolution **through `EdgeCDPLauncher`** (e.g., `EdgeCDPLauncher(binary_path=None)` triggers `find_edge_binary()` internally; `EdgeCDPLauncher(binary_path="nonexistent")` raises `FileNotFoundError`).
- **Existing implementation reference:** `serve/browser/src/owlbear_browser/edge_launcher.py` — `EdgeCDPLauncher.__init__` accepts `binary_path`, `port`, `user_data_dir`.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in tool allowlist
- Architect response: Proceeded with codebase evidence (verified implementation exists, no test coverage gap overlap, AC items are verifiable)

### Verdict: APPROVE
### Action Taken: Advanced to `todo`. AC is verifiable. `EdgeCDPLauncher` is the untested target class. Overlap with #755/#758 tests is minimal when tests are scoped to `EdgeCDPLauncher` path.
[[2026-04-11]]
## Test-Writer Notes

**File:** `tests/test_browser_cdp_775.py`
**Commit:** `9d341b72`

### Classes and test counts

| Class | Category | Count |
|-------|----------|-------|
| `TestFromAC_PackageImport` | happy / import | 3 |
| `TestFromAC_EdgeCDPLauncherInterface` | happy / edge / error / boundary | 9 |
| `TestFromAC_EdgeBinaryResolution` | happy / edge / error | 6 |
| **Total** | | **20** |

### Fail verification

```
pytest tests/test_browser_cdp_775.py
19 passed, 1 failed
```

**Failing test:** `TestFromAC_EdgeCDPLauncherInterface::test_close_kills_process_when_terminate_times_out`
**Failure:** `AssertionError: Expected 'kill' to have been called once. Called 0 times.`
**Ruff:** clean

### Retroactive coverage note

`EdgeCDPLauncher` was already implemented (as part of the broader #775 scope) before this test task executed. The 19 passing tests provide regression coverage for the pre-existing implementation. The 1 failing test reveals a genuine behavioral gap: `close()` uses `contextlib.suppress(subprocess.TimeoutExpired, …)` without then calling `process.kill()` — inconsistent with `CDPConnectionManager.__aexit__` which does force-kill on timeout. Builder must add the SIGKILL fallback to satisfy this test.

### AC coverage

| AC | Tests |
|----|-------|
| AC1 — `import owlbear_browser` succeeds | `test_import_owlbear_browser_succeeds`, `test_edge_cdp_launcher_importable_from_package`, `test_edge_cdp_launcher_in_package_all` |
| AC2 — CDP launcher class with async `launch()`, `connect()`, `close()` | 9 tests in `TestFromAC_EdgeCDPLauncherInterface` |
| AC3 — Edge binary path resolution (Windows) via `EdgeCDPLauncher` | 6 tests in `TestFromAC_EdgeBinaryResolution` |
| AC4 — Mocked subprocess/CDP, no real browser | All tests use `patch` for `subprocess.Popen` and `CDPConnectionManager` |
[[2026-04-11]]
## Builder Notes

### Files Changed
- `serve/browser/src/owlbear_browser/edge_launcher.py` — replaced `contextlib.suppress(subprocess.TimeoutExpired, OSError)` around `wait()` with explicit try/except that calls `process.kill()` on `TimeoutExpired`.

### Test Results
- **20 passed, 0 failed** — all `TestFromAC_*` tests green
- Commit: `73365bab`

### Lint
- ruff: clean

### Fix Applied
`close()` was suppressing `subprocess.TimeoutExpired` without calling `process.kill()`. Added SIGKILL fallback: when `wait(timeout=5)` raises `TimeoutExpired`, `self._process.kill()` is now called before clearing `self._process`.

### Coverage
Single surgical change — 1 file, 5 insertions, 1 deletion. All pre-existing tests remain green.
[[2026-04-11]]
## Review Evidence

**Review cycle:** 1st

### Test Execution — FATAL ENVIRONMENT ERROR

Quality-Runner returned FATAL on pytest launch. No test results available.

```
FATAL: Instrument error — pytest cannot initialize.
KeyboardInterrupt during import phase — anyio, coverage plugin, unittest bytecode.
Root cause: Corrupted .pyc files or venv conflict:
  C:\Users\p362329\Coding\Projects\owlbear-dev\.venv (project)
  vs. C:\Users\p362329\AppData\Roaming\uv\python (uv runtime)
Pytest fails even in collection-only mode (--co). Environment defect, not code defect.
```

**Block reason:** Cannot satisfy the "always run tests yourself" critical rule. Builder self-report ("20 passed, 0 failed") is a claim, not evidence.

---

### Code-Reader Evidence (collected in parallel — valid)

**AC Compliance:**

| AC | Mapped Tests | Would Fail If Violated? | Verdict |
|----|-------------|------------------------|---------|
| AC1 — `import owlbear_browser` succeeds | `test_import_owlbear_browser_succeeds`, `test_edge_cdp_launcher_importable_from_package`, `test_edge_cdp_launcher_in_package_all` | Yes — all 3 fail if import broken | COVERED |
| AC2 — CDP launcher with async `launch()`, `connect()`, `close()` | 11 tests in `TestFromAC_EdgeCDPLauncherInterface` | Yes — method existence, async sig, lifecycle contracts | COVERED |
| AC3 — Edge binary path resolution (Windows) | 6 tests in `TestFromAC_EdgeBinaryResolution` | Yes — explicit path, fallback, error propagation | COVERED |
| AC4 — Mocked subprocess/CDP | All 21 tests use `@patch` for Popen and CDPConnectionManager | Yes — unmocked = real browser launch | COVERED |

**TestFromAC Integrity:** All 21 tests are NEW. No existing tests modified, weakened, or removed. Builder only added SIGKILL fix to `edge_launcher.py` (surgical: 5 insertions, 1 deletion).

**SIGKILL fix correctness:** Reviewed. `close()` now uses explicit try/except replacing `contextlib.suppress(TimeoutExpired)`, calls `process.kill()` on `TimeoutExpired`. Pattern is correct (SIGTERM → wait(5) → SIGKILL on timeout → cleanup). Code-reader grade: A.

**Test quality (code-reader):** A− overall. Assertion specificity A, independence A, naming A. Minor gaps: OSError path in `wait()` untested (close() branch 5), manager exception propagation untested — not FAIL-level.

**Security (code-reader):** No critical vulns. Port range not validated; `user_data_dir` validation is downstream responsibility of `build_launch_args()` — acceptable.

---

### Block Resolution

Unblock by fixing the pytest environment (clear `.pyc` files or reconcile venv). Once re-run returns a clean result, reviewer can re-claim and issue verdict. Code-reader evidence is strong — no code-level blockers found.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_browser_cdp_775.py`). Unblocked for review continuation.

[[2026-04-14]]
## Archived — Superseded by CDP Pivot
Tests for Edge CDP launcher — approach abandoned. Group Policy blocks CDP on corporate laptop. New architecture: Playwright Chromium + SSO extension. New test tasks will cover the pivot approach.
[[2026-04-14]]
## Review Evidence

**Review cycle:** 2nd  
**Reviewer action:** Administrative closure — task superseded before review could complete.

### Superseded Status

Task body (2026-04-14): *"Archived — Superseded by CDP Pivot. Tests for Edge CDP launcher — approach abandoned. Group Policy blocks CDP on corporate laptop. New architecture: Playwright Chromium + SSO extension."*

The implementation under review (`EdgeCDPLauncher` SIGKILL fix in `edge_launcher.py`, `tests/test_browser_cdp_775.py`) is no longer part of the active architecture. The 1st-cycle review was blocked on environment defect; environment was restored (2026-04-13 note confirmed), but the architectural pivot was announced before a 2nd review cycle could be dispatched.

### Review Verdict

**No verdict issued.** Standard AC compliance, test quality, and confidence scoring are not applicable to superseded work. Moving to `archived`. No follow-up tasks required — new test tasks for the Playwright pivot are expected under the #775 parent.