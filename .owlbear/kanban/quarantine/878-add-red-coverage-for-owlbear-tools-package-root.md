---
id: 878
title: Add RED coverage for owlbear.tools package-root lazy exports
status: archived
priority: important
created: 2026-03-20T16:03:40.0551697+01:00
updated: 2026-03-21T03:41:09.8821892+01:00
started: 2026-03-21T03:41:05.5151239+01:00
completed: 2026-03-21T03:41:05.5151239+01:00
tags:
    - test
    - architecture
    - bug
    - scope:tools
    - type:test
parent: 859
class: standard
---

This is the RED child task for #859 and the test predecessor for #879. Keep it scoped to coverage for package-root lazy exports in src/owlbear/tools/__init__.py.

## AC

- [ ] Update tests/test_tools_init_reexports.py only; do not change src/owlbear/tools/__init__.py in this task.
- [ ] Add a clean-subprocess import-side-effect test using the existing repo pattern of subprocess.run([sys.executable, -c, ...], capture_output=True, text=True, check=False).
- [ ] The new subprocess test imports owlbear.tools in a fresh interpreter and asserts owlbear.tools.github_api and owlbear.core.retry are absent from sys.modules after the bare package import.
- [ ] On the current tree, the new subprocess side-effect assertion fails because src/owlbear/tools/__init__.py eagerly imports the package-root re-exports.
- [ ] Preserve the #814 compatibility contract in tests/test_tools_init_reexports.py: the 10 supported package-root imports, canonical identity checks, exact __all__ surface, and from owlbear.tools import GitHubToolset coverage remain present.
- [ ] Do not assert GREEN implementation details such as _LAZY_IMPORTS structure, importlib caching mechanics, or __getattr__ internals in this RED task.
- [ ] uv run ruff check tests/test_tools_init_reexports.py passes.
- [ ] uv run pytest tests/test_tools_init_reexports.py -q --tb=short fails on the current tree because of the new package-root side-effect assertion, not because the #814 compatibility checks were removed or weakened.

## Research

- Doc: docs/research/tools-root-lazy-exports-red-coverage.md
- Attribution updated: docs/sources/overview.md now logs the Python import docs, Python data model docs, PEP 562, and Scientific Python SPEC 1 used for this task.
- Clean-process evidence: bare import owlbear.tools currently loads owlbear.tools.github_api and owlbear.core.retry, while preserving the 10-name __all__ surface.
- RED recommendation: extend tests/test_tools_init_reexports.py with one clean-subprocess sys.modules side-effect class using the subprocess pattern from tests/test_knowledge_exports.py and tests/test_blocked_url_error_location.py.
- Preserve the existing #814 contract unchanged: the 10 import, identity, and __all__ checks remain the compatibility guard for from owlbear.tools import GitHubToolset and the other package-root exports.
- Do not encode importlib or cache internals in #878; those are GREEN implementation concerns for #879.
- __dir__ parity is optional, not part of the core RED/GREEN split.

- Follow-up task already created: #883 Preserve dir() parity for owlbear.tools lazy exports.
- Verdict: #878 is the correct atomic RED task and does not need splitting.

[[2026-03-20]] Fri 18:02

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Original one-line AC combined test file placement, subprocess behavior, compatibility preservation, and subprocess precedent | Correct scope but not mechanically verifiable as written | Rewrote into 8 discrete RED-phase AC lines |
| Bare import owlbear.tools leaves owlbear.tools.github_api and owlbear.core.retry absent from sys.modules | This is the live failing behavior caused by the eager imports in src/owlbear/tools/__init__.py | Kept and made it an explicit fresh-process assertion |
| The existing 10-symbol API from #814 remains covered | This is the compatibility contract already encoded in tests/test_tools_init_reexports.py | Kept and pinned to the existing import, identity, and __all__ checks |
| Use tests/test_knowledge_exports.py as the subprocess pattern | Valid repo precedent; tests/test_blocked_url_error_location.py uses the same clean-process shape for import regressions | Kept as pattern guidance without constraining GREEN internals |

### Architecture Notes

- src/owlbear/tools/__init__.py currently imports GitHubToolset and the other public names at module import time, so a fresh-process sys.modules assertion is the right RED check for the live regression.
- tests/test_tools_init_reexports.py already holds the #814 compatibility contract for the 10 supported package-root names, so extending that file is the smallest consistent change.
- tests/test_knowledge_exports.py and tests/test_blocked_url_error_location.py establish the clean-subprocess pattern already used in this repo for import side-effect checks.
- This task is single-domain and test-only. It should not modify src/owlbear/tools/__init__.py or encode the GREEN implementation shape for #879.
- Failure mode map: not applicable for a RED test task; it adds coverage rather than a new runtime codepath.

### Changes Made

- Rewrote #878 into a discrete RED-phase contract with verifiable AC.
- Kept the task scoped to tests/test_tools_init_reexports.py and the existing package-root compatibility coverage.
- Approved the task to todo as the RED predecessor for #879.

### Dependencies

- Added/Removed/Verified: verified parent tracker #859 defines the #878 (RED) -> #879 (GREEN) execution path; verified #814 remains the compatibility contract being preserved; no split needed.

## Test-Writer Notes - Test file: tests/test_tools_init_reexports.py - New class: TestFromAC_ToolsImportSideEffect - 1 new test FAILS (github_api eagerly loaded), 25 existing PASS - ruff clean - All 8 AC lines covered

[[2026-03-21]] Sat 02:38

## Review Evidence

## Review: #878 — Add RED coverage for owlbear.tools package-root lazy exports

### Test Results

- Command: `uv run pytest tests/test_tools_init_reexports.py -q --tb=short`
- Result: 25 passed, 1 failed (expected RED)
- Failing test: `TestFromAC_ToolsImportSideEffect::test_bare_import_does_not_load_github_api_or_retry`
- Failure evidence: `AssertionError: owlbear.tools.github_api eagerly loaded by bare import` at tests/test_tools_init_reexports.py:224

### Lint Results

- Command: `uv run ruff check tests/test_tools_init_reexports.py`
- Result: All checks passed.

### Coverage

- Command: `uv run pytest tests/test_tools_init_reexports.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- Relevant module evidence: `src/owlbear/tools/__init__.py 11 0 100%`
- Note: global TOTAL is low because bare `--cov` reports full project scope per repo config.

### Pass 1 — CRITICAL

#### Security Review

- Hardcoded secrets: none found in changed test/source scope.
- Injection: subprocess call uses fixed literal `-c` script and `sys.executable`; no user input interpolation.
- Path traversal: none (no filesystem path handling in change).
- Insecure deserialization/eval: none.
- Input validation boundaries: not applicable (static test content only).
- Dependency risk: no dependency changes.
- Secret leakage in logs/errors: failure message reports module names only, no sensitive data.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_ToolsReExports::*` (10 tests, lines 12-57) | No assertion/method changes in diff | PRESERVED |
| `TestFromAC_ToolsReExportIdentity::*` (10 tests, lines 66-120) | No assertion/method changes in diff | PRESERVED |
| `TestFromAC_ToolsAllTuple::*` (4 tests, lines 145-162) | No assertion/method changes in diff | PRESERVED |
| `TestFromAC_NoCircularImport::test_import_owlbear_tools_exposes_all_symbols` | No assertion/method changes in diff | PRESERVED |
| `TestFromAC_ToolsImportSideEffect::test_bare_import_does_not_load_github_api_or_retry` | Added new RED subprocess side-effect assertion | STRENGTHENED |

No WEAKENED/REMOVED TestFromAC assertions detected.

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Import smoke checks are broad, but identity and exact `__all__` tests enforce strict API shape, and subprocess assertion checks exact module side effect. |
| Negative/error paths | STRONG | New subprocess test asserts forbidden modules in `sys.modules` and intentionally fails on current eager-import behavior. |
| Mutation reasoning | STRONG | If eager import remains, new test fails; if exported symbols or identities change, existing identity/`__all__` tests fail. |
| Test independence | STRONG | No shared mutable fixtures/state; tests perform isolated imports/subprocess execution. |
| Descriptive names | STRONG | Test names describe scenario + expected behavior (e.g. `test_bare_import_does_not_load_github_api_or_retry`). |

#### Data Safety

- No data integrity risks found (no persistence, no shared mutable runtime path, no unbounded external input).

### Pass 2 — INFORMATIONAL

- Minor note: simple `is not None` import checks are lighter than identity checks, but they are already backed by strict identity tests in the same file.
- Scope check command `git diff --name-only -- tests/test_tools_init_reexports.py src/owlbear/tools/__init__.py` shows only `tests/test_tools_init_reexports.py` changed; `git diff -- src/owlbear/tools/__init__.py` is empty.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Update `tests/test_tools_init_reexports.py` only; no `src/owlbear/tools/__init__.py` changes | `git diff --name-only -- tests/test_tools_init_reexports.py src/owlbear/tools/__init__.py` -> only test file; `git diff -- src/owlbear/tools/__init__.py` -> empty | N/A (scope constraint) | PASS |
| Add clean-subprocess side-effect test using existing pattern (`subprocess.run([...], capture_output=True, text=True, check=False)`) | `tests/test_tools_init_reexports.py:208-223` | `TestFromAC_ToolsImportSideEffect::test_bare_import_does_not_load_github_api_or_retry` | PASS |
| Fresh interpreter import asserts `owlbear.tools.github_api` and `owlbear.core.retry` absent | Assertions at `tests/test_tools_init_reexports.py:214-217` | `TestFromAC_ToolsImportSideEffect::test_bare_import_does_not_load_github_api_or_retry` | PASS |
| Current tree fails due eager package-root imports | Pytest failure: `AssertionError: owlbear.tools.github_api eagerly loaded by bare import` at `tests/test_tools_init_reexports.py:224` | Same as above | PASS |
| Preserve #814 compatibility contract (10 imports, identity checks, exact `__all__`, `from owlbear.tools import GitHubToolset`) | Import coverage lines `12-57`, identity lines `66-120`, `EXPECTED_NAMES` at `130-143`, `from owlbear.tools import GitHubToolset` at `28` and `85`; pytest shows 25 pass | `TestFromAC_ToolsReExports::*`, `TestFromAC_ToolsReExportIdentity::*`, `TestFromAC_ToolsAllTuple::*`, `TestFromAC_NoCircularImport::*` | PASS |
| Do not assert GREEN internals (`_LAZY_IMPORTS`, cache mechanics, `__getattr__`) | No such assertions in file; grep only finds generic importlib module import at `179-181` | N/A (constraint) | PASS |
| `uv run ruff check tests/test_tools_init_reexports.py` passes | Ruff output: `All checks passed!` | N/A | PASS |
| `uv run pytest tests/test_tools_init_reexports.py -q --tb=short` fails for new side-effect assertion, not weakened #814 checks | Output: `1 failed, 25 passed`; only failing test is new side-effect test | New side-effect test fails, 25 compatibility tests pass | PASS |

### Verdict: PASS

Confidence: .96
