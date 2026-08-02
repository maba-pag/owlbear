---
id: 937
title: 'P3-01: Launch command (uv run cockpit) + browser auto-open'
status: archived
priority: medium
created: 2026-04-17T19:59:26.716250+00:00
updated: 2026-04-19T15:02:14.279716+00:00
tags:
- cockpit
- backend
- phase-3
- type:build
parent: 920
depends_on:
- 934
- 936
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Wire `uv run cockpit` to start the FastAPI server serving the built SPA and auto-open the browser.

## Acceptance Criteria

- [ ] `pyproject.toml` script entry: `cockpit = "owlbear_cockpit.main:run"` (or equivalent CLI entry point)
- [ ] `uv run cockpit` starts uvicorn on `127.0.0.1:{port}` (default port: 8420 or configurable via `COCKPIT_PORT` env var)
- [ ] FastAPI mounts `/api/` routes + static file handler serving SPA from `dist/` directory
- [ ] Catch-all route for client-side routing (non-API paths serve `index.html`)
- [ ] Browser auto-opens to `http://127.0.0.1:{port}/` on startup (webbrowser module)
- [ ] Graceful shutdown on Ctrl+C (uvicorn default)
- [ ] Error message if `dist/` directory is missing (frontend not built)

## Files

- `serve/cockpit/src/owlbear_cockpit/main.py` (updated with run function + static mount)
- `serve/cockpit/pyproject.toml` (script entry)
[[2026-04-19]]

## Research

- Research doc: .owlbear/research/937-cockpit-launch-command.md
- Sources: 7 studied, 4 high-relevance (external)
- Recommendation: StaticFiles at /assets/ + catch-all route + run() with threading.Timer (confidence: 0.85)
- Follow-up tasks created: none needed — task itself proceeds to backlog for arch review
- Decision requests: none (T1 — standard build task within approved Brief)

## Challenge Results

- Challenger: reconsider (confidence in original: 0.55)
- Key challenges: __file__ fragility, StaticFiles(html=True) as alternative, route shadowing, test isolation
- Researcher response: rebutted 3/4 with source evidence; accepted test isolation concern (static routes conditional in run())
- Revised confidence: 0.85 (up from 0.88 original — minor reduction for accepted test-isolation refinement)

## Key Implementation Decisions

1. Static serving (mount + catch-all) added dynamically in run(), NOT at module import → preserves TestClient isolation
2. Catch-all route IS needed — confirmed from Starlette source that StaticFiles(html=True) does not serve root index.html for deep SPA paths
3. COCKPIT_NO_OPEN env var for suppressing browser open (testability, CI)
4. dist_dir via __file__-relative path (workspace-only package, never published)
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Launch + serve is one logical operation |
| Interface clarity | PASS (after refine) | AC now specifies engine init, COCKPIT_NO_OPEN, and kanban_dir resolution |
| Dependency correctness | PASS | Deps #934/#936 not verifiable (archived?) but task is self-contained |
| Module layering | PASS | run() is CLI boundary — dynamic mounts don't pollute module-level app |
| TDD compliance | PASS | Test-writer will process at todo |
| KISS/YAGNI | PASS | Minimal scope, standard patterns (threading.Timer, StaticFiles, env vars) |
| Premise challenge | PASS | No existing way to launch cockpit — capability is needed |
| Pattern consistency | PASS | [project.scripts] matches orchestrator pattern; env var config is standard |
| Security surface | PASS | Binds 127.0.0.1 only; env vars are trusted local input |
| Single domain | PASS | All cockpit/backend domain |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| dist/ missing | FileNotFoundError | sys.exit(1) + message | YES (AC #7) | Clear error before server start |
| kanban_dir missing | Directory not found | sys.exit(1) + message | YES (new AC #8) | Clear error before server start |
| Port in use | OSError from uvicorn | Uvicorn default traceback | YES (uvicorn native) | Standard error |
| Browser open fails | webbrowser error | Swallowed (non-fatal) | YES (AC #5 revised) | Server still runs |

### Challenge Results

- Challenger: reconsider (5 challenges, 1 critical, 2 moderate, 2 minor)
- C1 (engine init missing from AC): ACCEPTED — added AC #8
- C2 (COCKPIT_NO_OPEN not in AC): ACCEPTED — added to AC #5
- C3 (global app mutation): REBUTTED — tests never call run(), no contamination risk
- C4 (Timer reliability): NOTED — pragmatic for local dev tool, user can refresh
- C5 (port validation): NOTED — uvicorn handles natively, YAGNI

### AC Refinements Applied

1. AC #5 revised: added "suppressed via COCKPIT_NO_OPEN=1 env var; browser open failure must not crash server"
2. AC #8 added: "run() initializes KanbanEngine from .owlbear/kanban/ relative to CWD (or KANBAN_DIR env var) and sets app.state.engine before starting uvicorn; error message if kanban dir is missing"
3. AC #2 revised: added "port must be valid integer 1-65535 or sys.exit with error"

### Verdict: APPROVE (after REFINE)

### Action Taken: Refined AC to address engine initialization gap (critical) and COCKPIT_NO_OPEN (moderate), then advanced to todo

[[2026-04-19]]

## Test-Writer Notes

- Test file: tests/test_cockpit_launch.py
- Classes: `TestFromAC_CockpitLaunch`
- Tests per category: happy 9, edge 2, error 7, boundary 3
- Total: 21 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| #1 — run() callable / pyproject script entry | `test_run_is_callable_in_main`, `test_pyproject_has_cockpit_script_entry` |
| #2 — uvicorn host=127.0.0.1, port=8420 | `test_run_invokes_uvicorn_with_default_port`, `test_run_binds_to_localhost` |
| #2 — COCKPIT_PORT env var | `test_run_uses_cockpit_port_env_var` |
| #2 (revised) — port validation | `test_run_exits_on_non_integer_port`, `test_run_exits_on_port_zero`, `test_run_exits_on_port_above_max` |
| #2 — port boundaries | `test_run_accepts_port_boundary_low` (1), `test_run_accepts_port_boundary_high` (65535) |
| #3 — static files in run() not at import | `test_static_files_not_mounted_at_module_import`, `test_static_files_mounted_after_run` |
| #4 — catch-all SPA route | `test_catchall_route_serves_index_html_for_spa_paths` |
| #5 — browser auto-open | `test_browser_opens_on_startup`, `test_cockpit_no_open_suppresses_browser`, `test_browser_failure_does_not_crash_server` |
| #7 — dist/ missing error | `test_run_exits_with_error_if_dist_missing` |
| #8 — KanbanEngine init | `test_engine_initialized_from_kanban_dir_env_var`, `test_engine_initialized_from_cwd_owlbear_kanban`, `test_engine_set_on_app_state_before_uvicorn_starts`, `test_run_exits_with_error_if_kanban_dir_missing` |

### Implementation notes for builder

- `uvicorn.run` is patched at `"uvicorn.run"` (works regardless of import location in run())
- `threading.Timer` patched with `_ImmediateTimer` (fires callback immediately) for browser-open tests
- `serve/cockpit/dist/` exists in the workspace — happy path tests use it directly (no mock needed for dist check)
- `_reset_app_after_run` autouse fixture restores `app.routes` and clears `app.state.engine` between tests; uses `contextlib.suppress(AttributeError, KeyError)` for Starlette's `State.__delattr__` semantics
[[2026-04-19]]

## Builder Notes

### Files Changed

- `serve/cockpit/src/owlbear_cockpit/main.py` — added `run()` function + constants `_DEFAULT_PORT`, `_MAX_PORT`; added imports (`contextlib`, `os`, `sys`, `threading`, `webbrowser`, `Path`, `uvicorn`, `HTMLResponse`, `StaticFiles`)
- `serve/cockpit/pyproject.toml` — added `[project.scripts]` section with `cockpit = "owlbear_cockpit.main:run"`

### Test Results

- `tests/test_cockpit_launch.py`: 21/21 passed (was 21/21 FAILED in RED)
- Full cockpit test suite: 128 passed, 0 failed
- Builder-discovered tests: none needed — AC was complete

### Lint Status

- ruff: clean (0 errors on main.py and test file)
- One `ARG001` suppressed with noqa on `_spa_catchall(path: str)` — path param required by FAST003 rule but not used in body (always serves index.html)

### Implementation Notes

- `run()` deferred: port validate → kanban dir check → dist check → engine init → mount StaticFiles + catch-all → browser timer → uvicorn.run
- Static mount (`/assets`) and catch-all (`/{path:path}`) added INSIDE `run()` — preserves TestClient isolation (AC #3 architectural invariant)
- `KanbanEngine` imported inside `run()` (PLC0415) to avoid circular import at module level
- `dist_dir` = `Path(__file__).parent.parent.parent / "dist"` → `serve/cockpit/dist/`
- Browser open wrapped in `contextlib.suppress(Exception)` — non-fatal (AC #5)
- All error paths use `sys.stderr.write` (T201-clean) + `sys.exit(1)`
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 21 passed, 0 failed (tests/test_cockpit_launch.py)
- Full cockpit suite: not re-run (scoped to launch tests)

### Lint

- clean (0 violations, ruff exit 0)

### Coverage

- owlbear_cockpit.main: not reported by quality-runner (only kanban modules appeared in coverage output); 21 passing tests exercise run() — coverage gap in tooling output, not implementation

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| #1 — run() callable + pyproject entry | `test_run_is_callable_in_main`, `test_pyproject_has_cockpit_script_entry` | Yes | COVERED |
| #2 — uvicorn host=127.0.0.1, port=8420 | `test_run_invokes_uvicorn_with_default_port`, `test_run_binds_to_localhost` | Yes — asserts exact call_args kwargs | COVERED |
| #2 — COCKPIT_PORT env var | `test_run_uses_cockpit_port_env_var` | Yes | COVERED |
| #2 (revised) — port 1–65535 validation | `test_run_exits_on_non_integer_port`, `test_run_exits_on_port_zero`, `test_run_exits_on_port_above_max` | Yes | COVERED |
| #2 — port boundaries | `test_run_accepts_port_boundary_low`, `test_run_accepts_port_boundary_high` | Yes | COVERED |
| #3 — static mount inside run() | `test_static_files_not_mounted_at_module_import`, `test_static_files_mounted_after_run` | Yes | COVERED |
| #4 — catch-all serves index.html | `test_catchall_route_serves_index_html_for_spa_paths` | __No__ — asserts `status_code==200` and `len(resp.text)>0` only; a 200 with `" "` or any non-HTML body passes | __LAX__ |
| #5 — browser open, COCKPIT_NO_OPEN, non-fatal | 3 tests | Yes | COVERED |
| #6 — graceful shutdown | none (no-code AC, uvicorn default) | N/A | COVERED |
| #7 — dist/ missing error | `test_run_exits_with_error_if_dist_missing` | Yes | COVERED |
| #8 — KanbanEngine init, order, missing dir | 4 tests | Yes | COVERED |

LAX finding on AC #4 with no compensating `TestBuilderDiscovered` test. Builder notes: "Builder-discovered tests: none needed". → auto-FAIL per 5.0 rules.

#### Security Review

No issues found:

- Port validated as `int` 1–65535 before use in `webbrowser.open` URL — no injection surface
- `dist_dir` derived from `__file__`, not user input — no path traversal
- `kanban_dir` from `KANBAN_DIR` env var passed only to `KanbanEngine` — no direct file ops
- No hardcoded secrets, no insecure deserialization, no external deps added
- stderr path leak in error message: acceptable for developer CLI on stderr, not an HTTP surface

#### Test Integrity

Builder did not modify tests/test_cockpit_launch.py. All 21 TestFromAC_CockpitLaunch methods PRESERVED.

#### Test Quality — 5.3

__WEAK on AC #4 assertion__ (tests/test_cockpit_launch.py:311):

```python
assert resp.status_code == 200
assert len(resp.text) > 0   # ← WEAK: any non-empty body at 200 passes
```

The implementation returns `HTMLResponse((dist_dir / "index.html").read_text(...))`. The test does not verify: content-type is `text/html`, content contains `<html`, or content matches actual `index.html` bytes. A catch-all returning `HTMLResponse("x")` passes. This is the core correctness assertion for the SPA routing invariant — it must be strong.

All other tests: STRONG assertions (exact integers, exact host string, isinstance checks, exact call_args).

#### Data Safety

No issues. Single-threaded init path, contextlib.suppress on timer callback, no unbounded input.

#### Implementation-Aware Test Gaps (5.5)

- Informational: `StaticFiles(directory=dist_dir / "assets")` raises `RuntimeError` if `assets/` absent from an otherwise valid `dist/` — no test covers partial build scenario
- Informational: `_spa_catchall` calls `.read_text()` without try/except — `dist/` without `index.html` → unhandled `FileNotFoundError`; no test covers this
- Both are beyond AC scope; flagged for follow-up

#### Builder Process Quality (5.7)

Single `## Builder Notes` — CLEAN

---

### Deductions

| Finding | Severity | Deduction |
|---------|----------|-----------|
| AC #4 test assertion WEAK (`len(resp.text)>0`); no compensating builder-discovered test | Critical (5.0 LAX+no-compensator, 5.3 WEAK) | -0.28 |

### Verdict

confidence: .72 → __FAIL__

### Action

Routing → __todo__ (test gap; implementation is correct — catch-all returns actual index.html content; the test assertion is insufficient to verify AC #4).

__Fix required in `tests/test_cockpit_launch.py`:__
Strengthen `test_catchall_route_serves_index_html_for_spa_paths` assertion. Replace `assert len(resp.text) > 0` with at minimum:

```python
assert resp.headers.get("content-type", "").startswith("text/html")
assert "<html" in resp.text.lower()
```

Or assert the response body matches `(dist_dir / "index.html").read_text(encoding="utf-8")` exactly.
[[2026-04-19]]

## Test-Writer Notes

- Retry: strengthened weak assertion in `test_catchall_route_serves_index_html_for_spa_paths` per reviewer finding (LAX AC #4 assertion)
- Replaced `assert len(resp.text) > 0` with:
  - `assert resp.headers.get("content-type", "").startswith("text/html")`
  - `assert "<html" in resp.text.lower()`
- 21 tests, all PASS (implementation is already correct — fix is assertion quality only)
- ruff: clean
- Commit: 8e3b452c
[[2026-04-19]]

## Builder Notes

### Files Changed

- `serve/cockpit/src/owlbear_cockpit/main.py` — run() function already implemented from prior builder pass; no changes needed this iteration
- `tests/test_cockpit_launch.py` — assertion strengthened by test-writer (commit 8e3b452c); builder confirmed GREEN with new assertions

### Test Results

- `tests/test_cockpit_launch.py`: 21/21 passed
- Full cockpit suite (154 tests): 154 passed, 0 failed
- Pre-existing failures (6) in `mcp-knowledge/` — unrelated to #937, not introduced by this task

### Coverage

- `owlbear_cockpit/main.py`: 100%
- `owlbear_cockpit` package overall: deps.py 85% (lines 28–30 — app.dependency_overrides teardown path, not cockpit launch scope), all other files 100%

### Lint Status

- ruff: clean (0 violations on `serve/cockpit/src/` and `tests/test_cockpit_launch.py`)

### Evidence Summary

- Reviewer FAIL was due to LAX assertion in `test_catchall_route_serves_index_html_for_spa_paths` (`len(resp.text)>0`)
- Test-writer strengthened assertion: added `content-type startswith text/html` + `"<html" in resp.text.lower()`
- Implementation was already correct — fix was assertion quality only
- All 21 tests pass with strengthened assertions; implementation unchanged
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 21 passed, 0 failed (tests/test_cockpit_launch.py)
- Full suite not re-run; scoped to launch tests per task scope

### Lint

- clean (ruff exit 0, 0 violations on main.py and test file)

### Coverage

- owlbear_cockpit.main: not captured in quality-runner output (kanban modules only appear); same tooling gap noted in Pass 1 — not an implementation concern. 21 tests exercise all branches of run().

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| #1 — run() callable + pyproject entry | `test_run_is_callable_in_main`, `test_pyproject_has_cockpit_script_entry` | Yes | COVERED |
| #2 — uvicorn host=127.0.0.1, port=8420 | `test_run_invokes_uvicorn_with_default_port`, `test_run_binds_to_localhost` | Yes — exact call_args kwargs asserted | COVERED |
| #2 — COCKPIT_PORT env var | `test_run_uses_cockpit_port_env_var` | Yes | COVERED |
| #2 (revised) — port 1–65535 | `test_run_exits_on_non_integer_port`, `test_run_exits_on_port_zero`, `test_run_exits_on_port_above_max` | Yes | COVERED |
| #2 — port boundaries | `test_run_accepts_port_boundary_low`, `test_run_accepts_port_boundary_high` | Yes | COVERED |
| #3 — static mount inside run() | `test_static_files_not_mounted_at_module_import`, `test_static_files_mounted_after_run` | Yes | COVERED |
| #4 — catch-all serves index.html | `test_catchall_route_serves_index_html_for_spa_paths` | Yes (strengthened) | COVERED |
| #5 — browser open, COCKPIT_NO_OPEN, non-fatal | 3 tests | Yes | COVERED |
| #6 — graceful shutdown | N/A (uvicorn default) | N/A | COVERED |
| #7 — dist/ missing | `test_run_exits_with_error_if_dist_missing` | Yes | COVERED |
| #8 — KanbanEngine init, order, missing dir | 4 tests | Yes | COVERED |

AC #4 assertion (the Pass 1 FAIL from prior review) confirmed strengthened in test file:

```python
assert resp.headers.get("content-type", "").startswith("text/html")
assert "<html" in resp.text.lower()
```

`HTMLResponse("x")` would fail this — assertion is now STRONG.

#### Security Review

No issues found:

- Port validated 1–65535 before use in URL (main.py:43)
- dist_dir derived from `__file__`, not user input — no path traversal
- kanban_dir (from KANBAN_DIR env var) passed to KanbanEngine only — no direct file ops
- Binds 127.0.0.1 only (main.py:83)
- Browser failure swallowed via contextlib.suppress(Exception) — non-fatal
- No hardcoded secrets, no insecure deserialization, no new external deps

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_catchall_route_serves_index_html_for_spa_paths | `len(resp.text) > 0` → `content-type startswith text/html` + `"<html" in resp.text.lower()` | STRENGTHENED |
| All other 20 tests | No changes | PRESERVED |

No WEAKENED or REMOVED tests detected.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact integers, exact host string, isinstance checks, content-type header, HTML structure check, call_args verification |
| Error-path coverage | STRONG | sys.exit tests for non-integer, port 0, port 65536, dist/ missing, kanban/ missing |
| Mutation reasoning | STRONG | Flipping `1 <= port <= 65535` breaks port boundary tests; removing catch-all breaks AC #4 content-type check |
| Test independence | STRONG | autouse _reset_app_after_run restores routes and clears app.state.engine |
| Test names | STRONG | All descriptive — fully express intent |

#### Data Safety

No issues. Sequential init path; contextlib.suppress on timer callback; no unbounded input; no LLM output persistence.

#### Implementation-Aware Test Gaps

Informational only (beyond AC scope, no deduction):

- StaticFiles(directory=dist_dir/"assets") raises RuntimeError if assets/ absent from otherwise valid dist/ — no test for partial build
- _spa_catchall calls .read_text() without try/except — dist/ without index.html → unhandled FileNotFoundError

Both noted in Pass 1 review; neither introduced in retry cycle; not flagged as defects.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A — 2nd pass confirmed test-writer fix, no impl change needed |
| Assessment | FRICTION (informational; retry was prompted by reviewer-directed test fix, not an implementation loop) |

### Pass 2 — INFORMATIONAL

- None

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| #1 — run() + pyproject entry | main.py:30 `def run()`, pyproject.toml:13 `cockpit = "owlbear_cockpit.main:run"` | test_run_is_callable_in_main, test_pyproject_has_cockpit_script_entry | PASS |
| #2 — host=127.0.0.1, port=8420 default | main.py:36 `_DEFAULT_PORT=8420`, main.py:83 `uvicorn.run(app, host="127.0.0.1", port=port)` | test_run_invokes_uvicorn_with_default_port, test_run_binds_to_localhost | PASS |
| #2 — COCKPIT_PORT | main.py:36 `os.environ.get("COCKPIT_PORT", ...)` | test_run_uses_cockpit_port_env_var | PASS |
| #2 (revised) — port validation 1–65535 | main.py:37–44 ValueError catch + range check | 3 port validation tests | PASS |
| #3 — static mount inside run() | main.py:73–76 mount + catch-all defined inside run() body | test_static_files_not_mounted_at_module_import, test_static_files_mounted_after_run | PASS |
| #4 — catch-all serves index.html | main.py:74–76 `@app.get("/{path:path}")` → HTMLResponse(index.html content) | test_catchall_route_serves_index_html_for_spa_paths | PASS |
| #5 — browser + COCKPIT_NO_OPEN + non-fatal | main.py:79–87 threading.Timer + contextlib.suppress + env check | 3 browser tests | PASS |
| #6 — graceful shutdown | uvicorn default behavior, no code needed | N/A | PASS |
| #7 — dist/ missing error | main.py:57–63 is_dir check + sys.exit(1) | test_run_exits_with_error_if_dist_missing | PASS |
| #8 — KanbanEngine init + app.state.engine + missing dir | main.py:47–55 (kanban dir), main.py:65–68 (engine + state) | 4 KanbanEngine tests | PASS |

### Confidence: .93

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `uv run cockpit` launch command + env vars added to `copilot-instructions.md` section 4 (Cockpit Backend); `test_cockpit_launch.py` added to test scope |
| 2 | Module docstrings | Yes | Verified | `main.py`: module docstring ✓, `health()` ✓, `run()` ✓ — all accurate, no changes needed |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already has "Cockpit Launch Command (Task #937)" section with 4 external sources — no update needed |
| 4 | CLI changes | Yes | Updated | Added `## Cockpit` section to `README.md` with `uv run cockpit` usage, build prerequisite, and env var table |
| 5 | Research doc | Yes | Verified | `.owlbear/research/937-cockpit-launch-command.md` exists and is linked in task body |

### Files Updated

- `.github/copilot-instructions.md` — added `Launch` row + `test_cockpit_launch.py` to test scope in Cockpit Backend table
- `README.md` — added `## Cockpit` section with launch command, build step, and env var table

### Scratch Files Cleaned

- None (no `.owlbear/scratch/937-*` files found)

### Commit

1a97fb52 — `docs: add uv run cockpit launch docs (#937, doc-writer)`
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| #1 — run() callable + pyproject entry | main.py:37 `def run()`, pyproject.toml:16 `cockpit = "owlbear_cockpit.main:run"` | PASS |
| #2 — uvicorn host=127.0.0.1, port=8420 | main.py:21 `_DEFAULT_PORT=8420`, main.py:87 `uvicorn.run(app, host="127.0.0.1", port=port)` | PASS |
| #2 — COCKPIT_PORT env var | main.py:40 `os.environ.get("COCKPIT_PORT", ...)` | PASS |
| #2 (revised) — port validation 1–65535 | main.py:41–47 ValueError catch + range check | PASS |
| #3 — static mount inside run() | main.py:73–76 mount + catch-all inside run() body | PASS |
| #4 — catch-all serves index.html | main.py:76 HTMLResponse, test assertion strengthened (content-type + `<html`) | PASS |
| #5 — browser open + COCKPIT_NO_OPEN + non-fatal | main.py:79–87 Timer + suppress + env check | PASS |
| #6 — graceful shutdown | uvicorn default | PASS |
| #7 — dist/ missing error | main.py:57–63 is_dir check + sys.exit(1) | PASS |
| #8 — KanbanEngine init + app.state.engine + missing dir | main.py:47–55, 65–68 | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all in mcp-knowledge — pre-existing, unrelated to #937)
- ruff: clean (0 violations)

### Architect Quality: 4/5

AC was specific and verifiable across all 8 lines. Architecture review added 3 refinements (AC #8 engine init, AC #5 COCKPIT_NO_OPEN, AC #2 port validation) via challenge process. Minor gap: no AC for partial-build edge cases (informational, beyond scope).

### Deduction Breakdown

- No deductions. All AC lines have specific evidence; lint clean; no task-scope failures; reviewer evidence detailed and present; AC quality > 3.

### Confidence: 1.00

### Action: archive
