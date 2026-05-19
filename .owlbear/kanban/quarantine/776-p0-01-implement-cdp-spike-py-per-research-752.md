---
id: 776
title: 'P0-01: Implement cdp-spike.py per research #752'
status: archived
priority: critical
created: '2026-04-10T11:45:19.715661+00:00'
updated: '2026-04-10T19:04:35.715928+00:00'
tags:
- phase-0
- scope:browser
parent: 751
depends_on:
- 752
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Implement the CDP validation spike script at `.owlbear/scratch/cdp-spike.py` using the design from `.owlbear/research/cdp-spike-752.md` §3.3.

**Critical constraint (Chrome 136):** `--remote-debugging-port` no longer works with the default Edge profile. The script MUST use `--user-data-dir` with a fresh profile directory and test whether Windows Integrated Auth provides automatic SSO.

AC:

1. Script exists at `.owlbear/scratch/cdp-spike.py`
2. Runnable with `uv run python .owlbear/scratch/cdp-spike.py`
3. Finds Edge executable at standard Windows paths
4. Launches Edge with `--remote-debugging-port=9222 --user-data-dir=.owlbear/scratch/cdp-spike-profile`
5. Connects via `playwright.chromium.connect_over_cdp("http://127.0.0.1:9222", is_local=True)`
6. Navigates to a configurable target URL (default: a known SharePoint page)
7. Detects SSO redirect vs auto-authentication vs login page
8. Extracts `page.inner_text("body")` and logs text length
9. Handles all error cases from research §3.4 with clear messages
10. Logs timestamps for EDR/DLP correlation
11. Cleans up (disconnect, terminate subprocess) on all exit paths
[[2026-04-10]]

## Research

Validation pass of #752's CDP spike design against primary sources and #776 AC.

- Research doc: `.owlbear/research/cdp-spike-impl-776.md`
- Sources: 7 studied, all existing claims verified against Playwright docs + Chrome 136 blog post
- Recommendation: Proceed to implementation (.85 confidence). Design is complete with 3 minor gaps.
- Follow-up tasks: none — #776 itself is the implementation task
- Decision requests: none (T1 — autonomous)

### Key Findings

1. **All #752 claims verified**: `connect_over_cdp` API (v1.9+), `is_local` (v1.58+), 30s default timeout, `browser.contexts[0]` pattern, Chrome 136 `--user-data-dir` requirement — all confirmed against primary sources
2. **Gap A: `--remote-allow-origins` missing from design**: #755 and #758 research specify this as a security requirement from brief HR#4 but #752 §3.3 omits it. Builder must add `--remote-allow-origins=http://127.0.0.1:9222` to launch args
3. **Gap B: URL config mechanism**: AC says "configurable" but design doesn't specify how — `argparse` + `TARGET_URL` env var recommended
4. **Gap C: Signal handler**: Design says cleanup but doesn't specify `try/finally` wrapping — builder should wrap Steps 5-9

### Challenge

FALLBACK — validation pass of pre-existing design; no controversial recommendation to challenge

### Sources Attribution

Updated `.owlbear/sources/overview.md` with #776 section
[[2026-04-10]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Implements one spike script at `.owlbear/scratch/cdp-spike.py` — single deliverable |
| Interface clarity | PASS | 11 AC lines with specific APIs, paths, args. Research Gap A/B/C documented in body provide binding builder guidance |
| Dependency correctness | PASS (advisory) | `depends_on: [752]` — #752 is in `todo` (not `done`), but research deliverable (`.owlbear/research/cdp-spike-752.md`) is complete. Pipeline formality only — orchestrator should not dispatch until #752 reaches `done` |
| Module layering | PASS | Standalone scratch script. No module imports from project packages. No layering concerns |
| TDD compliance | PASS | Test-writer will process. Core CDP functionality requires real Edge browser (infrastructure tests). Structural tests possible: file existence, argparse, Edge path discovery. Test-writer decides scope |
| KISS/YAGNI | PASS | ~120-140 LOC spike. Minimal scope — sync Playwright, subprocess.Popen, argparse. No abstractions |
| Premise challenge | PASS | No existing CDP extraction capability. Phase 0 go/no-go gate for #751. Must be built |
| Pattern consistency | PASS | Matches existing scratch script conventions in `.owlbear/scripts/`: argparse, clear error messages, `__name__ == "__main__"` guard, exit codes. See `clean_scratch.py`, `e2e_smoke.py` for precedent |
| Security surface | PASS | CDP binds to 127.0.0.1 only. Research Gap A mandates `--remote-allow-origins=http://127.0.0.1:9222` (brief HR#4 security requirement). Builder MUST include this per body Research §Key Findings item 2 |
| Single domain | PASS | `scope:browser` only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Edge binary lookup | Not found at standard paths | Script exit with message | Yes (AC3, §3.4 row 1) | Clear error: install Edge or set EDGE_PATH |
| Port 9222 probe | Already in use | Script exit with message | Yes (§3.4 row 2) | Clear error: close other Edge/CDP clients |
| Edge launch + CDP flag | Chrome 136 silent ignore | Timeout on /json/version | Yes (§3.4 row 3) | Clear error: CDP not responding |
| connect_over_cdp | TimeoutError | Playwright TimeoutError | Yes (§3.4 row 4) | Clear error: connection failed |
| page.goto | SSO redirect / login page | Detection + logging | Yes (AC7, §3.4 rows 5-6) | SSO status reported |
| Cleanup | Ctrl+C / unexpected exit | Gap C: try/finally required | Yes (body Research §Gap C) | Builder wraps Steps 5-9 in try/finally |
| EDR/DLP | Process terminated externally | Detect missing subprocess | Yes (§3.4 row 8) | Logged timestamps for correlation (AC10) |

### Binding Builder Guidance (from Research Gaps)

These research findings in the task body are **binding** AC refinements:

1. **Gap A (security):** Add `--remote-allow-origins=http://127.0.0.1:9222` to Edge launch args alongside `--remote-debugging-port=9222` and `--user-data-dir`. Omitting this violates brief HR#4
2. **Gap B (AC6 specificity):** Implement URL configuration via `--url` CLI arg (argparse) with `TARGET_URL` env var fallback. Matches existing scratch script conventions
3. **Gap C (AC11 specificity):** Wrap Steps 5-9 in `try/finally` ensuring disconnect + subprocess terminate on all exit paths including Ctrl+C

### Codebase Evidence

- No existing `.owlbear/scratch/cdp-spike.py` — clean slate confirmed
- No playwright dependency in any `pyproject.toml` — spike is standalone, install via `uv pip install playwright`
- Scratch script conventions: `clean_scratch.py` and `e2e_smoke.py` use argparse, docstrings, exit codes — spike should follow same patterns
- `ProcessSupervisor` in `serve/orchestrator/` uses async subprocess — spike correctly uses sync `subprocess.Popen` (different context)
- Edge paths validated in research #755 §3d and #758 §3.5: EDGE_PATH env var (priority 0), Program Files (x86) (priority 1), Program Files (priority 2)

### Challenge Results

- Challenger: FALLBACK — no challenger agent in available agent roster
- Architect self-assessment: AC is specific (11 lines), research gaps are documented with clear remediation, security surface addressed (127.0.0.1 binding + `--remote-allow-origins`), failure modes enumerated in §3.4. Confidence: .90

### Verdict: APPROVE

### Action Taken: Advanced #776 to todo. Dependency #752 still in pipeline — orchestrator must not dispatch #776 until #752 is done. Three binding builder refinements documented (Gap A security arg, Gap B URL config mechanism, Gap C try/finally cleanup)

[[2026-04-10]]

## Test-Writer Notes

- Test file: tests/test_cdp_spike_776.py
- Classes: `TestFromAC_ScriptExists`, `TestFromAC_Runnable`, `TestFromAC_EdgeDiscovery`, `TestFromAC_LaunchArgs`, `TestFromAC_CDPConnection`, `TestFromAC_URLConfig`, `TestFromAC_SSODetection`, `TestFromAC_TextExtraction`, `TestFromAC_ErrorHandling`, `TestFromAC_TimestampLogging`, `TestFromAC_Cleanup`
- Tests per category: happy 8, edge 7, error 6, boundary 16
- Total: 37 tests, all FAIL (0 passed)
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — script exists at `.owlbear/scratch/cdp-spike.py` | `TestFromAC_ScriptExists` (1) |
| AC2 — runnable + main guard + docstring | `TestFromAC_Runnable` (4) |
| AC3 — Edge discovery (paths + env override + error) | `TestFromAC_EdgeDiscovery` (5) |
| AC4 — launch args include port, user-data-dir, allow-origins (Gap A security) | `TestFromAC_LaunchArgs` (5) |
| AC5 — connect_over_cdp with 127.0.0.1 endpoint + is_local=True | `TestFromAC_CDPConnection` (3) |
| AC6 — URL via --url, TARGET_URL env, hardcoded default (Gap B) | `TestFromAC_URLConfig` (3) |
| AC7 — SSO: redirect / login page / authenticated | `TestFromAC_SSODetection` (3) |
| AC8 — inner_text("body"), returns text, logs length | `TestFromAC_TextExtraction` (3) |
| AC9 — CDP timeout message, port-in-use (truthy/falsy) | `TestFromAC_ErrorHandling` (3) |
| AC10 — timestamp digits + message in log_step output | `TestFromAC_TimestampLogging` (2) |
| AC11 — disconnect+terminate, None guards, try/finally (Gap C) | `TestFromAC_Cleanup` (5) |

### Strategy

Subprocess tests for file existence, --help, main guard and docstring checks.
importlib tests (playwright pre-stubbed in sys.modules) for all helper function tests so failures are AttributeError / pytest.fail on missing file, not ModuleNotFoundError on missing playwright install.

Builder helper functions to expose: `_find_edge()`, `_build_launch_args(port, user_data_dir)`, `_connect_cdp(pw, port)`, `_parse_args(argv)`, `_detect_sso(page, target_url)`, `_extract_text(page)`, `_log_step(msg)`, `_cleanup(browser, process)`, `_check_port_in_use(port)` (or similar names — tests check both underscore and no-underscore variants via getattr).

[[2026-04-10]]

## Builder Notes

### Files Changed

- `.owlbear/scratch/cdp-spike.py` — created (not committed; gitignored per scratch convention)
- `pyproject.toml` — added `.owlbear/scratch/*.py` per-file-ignores (`ANN401`, `INP001`, `S603`, `T201`)

### Test Results

- 37 passed, 0 failed (all `TestFromAC_*` tests GREEN)
- Verified RED on entry (confirmed 37 FAILs before implementation)

### Coverage

- Scratch spike script; not included in coverage scope

### Lint

- ruff: clean (0 errors after fixing `DTZ005` → `datetime.now(tz=UTC)`, removing unused `noqa: BLE001`/`noqa: C901`, converting `try/except/pass` to `contextlib.suppress(Exception)` for `SIM105`/`S110`)

### Implementation Summary

Helper functions exposed per test-writer strategy:

- `_find_edge()` — EDGE_PATH env → x86 path → PF path → sys.exit(1) with helpful message
- `_build_launch_args(port, user_data_dir)` — port, user-data-dir, remote-allow-origins (Gap A)
- `_check_port_in_use(port)` — socket.connect_ex probe
- `_connect_cdp(pw, port)` — connect_over_cdp with is_local=True, prints on failure then re-raises
- `_parse_args(argv)` — argparse `--url`, TARGET_URL env fallback, hardcoded SharePoint default (Gap B)
- `_detect_sso(page, *, target_url)` — netloc match → authenticated / password input → login_page / else → sso_redirect
- `_extract_text(page)` — inner_text("body") + logs length
- `_log_step(msg)` — UTC ISO timestamps for EDR/DLP correlation (AC10)
- `_cleanup(browser, process)` — contextlib.suppress around disconnect + terminate/wait; None-safe (Gap C)

Main flow wrapped in try/finally for guaranteed cleanup on all exit paths including Ctrl+C.
[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: 37 passed, 0 failed (all `TestFromAC_*` tests GREEN)

### Lint: clean (0 errors — implementation + test file)

### Coverage: scratch spike — excluded from coverage scope (expected)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — script exists at `.owlbear/scratch/cdp-spike.py` | `TestFromAC_ScriptExists` (1) | Yes — `assert _SPIKE_PATH.exists()` | COVERED |
| AC2 — runnable + main guard + docstring | `TestFromAC_Runnable` (4) | Yes — `--help` exit 0; text grep for `__name__` guard and docstring | COVERED |
| AC3 — Edge discovery: env override, x86/PF fallback, error on missing | `TestFromAC_EdgeDiscovery` (5) | Yes — each priority path and sys.exit case individually tested | COVERED |
| AC4 — launch args: port, user-data-dir, allow-origins (Gap A) | `TestFromAC_LaunchArgs` (5) | Yes — each flag asserted separately with specific strings | COVERED |
| AC5 — `connect_over_cdp("http://127.0.0.1:9222", is_local=True)` | `TestFromAC_CDPConnection` (3) | Yes — `call_args` inspected for endpoint and `is_local` kwarg | COVERED |
| AC6 — `--url` flag + `TARGET_URL` env + hardcoded default (Gap B) | `TestFromAC_URLConfig` (3) | Yes — each source verified independently with monkeypatch | COVERED |
| AC7 — SSO: authenticated / login_page / sso_redirect | `TestFromAC_SSODetection` (3) | Yes (LAX — see below) | COVERED |
| AC8 — `inner_text("body")` + log length | `TestFromAC_TextExtraction` (3) | Yes — `assert_called_with("body")`, return value, length in output | COVERED |
| AC9 — timeout message + port-in-use helper (truthy/falsy) | `TestFromAC_ErrorHandling` (3) | Yes — socket patch, stderr keyword checks | COVERED |
| AC10 — timestamp digits + message in `_log_step` output | `TestFromAC_TimestampLogging` (2) | Yes — `re.search(r"\d{4}", output)` + sentinel message | COVERED |
| AC11 — disconnect + terminate, None guards, try/finally (Gap C) | `TestFromAC_Cleanup` (5) | Yes — mock call assertions; `try:` / `finally:` text grep | COVERED |

**LAX — AC7:** `test_detects_login_page_when_password_input_present` assertion is `"login" in result or "auth" in result`. A mutant returning `"authenticated"` for the password-input branch would pass this test (since `"auth" in "authenticated"` is True). No compensating `TestBuilderDiscovered` test exists. However, the other two SSO tests (sso_redirect and authenticated) constrain the result space sufficiently that complete misclassification would be caught across the suite. **Not elevated to FAIL-level** — informational only (Pass 2).

#### Security Review

- Hardcoded secrets: none. Default URL is a configurable placeholder.
- Injection: `subprocess.Popen` uses list form (no `shell=True`); edge binary comes from `EDGE_PATH` env var or fixed paths. List-form Popen with a trusted path is not shell injection.
- Path traversal: `_PROFILE_DIR` is derived from `__file__` with a fixed suffix; no user input in file paths.
- Insecure deserialization: no `pickle`, `yaml.load`, `eval()`, or `exec()` anywhere.
- CDP security: binds to `127.0.0.1:9222` only; `--remote-allow-origins=http://127.0.0.1:9222` present (Gap A satisfied). ✓
- Dependencies: `playwright` is Microsoft-maintained, widely used, no known CVEs.
- Secret leakage: log output contains timestamps + step names only. No credentials exposed.
- **No security issues found.**

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 37 `TestFromAC_*` tests | No modifications detected — builder notes confirm RED-first (37 FAILs on entry), count unchanged | PRESERVED |

#### Test Quality

| Dimension | Rating |
|-----------|--------|
| Assertion specificity | STRONG — specific flag strings, exact mock call assertions, regex patterns |
| Negative/error-path coverage | STRONG — port-in-use (truthy+falsy), Edge not found, CDP timeout, None guards |
| Manual mutation reasoning | ADEQUATE — mutations in `_find_edge`, `_build_launch_args`, `_connect_cdp` all caught. LAX in AC7 noted above |
| Test independence | STRONG — `_load_spike()` evicts module cache; fresh load per test; no shared state |
| Descriptive test names | STRONG — all names describe intent |

**No WEAK ratings.**

#### Data Safety

No LLM output persistence, no shared mutable state, no unbounded input, no multi-step atomicity concerns. PASS.

#### Implementation-Aware Test Gap Analysis

All 9 helper functions exercised. `main()` integration untested (requires live browser — expected for a CDP spike). `_find_edge()` silent-fallback when `EDGE_PATH` is set to a non-existent path is untested but this is a minor edge case for a scratch spike, not a significant code path. **No critical gaps.**

#### Necessity Check

`playwright` is the explicit subject of this spike — `connect_over_cdp` via `playwright.chromium` is the sole purpose of task #776. No existing project tooling provides this. Not a presumptive feature. PASS.

#### Builder Process Quality

Single `## Builder Notes` section. No retries. **CLEAN.**

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `cdp-spike.py` at `.owlbear/scratch/cdp-spike.py` — file read by quality-runner, 37 tests ran against it | PASS |
| AC2 | `--help` exits 0 (subprocess test); `if __name__ == "__main__":` guard present (text grep); module docstring present (text grep) | PASS |
| AC3 | `_find_edge()` checks EDGE_PATH → x86 path → PF path; `sys.exit(1)` with "Edge or EDGE_PATH" message on all-miss | PASS |
| AC4 | `_build_launch_args()` returns `["--remote-debugging-port=9222", "--user-data-dir=...", "--remote-allow-origins=http://127.0.0.1:9222", ...]` | PASS |
| AC5 | `_connect_cdp()` calls `pw.chromium.connect_over_cdp("http://127.0.0.1:9222", is_local=True)` | PASS |
| AC6 | `_parse_args()` argparse with `--url`; `TARGET_URL` env fallback; hardcoded SharePoint default | PASS |
| AC7 | `_detect_sso()` returns "authenticated" / "login_page" / "sso_redirect" based on URL + password selector | PASS |
| AC8 | `_extract_text()` calls `page.inner_text("body")` and `_log_step(f"Body text extracted — length={len(text)} chars")` | PASS |
| AC9 | `_connect_cdp` prints + re-raises on Exception; `_check_port_in_use()` via `socket.connect_ex`; `_find_edge` sys.exit on miss | PASS |
| AC10 | `_log_step()` prints `[{UTC ISO timestamp}] {msg}` — `datetime.now(tz=UTC).isoformat(timespec="seconds")` | PASS |
| AC11 | `_cleanup()` with `contextlib.suppress`, None guards for both browser and process; `main()` wrapped in `try/finally` calling `_cleanup` | PASS |

**Research Gaps**: Gap A (--remote-allow-origins in `_build_launch_args`): DONE. Gap B (--url + TARGET_URL in `_parse_args`): DONE. Gap C (try/finally in `main`): DONE.

---

### Deductions

- 0 FAIL-level deductions
- 1 informational LAX (AC7 SSO assertion overly permissive — not blocking)
- 1 informational gap (`EDGE_PATH` silent fallback when set to non-existent path — untested, minor, scratch spike)

### Verdict: PASS | confidence .94 → docs

[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Scratch spike only — `.owlbear/scratch/cdp-spike.py` is gitignored, not a public API. `pyproject.toml` ruff per-file-ignores is lint config, not behavior. `copilot-instructions.md` unchanged. |
| 2 | Module docstrings | No | N/A | No project Python modules modified. Spike script docstring verified by reviewer in `## Review Evidence` AC2 PASS. |
| 3 | External attribution | Yes | Pre-existing | `.owlbear/sources/overview.md` lines 37–43: 3 rows for #776 (Playwright API, Chrome 136 blog, security brief voice). Added by researcher, confirmed present. |
| 4 | CLI changes | No | N/A | No OwlBear CLI commands added or modified. Spike argparse is internal to scratch script. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/cdp-spike-impl-776.md` confirmed present. Linked in task body. No follow-up tasks required per researcher. |

### Files Updated

None — all relevant docs were already updated upstream.

### Scratch Files Cleaned

No `.owlbear/scratch/776-*` files found.

### Commit

No docs commit needed — no documentation files were modified in this gate.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — script exists at `.owlbear/scratch/cdp-spike.py` | Test-Path confirmed; 37 tests ran against it | PASS |
| AC2 — runnable + main guard + docstring | Reviewer evidence: --help exit 0, **name** guard grep, docstring grep | PASS |
| AC3 — Edge discovery paths + error | Source spot-check: _find_edge() EDGE_PATH env, x86, PF, sys.exit(1) | PASS |
| AC4 — launch args: port, user-data-dir, allow-origins (Gap A) | Source spot-check: _build_launch_args() all 3 flags present | PASS |
| AC5 — connect_over_cdp with is_local=True | Source spot-check: _connect_cdp() calls connect_over_cdp(endpoint, is_local=True) | PASS |
| AC6 — configurable URL via --url + TARGET_URL (Gap B) | Reviewer evidence: argparse --url, TARGET_URL env, hardcoded default | PASS |
| AC7 — SSO detection: authenticated/login_page/sso_redirect | Reviewer evidence: 3 states tested (LAX informational, not blocking) | PASS |
| AC8 — inner_text("body") + log length | Source spot-check: _extract_text() calls inner_text("body"), logs length | PASS |
| AC9 — error handling: timeout, port-in-use | Reviewer evidence: socket patch, stderr keyword checks | PASS |
| AC10 — timestamps for EDR/DLP correlation | Source spot-check: datetime.now(tz=UTC).isoformat(timespec="seconds") | PASS |
| AC11 — cleanup: disconnect+terminate, try/finally (Gap C) | Source spot-check: main() try/finally, _cleanup() with contextlib.suppress + None guards | PASS |

### Test Results

- pytest (task-scoped): 37 passed, 0 failed
- pytest (full suite): 3309 passed, 271 failed, 8 skipped — 0 failures in test_cdp_spike_776.py; all 271 failures are pre-existing in unrelated files (test_analysis, test_bookmark_pipeline, test_knowledge_foundation, etc.)
- ruff: clean (0 errors on both cdp-spike.py and test_cdp_spike_776.py)

### Architect Quality: 4/5

11 AC lines with specific APIs, paths, and args. Three gaps (A: security arg, B: URL config, C: try/finally) were identified by research and documented as binding refinements — good upstream quality. Minor gap: AC6 "configurable" was vague but filled by Gap B.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 11 PASS)
- Lint violations: 0
- AC quality score: 4/5 (no deduction)
- Missing reviewer evidence: No (detailed, PASS verdict)
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive

### Commit Integrity

- test-writer: f612e6de — tests/test_cdp_spike_776.py (738 lines, scoped)
- builder: 662176ec — pyproject.toml (6 lines ruff per-file-ignores, scoped)
- cdp-spike.py in .owlbear/scratch/ (gitignored per convention — correct)
- Reviewer PASS at .94, detailed evidence with security review and test integrity check
