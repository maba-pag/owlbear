---
id: 536
title: Lazy-singleton OwlBearSettings in cli.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:41.3865662+01:00
updated: 2026-03-19T15:43:14.8414162+01:00
started: 2026-03-07T00:29:37.413524+01:00
completed: 2026-03-19T15:43:08.6697438+01:00
tags:
    - audit
    - dry
    - scope:cli
depends_on:
    - 481
    - 807
class: standard
---

DRY-05: OwlBearSettings() instantiated 13 times across 7 bearclaw/commands/ modules. pydantic-settings re-reads env vars each time. See docs/research/lazy-singleton-settings.md

**Approach:** functools.cache getter (.90 confidence) in owlbear/config.py. Replace 13 call sites, update 32 test patch targets.

**AC:**

- [ ] `get_settings() -> OwlBearSettings` with `@functools.cache` in `owlbear/config.py`
- [ ] All 13 `OwlBearSettings()` calls in `bearclaw/commands/` replaced with `get_settings()` (auth:1, browser:2, chat:1, daemon:3, knowledge_source:1, project:3, slack:1, usage:1)
- [ ] 32 test patch targets updated from `bearclaw.commands.{module}.OwlBearSettings` to `owlbear.config.OwlBearSettings`
- [ ] Autouse fixture in `tests/conftest.py` calls `get_settings.cache_clear()` after each test
- [ ] All existing CLI tests pass
- [ ] ruff clean

[[2026-03-14]] Sat 21:01

## Architecture Review

See docs/scratch/536-architect.md for full review.

[[2026-03-15]] Sun 04:46

## Test-Writer Notes

- Test file: tests/test_lazy_singleton_settings.py
- Classes: TestFromAC_CallSiteReplacement, TestFromAC_UnifiedPatchTarget, TestFromAC_CacheClearFixture
- Tests per category: happy 19, edge 8, error 0, boundary 0
- Total: 27 tests, all FAIL
- ruff: clean
- AC coverage:
  - get_settings import in each command module (8 parametrized)
  - No direct OwlBearSettings() calls in modules (8 parametrized)
  - OwlBearSettings not re-exported per-module (8 parametrized)
  - conftest.py imports get_settings (1)
  - conftest.py has cache_clear in source (1)
  - conftest.py autouse fixture calls cache_clear (1)

[[2026-03-15]] Sun 05:50

## Builder Notes

- Files changed: 8 command modules (auth, browser, chat, daemon, knowledge_source, project, slack, usage), tests/conftest.py, 10 test files (patch targets)
- Implementation: Replaced 13 OwlBearSettings() calls with get_settings() across 8 modules. Moved OwlBearSettings to TYPE_CHECKING where type annotations needed (chat, slack). Added autouse cache_clear fixture to conftest.py. Updated 52 test patch targets.
- Tests: 27 passed (test_lazy_singleton_settings), 236+ passed across affected CLI tests
- Lint: ruff clean
- Pre-existing failures: 4 hydration_integration (bootstrap unpacking), 1 trafilatura regex  confirmed on clean main

[[2026-03-15]] Sun 06:03

## Review Evidence

Tests: 319 passed, 0 failed (27 TestFromAC + 97 CLI + 195 other affected)
Lint: ruff clean on all 22 files
Coverage: config.py 65% (get_settings covered; missed lines pre-existing)
Security: No issues (mechanical replacements only)
TestFromAC: All 27 preserved, 0 weakened/removed
Test quality: 4 STRONG, 1 ADEQUATE, 0 WEAK
AC: All 6 lines PASS (13 callsites, 50 patch targets, autouse fixture, CLI tests pass, ruff clean)
Verdict: PASS | Confidence: .95

[[2026-03-15]] Sun 06:13

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added get_settings() singleton note to Config row in tech stack table |
| 2 | Docstrings complete | Yes | Pass | get_settings() at config.py:519 has full docstring (purpose + cache_clear usage) |
| 3 | sources/overview.md | Yes | Pass | Already has FastAPI Settings + Typer Callback rows (added during research, line 355+) |
| 4 | README.md | No | N/A | No CLI command changes, internal refactoring only |
| 5 | Research doc linked | Yes | Pass | docs/research/lazy-singleton-settings.md exists, linked in task body |

### Files Updated

- .github/copilot-instructions.md (Config row: added get_settings() singleton convention)

### Scratch Files Cleaned

- None (no docs/scratch/536-* files found)

[[2026-03-17]] Tue 17:25
## Audit

### AC Verification

| # | AC Line | Evidence | Status |
|---|---------|----------|--------|
| 1 | get_settings() with @functools.cache in config.py | config.py L524-534: @functools.cache decorator + OwlBearSettings() return. Docstring documents cache_clear(). Impl from dep #807 (f9c8fff). | PASS |
| 2 | All 13 OwlBearSettings() calls replaced with get_settings() | grep confirms zero OwlBearSettings() calls remain in bearclaw/commands/. Count: auth(1), browser(2), chat(1), daemon(3), ks(1), project(3), slack(1), usage(1) = 13. TYPE_CHECKING-only imports in chat.py + slack.py (correct). | PASS |
| 3 | 32 test patch targets updated to owlbear.config.OwlBearSettings | 20+ targets confirmed via grep. Builder reports 52 updated. **1 MISSED: test_client_cleanup.py:235 still patches bearclaw.commands.chat.OwlBearSettings.** | FAIL |
| 4 | Autouse fixture calls get_settings.cache_clear() | conftest.py L120-122: @pytest.fixture(autouse=True) _clear_settings_cache() calls get_settings.cache_clear(). | PASS |
| 5 | All existing CLI tests pass | **BLOCKED**: Circular import from #814 (604b2df, Mar 16) breaks all CLI test collection. Pre-existing in committed code, not caused by #536. Builder verified on Mar 15 before #814 landed. | BLOCKED |
| 6 | ruff clean | No ruff errors from #536 changes. Pre-existing BLE001 in auth.py (from #532). | PASS |

### Test Results

- pytest (task-specific): 26/27 passed. 1 failure = circular import from #814 (pre-existing).
- pytest (CLI suite): collection errors on all 7 test files due to pre-existing circular import (#814).
- ruff: 0 errors introduced by #536. Pre-existing BLE001 (auth.py) + RUF100 (conftest.py WMI workaround, separate task).

### Process Gaps

1. **Builder did not commit deliverables.** chat.py, daemon.py, usage.py, conftest.py, and test files remain uncommitted.
2. **Missed patch target**: test_client_cleanup.py:235 still uses old bearclaw.commands.chat.OwlBearSettings target.
3. Pre-existing circular import from #814 blocks full AC5 verification.

### Confidence: .85
### Action: reject to review

[[2026-03-17]] Tue 17:40
## Review Evidence (reviewer, cycle 2)

### Test Results
- pytest: 26 passed, 1 failed (test_lazy_singleton_settings.py)
- The 1 failure is `test_module_imports_get_settings[bearclaw.commands.auth]`  circular import from #814 (`tools/__init__.py` re-exports). Pre-existing, not caused by #536.
- CLI test collection entirely blocked by same #814 circular import (AC5 unverifiable).

### Lint Results
- ruff: 0 errors introduced by #536. 3 pre-existing (BLE001 auth.py, 2x RUF100 conftest.py WMI workaround).

### Coverage
- config.py: 65% (get_settings L532 missed  structural tests don't invoke it. Pre-existing uncovered validators.)

### Pass 1 -- CRITICAL

#### Security Review
- No hardcoded secrets, no injection vectors, no path traversal
- No insecure deserialization, no eval/exec
- No new dependencies added
- No secret leakage in logs/errors
- Finding: CLEAN

#### Test Integrity (TestFromAC comparison)
File is untracked (never committed by test-writer or builder). Test-writer notes describe 3 classes, 27 tests. Current file matches: 3 TestFromAC classes (CallSiteReplacement, UnifiedPatchTarget, CacheClearFixture), 27 tests total. All method names and assertion patterns correspond to the test-writer AC coverage table.

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_CallSiteReplacement (8+8 parametrized) | No change | PRESERVED |
| TestFromAC_UnifiedPatchTarget (8 parametrized) | No change | PRESERVED |
| TestFromAC_CacheClearFixture (3 tests) | No change | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AST-based structural checks verify exact absence of OwlBearSettings() calls, exact presence of get_settings imports, autouse fixture with cache_clear |
| Negative/error paths | ADEQUATE | Tests verify absence (no direct calls, no re-exports) but no error-path tests (N/A for a refactoring task) |
| Mutation reasoning | STRONG | Reverting any callsite to OwlBearSettings() triggers test_no_direct_owlbearsettings_instantiation; removing get_settings import triggers test_module_imports_get_settings |
| Test independence | STRONG | Each parametrized case imports module independently; conftest autouse fixture clears cache |
| Descriptive names | STRONG | test_module_imports_get_settings, test_no_direct_owlbearsettings_instantiation, test_conftest_has_autouse_fixture_with_cache_clear |

#### Data Safety
- No data safety issues found (mechanical replacement, no new I/O)

### Pass 2 -- INFORMATIONAL
- config.py get_settings() coverage at 65%  the structural tests don't invoke it directly. Not blocking (suppression #9: pre-existing uncovered code).
- Builder deliverables still uncommitted (chat.py, daemon.py, usage.py, conftest.py, test file). Process gap, not AC violation.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| (1) get_settings() with @functools.cache in config.py | config.py L524-534: @functools.cache + return OwlBearSettings() | TestFromAC_CacheClearFixture | PASS |
| (2) All 13 OwlBearSettings() calls replaced | grep: 0 matches for OwlBearSettings() in bearclaw/commands/; get_settings() calls at auth:60, browser:30+45, chat:119, daemon:24+56+139, ks:31, project:27+92+129, slack:34, usage:25 = 13 | TestFromAC_CallSiteReplacement | PASS |
| (3) Test patch targets updated | grep: 1 stale target remains at test_client_cleanup.py:235 (`bearclaw.commands.chat.OwlBearSettings`). Since chat.py imports OwlBearSettings under TYPE_CHECKING only, this mock is INEFFECTIVE at runtime. | TestFromAC_UnifiedPatchTarget (does not cover external test files) | **FAIL** |
| (4) Autouse fixture calls cache_clear | conftest.py L120-123: @pytest.fixture(autouse=True) _clear_settings_cache() calls get_settings.cache_clear() | TestFromAC_CacheClearFixture::test_conftest_has_autouse_fixture_with_cache_clear | PASS |
| (5) All existing CLI tests pass | BLOCKED: circular import from #814 prevents CLI test collection. Pre-existing, not caused by #536. | (unverifiable) | BLOCKED |
| (6) ruff clean | 0 new ruff errors from #536 files | (structural check) | PASS |

### Rejection Detail
| Gap | Required Fix |
|---|---|
| AC3: stale patch target at test_client_cleanup.py:235 | Change `bearclaw.commands.chat.OwlBearSettings` to `owlbear.config.OwlBearSettings`. The current mock is inert because chat.py moved OwlBearSettings to TYPE_CHECKING. |
| AC5: CLI tests blocked by #814 circular import | Not caused by #536 but unverifiable. Builder should confirm #814 fix is tracked separately. |

### Verdict: FAIL (confidence .80)

[[2026-03-17]] Tue 21:29
## Test-Writer Notes (cycle 2)
- Test file: tests/test_lazy_singleton_settings.py
- Added class: TestFromAC_TestFilePatchTargets (2 tests)
- Tests per category: happy 0, edge 0, error 2, boundary 0
- Total new: 2 tests, all FAIL (test_client_cleanup.py:235 caught by both)
- ruff: clean
- AC coverage: AC3 stale-patch-target gap now covered

[[2026-03-17]] Tue 22:08
## Builder Notes
- Files changed: tests/test_client_cleanup.py
- Tests: 29 passed (tests/test_lazy_singleton_settings.py); 15 passed (tests/test_client_cleanup.py)
- Coverage: scoped pytest --cov run completed for tests/test_lazy_singleton_settings.py (overall 17% workspace coverage; task file fully green)
- Lint: ruff check passed on tests/test_client_cleanup.py and tests/test_lazy_singleton_settings.py
- Evidence: RED before fix (2 failing tests for stale patch target in test_client_cleanup.py:235). GREEN after fix (29/29 passing).
- Fixes applied: Replaced stale patch target 'bearclaw.commands.chat.OwlBearSettings' with 'owlbear.config.OwlBearSettings' in tests/test_client_cleanup.py.

[[2026-03-17]] Tue 22:47
## Review Evidence (reviewer, cycle 3)

### Test Results
- pytest (task-specific): 29 passed, 0 failed (test_lazy_singleton_settings.py)
- pytest (CLI suite): 96 passed (chat, auth, browser, daemon, project, knowledge_source)
- pytest (additional affected): 30 passed (voice, client_cleanup)
- Total: 155 passed, 0 failed. Circular import from #814 is resolved.

### Lint Results
- ruff: 0 new errors from #536. 3 pre-existing (BLE001 auth.py, 2x RUF100 conftest.py).

### Coverage
- config.py: 66% (missed lines are pre-existing validators; get_settings at L531 covered. Suppression #9.)

### Pass 1 -- CRITICAL

#### Security Review
- CLEAN. No secrets, injection, path traversal, or new deps.

#### Test Integrity (TestFromAC comparison)
All 4 TestFromAC classes (29 tests) PRESERVED. 0 weakened/removed.

#### Test Quality
- Assertion specificity: STRONG
- Negative/error paths: ADEQUATE (N/A for refactoring)
- Mutation reasoning: STRONG
- Test independence: STRONG
- Descriptive names: STRONG

#### Data Safety
- No issues (mechanical replacement, no new I/O)

### Pass 2 -- INFORMATIONAL
- config.py coverage 66%: structural tests don't invoke get_settings directly. Pre-existing.

### AC Compliance
All 6 AC lines PASS. Stale patch target in test_client_cleanup.py:235 fixed. CLI tests now pass (155 total, 0 failed).

### Verdict: PASS | Confidence: .93

[[2026-03-18]] Wed 13:39
## Builder Notes (cycle 3)
- Files changed: src/bearclaw/commands/chat.py, daemon.py, usage.py, tests/test_cli_browser.py, test_cli_chat.py, test_cli_daemon.py, test_cli_project.py, test_cli_status_rich.py, test_client_cleanup.py, tests/test_lazy_singleton_settings.py
- Commit: d05a926 (feat: lazy-singleton get_settings() in CLI commands (#536, builder))
- Tests: 29 passed (test_lazy_singleton_settings.py); 111 passed (CLI suite); ruff clean on all task files (2 pre-existing RUF100 in conftest.py WMI workaround)
- Coverage: config.py 66% (structural tests); get_settings() validated by structural checks
- All AC verified green

[[2026-03-18]] Wed 14:04
## Review Evidence (reviewer, cycle 4)

### Test Results
- Command: `uv run pytest tests/test_cli.py tests/test_cli_auth.py tests/test_cli_browser.py tests/test_cli_chat.py tests/test_cli_daemon.py tests/test_cli_decisions.py tests/test_cli_error_helper.py tests/test_cli_knowledge_source.py tests/test_cli_project.py tests/test_cli_status_rich.py tests/test_cli_voice.py tests/test_usage_cli.py tests/test_client_cleanup.py tests/test_lazy_singleton_settings.py -q --tb=short`
- Result: 279 passed, 0 failed, 10 warnings
- Warnings are optional-dependency skips from `tests/conftest.py` (numpy/qdrant not installed), not task regressions.

### Lint Results
- Repo command: `uv run ruff check src/ tests/`
- Repo result: 7 errors in unrelated pre-existing files (`src/bearclaw/commands/auth.py`, `src/owlbear/tools/screenshot.py`, `tests/conftest.py`, `tests/test_blocked_error_location.py`, `tests/test_loop_detection.py`).
- Commit-scoped command: `uv run ruff check src/bearclaw/commands/chat.py src/bearclaw/commands/daemon.py src/bearclaw/commands/usage.py tests/test_cli_browser.py tests/test_cli_chat.py tests/test_cli_daemon.py tests/test_cli_project.py tests/test_cli_status_rich.py tests/test_client_cleanup.py tests/test_lazy_singleton_settings.py`
- Commit-scoped result: All checks passed.

### Coverage
- Command: `uv run pytest <same 14 files> --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- Result: 279 passed, 0 failed, 10 warnings.
- Focused report command: `uv run coverage report -m src/bearclaw/commands/auth.py src/bearclaw/commands/browser.py src/bearclaw/commands/chat.py src/bearclaw/commands/daemon.py src/bearclaw/commands/knowledge_source.py src/bearclaw/commands/project.py src/bearclaw/commands/slack.py src/bearclaw/commands/usage.py src/owlbear/config.py`
- Coverage:
  - `auth.py` 100%
  - `browser.py` 100%
  - `chat.py` 90%
  - `daemon.py` 100%
  - `knowledge_source.py` 90%
  - `project.py` 100%
  - `slack.py` 100%
  - `usage.py` 99%
  - `config.py` 82% (pre-existing uncovered validator branches outside this task's changed files)

### Pass 1 -- CRITICAL

#### Security Review
- Hardcoded secrets: none in reviewed task files.
- Injection vectors: no new SQL/shell/template injection paths introduced; command changes are settings-access rewires.
- Path traversal: no user-controlled path construction newly introduced.
- Insecure deserialization/eval/exec: none introduced.
- Input validation boundary regressions: none found for changed command behavior.
- Dependency risk: no new dependencies.
- Secret leakage in logs/errors: none introduced.

#### Test Integrity (TestFromAC comparison)
- Git integrity check:
  - `git ls-files -- tests/test_lazy_singleton_settings.py` => tracked
  - `git log --oneline -- tests/test_lazy_singleton_settings.py` => commit `d05a926`

| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_CallSiteReplacement::test_module_imports_get_settings` (parametrized 8 modules) | Present with same intent and strict hasattr check | PRESERVED |
| `TestFromAC_CallSiteReplacement::test_no_direct_owlbearsettings_instantiation` (parametrized 8 modules) | Present with AST-based call detection | PRESERVED |
| `TestFromAC_UnifiedPatchTarget::test_owlbearsettings_not_in_module_namespace` (parametrized 8 modules) | Present with same namespace absence assertion | PRESERVED |
| `TestFromAC_CacheClearFixture::test_conftest_imports_get_settings` | Present | PRESERVED |
| `TestFromAC_CacheClearFixture::test_conftest_source_contains_cache_clear` | Present | PRESERVED |
| `TestFromAC_CacheClearFixture::test_conftest_has_autouse_fixture_with_cache_clear` | Present (AST fixture scan) | PRESERVED |
| `TestFromAC_TestFilePatchTargets::test_no_stale_per_module_patch_targets_in_test_suite` | Present | PRESERVED |
| `TestFromAC_TestFilePatchTargets::test_test_client_cleanup_uses_correct_patch_target` | Present | PRESERVED |

No WEAKENED or REMOVED TestFromAC assertions found.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AST parsing and exact string checks assert concrete migration properties, not loose truthy checks. |
| Negative/error paths | ADEQUATE | Includes explicit stale-target absence checks and namespace-negation checks; task is structural refactor with limited runtime error branches. |
| Mutation reasoning | STRONG | Reintroducing any `OwlBearSettings()` call or old patch target is directly caught by dedicated tests. |
| Test independence | STRONG | Parametrized module checks are self-contained; autouse fixture clears settings cache between tests. |
| Descriptive names | STRONG | Test names encode scenario + expected constraint clearly. |

#### Data Safety
- No data-safety regressions found (no new multi-step persistence, no new shared mutable state races, no unbounded input paths introduced by this task).

### Pass 2 -- INFORMATIONAL
- Global ruff baseline is not green in this workspace due unrelated files; task/commit files are lint-clean.
- `tests/conftest.py` contains pre-existing `RUF100` `noqa` directives unrelated to this task's accepted behavior.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. `get_settings() -> OwlBearSettings` with `@functools.cache` in `owlbear/config.py` | `src/owlbear/config.py:531` (`@functools.cache`) and `src/owlbear/config.py:532` (`def get_settings() -> OwlBearSettings`) | `TestFromAC_CacheClearFixture::test_conftest_imports_get_settings` | PASS |
| 2. All 13 `OwlBearSettings()` callsites replaced in listed command modules | Direct count check: `DIRECT_OWLBEARSETTINGS_CALLS=0`; `GET_SETTINGS_CALLS=13` across `auth, browser, chat, daemon, knowledge_source, project, slack, usage` | `TestFromAC_CallSiteReplacement::*` | PASS |
| 3. 32 test patch targets updated to `owlbear.config.OwlBearSettings` | `NEW_PATCH_CALL_COUNT=32`; `OLD_OWLBEARSETTINGS_PATCH_CALL_COUNT=0`; `tests/test_client_cleanup.py:235` uses new target | `TestFromAC_UnifiedPatchTarget::*`; `TestFromAC_TestFilePatchTargets::*` | PASS |
| 4. Autouse fixture in `tests/conftest.py` calls `get_settings.cache_clear()` | `tests/conftest.py:120` autouse fixture and `tests/conftest.py:123` cache clear call | `TestFromAC_CacheClearFixture::test_conftest_has_autouse_fixture_with_cache_clear` | PASS |
| 5. All existing CLI tests pass | Scoped CLI run over 14 CLI/singleton-related files: 279 passed, 0 failed | Full command in Test Results | PASS |
| 6. ruff clean | Commit-scoped lint on all #536 changed files: All checks passed; no new lint regressions from task | Commit-scoped ruff command in Lint Results | PASS |

### Verdict: PASS (confidence .93)

### Action Taken
- Review evidence appended
- Next command: move task status `review -> docs` and release claim

[[2026-03-19]] Thu 14:32
## Docs Gate (cycle 2)
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Pass | get_settings() singleton convention in Config row (.github/copilot-instructions.md L49) - added in cycle 1 |
| 2 | Docstrings complete | Yes | Pass | get_settings() at config.py L532 has full docstring (purpose + cache_clear usage) |
| 3 | sources/overview.md | Yes | Pass | Task #536 section at docs/sources/overview.md lines 395-400 (FastAPI Settings + Typer Callback) |
| 4 | README.md | No | N/A | No CLI command changes, internal refactoring only |
| 5 | Research doc linked | Yes | Pass | docs/research/lazy-singleton-settings.md exists, linked in task body |
| 6 | No impact | N/A | N/A | Items 1-5 applicable |

### Files Updated
- None (all docs updates from cycle 1 remain valid; no new gaps found)

### Scratch Files Cleaned
- None (no docs/scratch/536-* files found)

[[2026-03-19]] Thu 15:43
## Audit (cycle 2)
### AC Verification
| # | AC Line | Evidence | Status |
|---|---------|----------|--------|
| 1 | get_settings() with @functools.cache in config.py | config.py L531-539: @functools.cache decorator, returns OwlBearSettings(), docstring documents cache_clear(). | PASS |
| 2 | All 13 OwlBearSettings() calls replaced | grep: 0 OwlBearSettings() in bearclaw/commands/. 13 get_settings() calls: auth(1), browser(2), chat(1), daemon(3), ks(1), project(3), slack(1), usage(1). TYPE_CHECKING imports in chat.py + slack.py correct. | PASS |
| 3 | 32 test patch targets updated | grep: 0 stale bearclaw.commands.*.OwlBearSettings targets in tests. 20+ owlbear.config.OwlBearSettings targets confirmed. test_client_cleanup.py:235 uses correct target. | PASS |
| 4 | Autouse fixture calls cache_clear | conftest.py L120-122: @pytest.fixture(autouse=True) _clear_settings_cache() calls get_settings.cache_clear(). | PASS |
| 5 | All existing CLI tests pass | 217 passed, 0 failed across 12 CLI+singleton test files. | PASS |
| 6 | ruff clean | 0 new ruff errors from #536 files. 1 pre-existing BLE001 in auth.py. | PASS |

### Test Results
- pytest (task-specific): 217 passed, 0 failed (12 CLI + singleton test files)
- Cross-task: 17 failures in bootstrap tests, all pre-existing (TextChunker import, slack_sdk), unrelated to #536
- ruff: 0 new errors from #536

### Commit Verification
- Builder commit d05a926: 10 files (3 src + 7 tests), well-scoped
- Docs: get_settings() convention in copilot-instructions.md L49
- Research doc: docs/research/lazy-singleton-settings.md exists

### Confidence: .97
### Action: archive
