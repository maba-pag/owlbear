---
id: 861
title: Tests for deprecation-free PydanticAI bootstrap model fixtures (#556)
status: archived
priority: nice-to-have
created: 2026-03-19T17:22:21.5869592+01:00
updated: 2026-03-20T16:59:45.0941954+01:00
started: 2026-03-20T16:59:22.6047809+01:00
completed: 2026-03-20T16:59:22.6047809+01:00
tags:
    - audit
    - test
class: standard
---

## Acceptance Criteria

- [ ] In `tests/test_bootstrap.py`, add class `TestFromAC_BuildToolsetsNoBareModelDeprecation` with targeted regression tests that call `build_toolsets()` through the `chat_model or settings.chat_model` fallback in `src/owlbear/bootstrap/toolsets.py` and execute the covered call under `DeprecationWarning`-as-error handling.
- [ ] In `tests/test_knowledge_query_service_expansion.py`, add `test_build_toolsets_expansion_path_no_bare_model_deprecation` that exercises the knowledge-graph expansion wiring path through `build_toolsets()` under the same `DeprecationWarning`-as-error handling.
- [ ] The new RED tests are runnable in isolation with `uv run pytest tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation -W error::DeprecationWarning`.
- [ ] Before #556 implementation, that targeted pytest selection fails because the covered callsites still rely on the bare-string model fallback; unrelated existing failures in these files are out of scope for #861.
- [ ] Keep scope test-only: no `src/`, config, or dependency files change under #861.
- [ ] Ruff clean on touched test files.

## Notes

- `bootstrap()` in `src/owlbear/bootstrap/__init__.py` now creates `OpenAIChatModel(settings.chat_model, provider=provider)` inline after `create_copilot_client()`. Do not add new RED coverage that patches `owlbear.bootstrap.create_copilot_model` on a `bootstrap()` path.
- The live deprecation surface still present in the codebase is the `chat_model or settings.chat_model` fallback inside `src/owlbear/bootstrap/toolsets.py`.
- Existing `MagicMock(spec=Model)` usage in `tests/test_agent.py` remains the fixture pattern to follow if a PydanticAI model double is needed.

[[2026-03-20]] Fri 12:00

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| In `tests/test_bootstrap.py`, add `TestFromAC_BootstrapModelFixturesNoDeprecation` covering a `bootstrap()` path that patches `owlbear.bootstrap.create_copilot_model` | Stale against the current assembly root: `bootstrap()` in `src/owlbear/bootstrap/__init__.py` now creates `OpenAIChatModel(...)` inline after `create_copilot_client()` and does not exercise `create_copilot_model` | Rewrote to remove the obsolete bootstrap fixture path |
| In `tests/test_bootstrap.py`, add `TestFromAC_BuildToolsetsNoBareModelDeprecation` covering representative `build_toolsets()` callsites | Correct live warning surface, but `representative` was too vague to verify mechanically | Rewrote with an explicit class name and isolated pytest node selection |
| In `tests/test_knowledge_query_service_expansion.py`, add or update a regression test for the expansion wiring path under the same filter | Valid scope, but it needed an exact test name and a requirement to route through `build_toolsets()` instead of helper signatures that already fail for unrelated reasons | Rewrote |
| Existing happy-path assertions remain green apart from the new RED failures | Not mechanically verifiable because these files already have unrelated failures today | Replaced with isolated-node execution criteria |
| All new tests FAIL (RED) before #556 implementation when run with `uv run pytest tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py -W error::DeprecationWarning` | The referenced full-file command already fails for unrelated reasons, so it cannot prove that only the new RED tests are failing | Rewrote to a targeted pytest selection |
| Ruff clean on touched test files | Clear and verifiable | Kept |

### Architecture Notes

Codebase check changed the scope here. The remaining live deprecation path is the `chat_model or settings.chat_model` fallback in `src/owlbear/bootstrap/toolsets.py`. The earlier research and original AC still assumed `bootstrap()` patched `create_copilot_model`, but current `bootstrap()` wiring in `src/owlbear/bootstrap/__init__.py` creates the model inline after `create_copilot_client()`.

The existing fixture precedent for PydanticAI model doubles is still `MagicMock(spec=Model)` in `tests/test_agent.py`, so that note stays relevant if the RED tests need a model double. The expansion file also has unrelated helper drift today (`_build_knowledge_infra()` callsites that no longer match the current signature), which is why the verification contract had to move from a whole-file pytest command to explicit node IDs.

This remains a single-domain test task and still serves as the RED predecessor for #556, but only after narrowing the AC to the current warning-producing surface.

### Changes Made

- Rewrote #861 acceptance criteria to remove the stale `bootstrap()`/`create_copilot_model` assumption
- Added exact new test identifiers and a targeted pytest command for RED verification
- Preserved the test-only scope and Ruff gate
- Left the task in `backlog` for re-dispatch with tightened AC

### Dependencies

- Verified: #556 exists in `todo` and depends on #861
- Verified: `tests/test_agent.py` contains the established `MagicMock(spec=Model)` fixture pattern
- Verified: no `src/` changes belong in #861

[[2026-03-20]] Fri 13:12

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add `TestFromAC_BuildToolsetsNoBareModelDeprecation` in `tests/test_bootstrap.py` covering `build_toolsets()` through the `chat_model or settings.chat_model` fallback under `-W error::DeprecationWarning` | Precise against the live warning source in `src/owlbear/bootstrap/toolsets.py`; class-level node selection keeps the RED contract stable without coupling to a specific helper name | Keep |
| Add `test_build_toolsets_expansion_path_no_bare_model_deprecation` in `tests/test_knowledge_query_service_expansion.py` | Exact seam and exact node ID for the expansion wiring path that still reaches `build_toolsets()` | Keep |
| New RED tests runnable in isolation with the targeted pytest selection | Mechanical verification command that avoids unrelated failures already present elsewhere in these files | Keep |
| Before #556 implementation, the targeted selection fails because the covered callsites still use the bare-string fallback | Valid RED gate and scoped failure expectation tied to the current deprecation surface | Keep |
| Keep scope test-only with no `src/`, config, or dependency changes | Preserves atomicity and matches the archived source-level cleanup split | Keep |
| Ruff clean on touched test files | Clear quality gate | Keep |

### Architecture Notes

The current task body is sufficiently precise to move forward. The live deprecation surface is the `chat_model or settings.chat_model` fallback in `src/owlbear/bootstrap/toolsets.py`, and the notes correctly exclude the obsolete `bootstrap()` / `create_copilot_model` path now that `src/owlbear/bootstrap/__init__.py` constructs `OpenAIChatModel(...)` inline after `create_copilot_client()`.

This remains a single-domain RED test task for #556. The title still reflects the earlier bootstrap-fixture framing, but the acceptance criteria and notes now define the implementation contract unambiguously, so no further backlog refinement is needed.

### Changes Made

- `kanban\kanban-md.exe edit 861 --claim architect`
- `kanban\kanban-md.exe edit 861 -a ... -t --claim architect`
- `kanban\kanban-md.exe edit 861 --status todo --release`

### Dependencies

- Verified: #556 depends on #861 as its RED predecessor
- Verified: `tests/test_knowledge_query_service_expansion.py` still has a `build_toolsets()` wiring seam to cover
- Verified: no split required; task remains single-domain and test-only

[[2026-03-20]] Fri 13:41

## Test-Writer Notes

- Test files: tests/test_bootstrap.py, tests/test_knowledge_query_service_expansion.py
- Classes: TestFromAC_BuildToolsetsNoBareModelDeprecation (test_bootstrap.py)
- Standalone: test_build_toolsets_expansion_path_no_bare_model_deprecation (test_knowledge_query_service_expansion.py)
- Tests per category: happy 0, edge 0, error 0, boundary 4
- Total: 4 tests, all FAIL (AssertionError: isinstance(str, Model) is False)
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| TestFromAC_BuildToolsetsNoBareModelDeprecation in test_bootstrap.py via chat_model or settings.chat_model fallback | test_knowledge_infra_receives_model_not_bare_string, test_knowledge_toolset_receives_model_not_bare_string, test_bookmark_toolset_receives_model_not_bare_string | boundary |
| test_build_toolsets_expansion_path_no_bare_model_deprecation in test_knowledge_query_service_expansion.py with knowledge_graph_expansion=True | test_build_toolsets_expansion_path_no_bare_model_deprecation | boundary |
| Runnable with -W error::DeprecationWarning (4 fail, 0 pass) | all 4 | boundary |
| Test-only scope — no src/ changes | verified | n/a |
| Ruff clean | verified | n/a |

[[2026-03-20]] Fri 14:23

## Builder Notes

- Files changed: tests/test_bootstrap.py (ruff fixes only), tests/test_knowledge_query_service_expansion.py (no changes needed)
- Tests: 4 RED tests verified failing as expected (before #556), ruff clean
- Lint: ruff clean on both touched test files (fixed 11 pre-existing violations: D403x2, D209x3, D205x6)
- Evidence: 4 FAILED with AssertionError: isinstance('gpt-4o', Model) is False
- Fixes applied: ruff --fix (D403x2, D209x3) + manual D205x6 (single-line docstring rewrites) + ruff format
- Scope: test-only, no src/ changes (AC constraint respected)

[[2026-03-20]] Fri 15:15

## Review Evidence

## Review: #861 - Tests for deprecation-free PydanticAI bootstrap model fixtures (#556)

### Test Results

- pytest command: uv run pytest tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation -W error::DeprecationWarning -q --tb=short
- Result: 4 failed, 0 passed (expected RED pre-#556)
- Failure evidence: assertions fail on bare string 'gpt-4o' at tests/test_bootstrap.py:2901, tests/test_bootstrap.py:2936, tests/test_bootstrap.py:2970, and tests/test_knowledge_query_service_expansion.py:715 under -W error::DeprecationWarning.

### Lint Results

- ruff command: uv run ruff check tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py
- Result: All checks passed.

### Coverage

- Command run: uv run pytest tests/test_bootstrap.py::TestFromAC_BuildToolsetsNoBareModelDeprecation tests/test_knowledge_query_service_expansion.py::test_build_toolsets_expansion_path_no_bare_model_deprecation -W error::DeprecationWarning --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: command executed successfully; expected RED failures remained (4 failed). Coverage report emitted (overall 23% for this scoped failing run).
- Applicability note: task is test-only with no src changes in #861, so module coverage threshold is non-blocking for this review gate.

### Pass 1 - CRITICAL

#### Security Review

- No hardcoded secrets, injection vectors, path traversal, insecure deserialization, dependency risk, or secret leakage introduced in touched tests.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_infra_receives_model_not_bare_string | Present in final file; strict isinstance(captured[0], Model) assertion retained at tests/test_bootstrap.py:2901 | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_knowledge_toolset_receives_model_not_bare_string | Present in final file; strict isinstance(captured[0], Model) assertion retained at tests/test_bootstrap.py:2936 | PRESERVED |
| TestFromAC_BuildToolsetsNoBareModelDeprecation::test_bookmark_toolset_receives_model_not_bare_string | Present in final file; strict isinstance(captured[0], Model) assertion retained at tests/test_bootstrap.py:2970 | PRESERVED |
| test_build_toolsets_expansion_path_no_bare_model_deprecation | Present in final file; strict isinstance(captured[0], Model) assertion retained at tests/test_knowledge_query_service_expansion.py:715 | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Each test asserts exact call capture count and strict Model type (tests/test_bootstrap.py:2900-2901, 2935-2936, 2969-2970; tests/test_knowledge_query_service_expansion.py:714-715). |
| Negative/error paths | STRONG | RED-path tests intentionally validate current failing fallback behavior pre-#556 and fail for the expected reason (bare string model). |
| Mutation reasoning | STRONG | If fallback/argument wiring regresses (wrong type, missing call, altered callsite), len/type assertions fail immediately. |
| Test independence | STRONG | Tests use local fixtures/mocks/patch contexts; no shared mutable global state. |
| Descriptive names | STRONG | Method/function names clearly encode scenario and expectation (no generic names). |

#### Data Safety

- No data safety risks introduced (tests only, no persistence writes, no shared concurrent mutation).

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Add TestFromAC_BuildToolsetsNoBareModelDeprecation in tests/test_bootstrap.py with targeted build_toolsets regression coverage through fallback under DeprecationWarning-as-error handling | Class and three tests exist at tests/test_bootstrap.py:2869, 2885, 2906, 2941; strict Model assertions at tests/test_bootstrap.py:2901, 2936, 2970; targeted pytest run executed with -W error::DeprecationWarning | test_knowledge_infra_receives_model_not_bare_string; test_knowledge_toolset_receives_model_not_bare_string; test_bookmark_toolset_receives_model_not_bare_string | PASS |
| Add test_build_toolsets_expansion_path_no_bare_model_deprecation in tests/test_knowledge_query_service_expansion.py under same warning handling | Test exists at tests/test_knowledge_query_service_expansion.py:665; expansion enabled at tests/test_knowledge_query_service_expansion.py:687; strict Model assertion at tests/test_knowledge_query_service_expansion.py:715; targeted pytest run executed with -W error::DeprecationWarning | test_build_toolsets_expansion_path_no_bare_model_deprecation | PASS |
| New RED tests runnable in isolation with targeted pytest selection and -W error::DeprecationWarning | Command executed exactly; node selection ran and produced deterministic output for all four tests | all 4 tests above | PASS |
| Before #556 implementation, targeted selection fails because callsites still rely on bare-string fallback | pytest failures explicitly show captured bare string 'gpt-4o'; live fallback remains in src/owlbear/bootstrap/toolsets.py:87, :109, :134 | all 4 tests above | PASS |
| Keep scope test-only: no src/config/dependency changes under #861 | git show --name-only --oneline f1e3aa4 lists only tests/test_bootstrap.py and tests/test_knowledge_query_service_expansion.py | n/a | PASS |
| Ruff clean on touched test files | uv run ruff check tests/test_bootstrap.py tests/test_knowledge_query_service_expansion.py -> All checks passed | n/a | PASS |

### Verdict: PASS

- Confidence: .96

### Action Taken

- kanban\\kanban-md.exe edit 861 --status docs --release

[[2026-03-20]] Fri 16:08

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only scope; no behavior, API, or convention change |
| 2 | Docstrings | No | N/A | No src/ modules touched; task is test-only per AC |
| 3 | sources/overview.md | No | N/A | No external patterns adopted; followed existing MagicMock(spec=Model) precedent already in codebase |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

**No docs impact.** Pure test-only task: 4 RED tests added in tests/test_bootstrap.py and tests/test_knowledge_query_service_expansion.py.

### Files Updated

- None

### Scratch Files Cleaned

- None (no scratch files existed for #861)

[[2026-03-20]] Fri 16:59

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_BuildToolsetsNoBareModelDeprecation in test_bootstrap.py | Class at L2869 with 3 tests (L2885, L2906, L2941); isinstance(Model) assertions at L2901, L2936, L2970; all 3 FAIL with bare string 'gpt-4o' | PASS |
| test_build_toolsets_expansion_path_no_bare_model_deprecation in test_knowledge_query_service_expansion.py | Function at L665; knowledge_graph_expansion=True at L687; isinstance(Model) assertion at L715; FAILS with bare string 'gpt-4o' | PASS |
| New RED tests runnable in isolation with -W error::DeprecationWarning | Targeted pytest command: 4 FAILED, 0 passed | PASS |
| Before #556, targeted selection fails because callsites use bare-string fallback | All 4 tests fail with isinstance('gpt-4o', Model) is False | PASS |
| Keep scope test-only: no src/config/dependency changes | Commit f1e3aa4 touches only tests/test_bootstrap.py and tests/test_knowledge_query_service_expansion.py | PASS |
| Ruff clean on touched test files | uv run ruff check -> All checks passed | PASS |

### Test Results

- Targeted RED tests: 4 FAILED, 0 passed (expected pre-#556)
- Full suite: 3665 passed, 112 failed (pre-existing; numpy compat, bootstrap signature drift, import errors - none from #861)
- ruff: All checks passed on touched files

### Confidence: .97

### Action: archive

[[2026-03-20]] Fri 16:59

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_BuildToolsetsNoBareModelDeprecation in test_bootstrap.py | Class at L2869 with 3 tests (L2885, L2906, L2941); isinstance(Model) assertions at L2901, L2936, L2970; all 3 FAIL with bare string 'gpt-4o' | PASS |
| test_build_toolsets_expansion_path_no_bare_model_deprecation in test_knowledge_query_service_expansion.py | Function at L665; knowledge_graph_expansion=True at L687; isinstance(Model) assertion at L715; FAILS with bare string 'gpt-4o' | PASS |
| New RED tests runnable in isolation with -W error::DeprecationWarning | Targeted pytest command: 4 FAILED, 0 passed | PASS |
| Before #556, targeted selection fails because callsites use bare-string fallback | All 4 tests fail with isinstance('gpt-4o', Model) is False | PASS |
| Keep scope test-only: no src/config/dependency changes | Commit f1e3aa4 touches only tests/test_bootstrap.py and tests/test_knowledge_query_service_expansion.py | PASS |
| Ruff clean on touched test files | uv run ruff check -> All checks passed | PASS |

### Test Results

- Targeted RED tests: 4 FAILED, 0 passed (expected pre-#556)
- Full suite: 3665 passed, 112 failed (pre-existing; numpy compat, bootstrap signature drift, import errors - none from #861)
- ruff: All checks passed on touched files

### Confidence: .97

### Action: archive

[[2026-03-20]] Fri 16:59

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| d096475 | chore | kanban/tasks/861-*.md | #861 |
