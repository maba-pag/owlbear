---
id: 868
title: Create leaf markdown extraction helper for cross-layer callers
status: archived
priority: nice-to-have
created: 2026-03-20T13:53:19.4355036+01:00
updated: 2026-03-23T06:42:44.9958866+01:00
started: 2026-03-23T06:41:47.7453504+01:00
completed: 2026-03-23T06:41:47.7453504+01:00
tags:
    - dry
    - type:build
    - scope:core
    - phase-9
depends_on:
    - 874
class: standard
---

Prerequisite discovered during research for #825 and relevant to downstream consumer tasks #825 and #873. Implement the GREEN-phase leaf helper introduced by #874 by adding package-root module src/owlbear/web_extract.py with extract_markdown(html, url=None). Source: docs/research/leaf-markdown-extraction-helper.md.

AC:

1. src/owlbear/web_extract.py exports extract_markdown(html: str, url: str | None = None) -> str as a package-root leaf helper and imports no owlbear.core, owlbear.tools, owlbear.memory, owlbear.agents, owlbear.config, wrapping helpers, or settings helpers.
2. extract_markdown lazy-imports trafilatura on first call and raises an actionable ImportError with an install hint when the dependency is unavailable.
3. On success, extract_markdown delegates exactly once to trafilatura.extract(html, output_format=markdown, include_links=True, url=url) and returns the raw string result without wrapping or metadata decoration.
4. When trafilatura.extract returns None or raises during extraction, extract_markdown returns an empty string and does not surface the extraction exception.
5. This task does not migrate existing callers; bookmark_pipeline/context_hydration/content_extractor rewires stay in #825, #873, and #875, and the focused RED tests from #874 pass.

[[2026-03-20]] Fri 14:59

## Research

- Research doc: docs/research/leaf-markdown-extraction-helper.md
- External attribution updated: docs/sources/overview.md
- Key finding: archived task #537 was too broad; extract_content remains correct for tools-layer callers, but core/ and memory/ need a package-root raw helper because they cannot legally import from tools/.
- Key finding: the helper should own only lazy optional-dependency import plus trafilatura.extract(markdown/include_links/url) and empty-string fallback; metadata extraction and wrap_web_content stay outside it.
- Existing downstream chain: #867/#825 for bookmark_pipeline and #869/#873 for context_hydration already capture the consumer RED/GREEN work once #868 exists.
- Follow-up created: #874 - Add RED tests for owlbear.web_extract.extract_markdown
- Follow-up created: #875 - Refactor content_extractor to reuse web_extract.extract_markdown
- Command executed: kanban\kanban-md.exe create Add RED tests for owlbear.web_extract.extract_markdown -> #874
- Command executed: kanban\kanban-md.exe create Refactor content_extractor to reuse web_extract.extract_markdown -> #875

[[2026-03-20]] Fri 15:20

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) src/owlbear/web_extract.py exists as a leaf module | Needed the public API and import boundary spelled out so the builder cannot add higher-layer imports. | Rewrote body AC to require a single exported leaf function with no owlbear higher-layer or settings imports. |
| (2) extract_markdown centralizes the markdown extraction call | Missing the exact trafilatura contract and lazy optional-dependency behavior. | Rewrote body AC to require lazy import, actionable ImportError, and the exact markdown/include_links/url call shape. |
| (3) helper output is raw and unwrapped | Needed an explicit no-metadata/no-wrapping constraint to avoid duplicating tools-layer behavior. | Rewrote body AC to require raw string output and keep wrapping/metadata out of scope. |
| (4) focused tests pass | As written it bundled RED and GREEN. The implementation task needs a paired test task and a clear handoff. | Added dependency on #874 and rewrote the AC as a GREEN-phase pass condition. |

### Architecture Notes

Leaf-module precedent already exists in src/owlbear/paths.py. src/owlbear/tools/browser/content_extractor.py is not a legal reuse target for lower layers because it imports OwlBearSettings and wrapping logic, while src/owlbear/memory/knowledge/bookmark_pipeline.py and src/owlbear/core/context_hydration.py currently duplicate only the raw trafilatura.extract(...) contract that this helper should centralize. Keep #868 limited to the new leaf helper; consumer rewires stay in #825, #873, and #875.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| extract_markdown() | optional dependency missing | ImportError | Yes - actionable install hint | Caller gets a clear setup error on first use |
| extract_markdown() | trafilatura.extract returns None | none | Yes - returns empty string | Caller sees no extracted content |
| extract_markdown() | trafilatura.extract raises | implementation-defined upstream exception | Yes - returns empty string | Caller sees no extracted content |

### Changes Made

- Rewrote #868 body AC as a GREEN-phase contract tied to the research doc.
- Added dependency on #874 so the helper cannot be implemented before its paired RED task.
- Kept bookmark_pipeline, context_hydration, and content_extractor rewires out of scope for this task.

### Dependencies

- Added: #874 (paired RED tests for this helper)
- Verified downstream: #825, #873, #875

[[2026-03-21]] Sat 15:39

## Builder Notes

- Files changed: src/owlbear/web_extract.py (already implemented)
- Tests: 13 passed (tests/test_web_extract.py), coverage 100% on web_extract.py
- Lint: ruff check clean, ruff format clean
- Evidence: 13 passed in 0.10s; web_extract.py 17 stmts 0 miss 100%
- Fixes applied: None - module correctly implemented; all TestFromAC_* tests pass green

[[2026-03-21]] Sat 16:27

## Review Evidence

## Review: #868 - Create leaf markdown extraction helper for cross-layer callers

### Test Results

- Command: uv run pytest tests/test_web_extract.py -q --tb=short
- Result: 13 passed, 0 failed (2 optional-dependency warnings from tests/conftest.py).

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: FAIL (451 findings in unrelated existing files).
- Scoped check for this task: uv run ruff check src/owlbear/web_extract.py tests/test_web_extract.py -> All checks passed.

### Coverage

- Command: uv run pytest tests/test_web_extract.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: src/owlbear/web_extract.py = 100% (17 statements, 0 missed).

### Pass 1 - CRITICAL

#### Security Review

- Hardcoded secrets: none.
- Injection/path traversal/insecure deserialization/eval/exec: none.
- Dependency risk: no new dependency added.
- Sensitive-data leakage in errors/logs: none.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| TestFromAC_ExtractMarkdownSuccess::test_returns_extracted_markdown | No change (git diff 165702d..HEAD shows no changes in tests/test_web_extract.py) | PRESERVED |
| TestFromAC_ExtractMarkdownSuccess::test_calls_trafilatura_with_correct_kwargs | No change | PRESERVED |
| TestFromAC_ExtractMarkdownSuccess::test_exactly_one_trafilatura_extract_call | No change | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_default_url_is_none | No change | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_provided_url_forwarded_unchanged | No change | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_url_forwarding_does_not_affect_return_value | No change | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_returns_empty_string_when_extract_returns_none | No change | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_returns_empty_string_when_extract_raises | No change | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_does_not_surface_extraction_exception | No change | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_empty_string_not_none_on_none_extract | No change | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_raises_import_error_when_trafilatura_missing | No change | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_import_error_contains_owlbear_search_install_hint | No change | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_import_error_message_references_uv | No change | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Exact kwargs/call-count assertions exist (tests/test_web_extract.py:41, tests/test_web_extract.py:53, tests/test_web_extract.py:69). |
| Negative/error paths | STRONG | Dedicated None/exception/missing-dependency coverage (tests/test_web_extract.py:106, tests/test_web_extract.py:113, tests/test_web_extract.py:146). |
| Mutation reasoning | WEAK | AC2 requires first-call lazy import, but no test asserts that module import itself does not attempt trafilatura import; current implementation can violate AC2 while all tests still pass. |
| Test independence | STRONG | Patch-based isolation per test; no shared mutable fixtures. |
| Descriptive names | STRONG | Test names are scenario-specific and explicit. |

#### Data Safety

- No data-safety risks found (no persistence, no shared mutable cross-thread state, no unbounded resource processing introduced).

### Pass 2 - INFORMATIONAL

- None.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| 1. Leaf helper exports extract_markdown and avoids prohibited owlbear layer imports | src/owlbear/web_extract.py:7, src/owlbear/web_extract.py:10, src/owlbear/web_extract.py:14, src/owlbear/web_extract.py:17 | tests/test_web_extract.py (module-level helper scope and function usage) | PASS |
| 2. Lazy-import trafilatura on first call with actionable ImportError when missing | Implementation performs module-load import attempt (`import trafilatura`) at src/owlbear/web_extract.py:9-12, so import is not first-call lazy when dependency is present; actionable ImportError message exists at src/owlbear/web_extract.py:41-44 | Missing dedicated first-call-lazy assertion in tests/test_web_extract.py | FAIL |
| 3. Success delegates exactly once to trafilatura.extract(...markdown/include_links/url) and returns raw string | src/owlbear/web_extract.py:47-52, src/owlbear/web_extract.py:56; exact call assertions in tests/test_web_extract.py:41-46 and tests/test_web_extract.py:53 | test_calls_trafilatura_with_correct_kwargs; test_exactly_one_trafilatura_extract_call; test_returns_extracted_markdown | PASS |
| 4. None/exception fallback returns empty string without surfacing extraction errors | src/owlbear/web_extract.py:53-56 with tests/test_web_extract.py:106-127 | test_returns_empty_string_when_extract_returns_none; test_returns_empty_string_when_extract_raises; test_does_not_surface_extraction_exception | PASS |
| 5. No caller migrations in this task; focused RED tests from #874 pass | Commit 38dc077 touches only src/owlbear/web_extract.py; scoped pytest command passes 13/13 | tests/test_web_extract.py (entire suite) | PASS |

### Rejection Table

| Gap | Evidence | Required Fix |
| --- | --- | --- |
| AC2 violation: import is not first-call lazy | src/owlbear/web_extract.py:9-12 performs module-load import attempt | Move trafilatura import fully into extract_markdown() call path (or equivalent true lazy strategy) so import is first attempted only when extract_markdown is invoked. |
| Missing regression test for lazy-import timing | All current tests pass despite module-load import attempt | Add a TestFromAC case that verifies importing owlbear.web_extract does not attempt trafilatura import; assert first import attempt happens when extract_markdown is called. |

### Verdict: FAIL

- Confidence: .86

[[2026-03-22]] Sun 22:18

## Test-Writer Notes (retry)

- Retry reason: reviewer cited missing test — lazy-import timing (AC2) not asserted
- Added: 2 new failing tests in TestFromAC_ExtractMarkdownLazyImport
  - test_module_load_does_not_call_import_for_trafilatura
  - test_first_trafilatura_import_attempt_is_inside_extract_markdown
- Preserved: 13 existing tests (all PASS)
- Evidence: uv run pytest tests/test_web_extract.py -> 2 failed, 13 passed
- Failure reason: web_extract.py has eager module-level  ry: import trafilatura (lines 9-12)
- ruff: clean (scoped check)
- AC2 coverage gap now addressed: module-load must not attempt trafilatura import

[[2026-03-22]] Sun 23:11

## Builder Notes (retry)

- Files changed: src/owlbear/web_extract.py (removed eager module-level import, replaced with trafilatura = None sentinel)
- Tests: 15 passed (tests/test_web_extract.py), coverage 100% on web_extract.py (16 stmts, 0 missed)
- Lint: ruff clean on src/owlbear/web_extract.py; 2 ruff findings in tests/test_web_extract.py (E501 L251, SIM117 L291 - inside TestFromAC_ExtractMarkdownLazyImport, test-writer artifact, cannot modify per builder rules)
- Evidence: 15 passed in 0.12s; web_extract.py 16 stmts 0 miss 100%
- Fix: Removed try/import block at module scope; trafilatura = None until extract_markdown is first called

[[2026-03-23]] Mon 00:08

## Review Evidence

## Review: #868 - Create leaf markdown extraction helper for cross-layer callers

### Test Results

- Command: uv run pytest tests/test_web_extract.py -q --tb=short
- Result: 15 passed, 0 failed, 2 warnings (optional dependency skips in tests/conftest.py)

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: FAIL (253 existing repo-wide findings; baseline debt outside this task)
- Scoped command: uv run ruff check src/owlbear/web_extract.py tests/test_web_extract.py
- Result: FAIL (2 task-scoped findings):
  - E501 at tests/test_web_extract.py:251
  - SIM117 at tests/test_web_extract.py:291

### Coverage

- Command: uv run pytest tests/test_web_extract.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: src/owlbear/web_extract.py = 100% (16 statements, 0 missed)

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| 1) Export helper + keep leaf import boundary | tests/test_web_extract.py imports and calls extract_markdown (e.g., lines 15, 31) | Export/name drift: Yes; forbidden higher-layer import drift: No direct assertion | LAX |
| 2) Lazy import + actionable ImportError | TestFromAC_ExtractMarkdownLazyImport::test_module_load_does_not_call_import_for_trafilatura; TestFromAC_ExtractMarkdownLazyImport::test_first_trafilatura_import_attempt_is_inside_extract_markdown; TestFromAC_ExtractMarkdownMissingDependency::* | Yes | COVERED |
| 3) Exactly one delegate call with exact kwargs + raw return | test_calls_trafilatura_with_correct_kwargs; test_exactly_one_trafilatura_extract_call; test_returns_extracted_markdown | Yes | COVERED |
| 4) None/exception fallback returns empty string and suppresses extraction errors | test_returns_empty_string_when_extract_returns_none; test_returns_empty_string_when_extract_raises; test_does_not_surface_extraction_exception | Yes | COVERED |
| 5) No caller migration in this task + focused RED tests pass | git show --name-only 38dc077 and 0ff00f7 (only src/owlbear/web_extract.py); scoped pytest 15/15 pass | Yes (scope drift via commit evidence + task test pass) | COVERED |

#### Security Review

- No hardcoded secrets, injection vectors, path traversal, unsafe deserialization, eval/exec, or sensitive logging paths found in src/owlbear/web_extract.py.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| 13 original TestFromAC methods from baseline 165702d | No assertion weakening/removal observed | PRESERVED |
| TestFromAC_ExtractMarkdownLazyImport::test_module_load_does_not_call_import_for_trafilatura | Added in retry | STRENGTHENED |
| TestFromAC_ExtractMarkdownLazyImport::test_first_trafilatura_import_attempt_is_inside_extract_markdown | Added in retry | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Strong exact-call assertions for extract kwargs/call count; one AC1 boundary assertion remains indirect only |
| Negative/error paths | STRONG | None-return, exception, and missing-dependency paths explicitly tested |
| Mutation reasoning | WEAK | Forbidden higher-layer import regressions for AC1 are not directly asserted by tests; suite can pass with boundary drift |
| Test independence | STRONG | Patch-based isolation; reload-based lazy-import tests restore state in finally blocks |
| Descriptive names | STRONG | Test names are explicit and scenario-specific |

#### Data Safety

- No persistence, atomicity, concurrency, or unbounded-input data-safety concerns introduced by this helper.

#### Implementation-Aware Test Gaps

- Runtime branching in src/owlbear/web_extract.py is broadly covered.
- Remaining gap: no direct regression test enforcing AC1 forbidden import boundary.

### Pass 2 - INFORMATIONAL

- src/owlbear/web_extract.py satisfies leaf-module shape and AC call contract:
  - **all** export at src/owlbear/web_extract.py:9
  - lazy import at src/owlbear/web_extract.py:38
  - actionable install hint at src/owlbear/web_extract.py:42
  - single extract call and fallback at src/owlbear/web_extract.py:47-56

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| 1. Leaf helper export and import boundary | src/owlbear/web_extract.py:9,14,17 and import scan | tests import/use helper; no direct forbidden-import assertion | FAIL |
| 2. Lazy import + actionable ImportError | src/owlbear/web_extract.py:38-44; lazy-import tests at tests/test_web_extract.py:209,250 and import-error tests at 148,164,179 | Multiple TestFromAC cases | PASS |
| 3. Exact delegate call + raw return | src/owlbear/web_extract.py:47-56; tests at tests/test_web_extract.py:38,51,31 | Success-path TestFromAC cases | PASS |
| 4. None/exception fallback behavior | src/owlbear/web_extract.py:53-56; tests at tests/test_web_extract.py:108,115,122 | Fallback TestFromAC cases | PASS |
| 5. No caller migration + focused RED tests pass | git show --name-only 38dc077 and 0ff00f7 only touch src/owlbear/web_extract.py; scoped pytest 15 passed | test_web_extract suite | PASS |

### Blocking Findings

- Scoped lint fails in task files ( ests/test_web_extract.py: E501 at line 251, SIM117 at line 291).
- AC1 import-boundary regression protection is not directly asserted in tests (TestFromAC coverage rated LAX; mutation reasoning WEAK).

### Verdict: FAIL

- Confidence: .88

### Action Taken

- Pending status move to todo via reviewer gate.

[[2026-03-23]] Mon 00:50

## Test-Writer Notes (retry 2)

- Retry reason: lint failures (E501 L251, SIM117 L291) in test file + reviewer FAIL on AC1 import-boundary (no regression test)
- Fixed: E501 at line 251 (wrapped long docstring), SIM117 at line 291 (merged nested with)
- Added: TestFromAC_ImportBoundary::test_web_extract_has_no_forbidden_owlbear_layer_imports (static AST regression guard)
- AC1 test PASSES (implementation already satisfies no-forbidden-import contract; test is a regression guard)
- Preserved: 15 existing tests (all PASS)
- Total: 16 tests, ruff: clean
- Note: AC1 test is a static analysis guard that passes today but fails if a forbidden owlbear import is added to web_extract.py

[[2026-03-23]] Mon 04:13

## Builder Notes (retry 2 verification)

- Files changed: tests/test_web_extract.py (trivial formatting only — path expression unwrapped)
- Tests: 16 passed (tests/test_web_extract.py), coverage 100% on web_extract.py (16 stmts, 0 missed)
- Lint: ruff clean on src/owlbear/web_extract.py and tests/test_web_extract.py
- Evidence: 16 passed in 0.11s; web_extract.py 16 stmts 0 miss 100%
- Fixes applied: No src/ changes needed — implementation already satisfies AC1 (no forbidden imports) and AC2 (lazy import). TestFromAC_ImportBoundary passes immediately. Committed trivial path-expression formatting diff in test file.

[[2026-03-23]] Mon 05:28

## Review Evidence

## Review: #868 - Create leaf markdown extraction helper for cross-layer callers

### Test Results

- Command: uv run pytest tests/test_web_extract.py -q --tb=short
- Result: 16 passed, 0 failed, 2 warnings (optional dependency skip warnings from tests/conftest.py)

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: FAIL (244 existing repo-wide findings, mostly RUF100 in unrelated tests; baseline debt outside #868 scope)
- Scoped command: uv run ruff check src/owlbear/web_extract.py tests/test_web_extract.py
- Result: All checks passed

### Coverage

- Command: uv run pytest tests/test_web_extract.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: src/owlbear/web_extract.py = 100% (16 statements, 0 missed)

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: package-root helper + no forbidden imports | TestFromAC_ImportBoundary::test_web_extract_has_no_forbidden_owlbear_layer_imports | Yes - AST guard fails on prohibited owlbear.core/tools/memory/agents/config imports | COVERED |
| AC2: lazy import + actionable ImportError | TestFromAC_ExtractMarkdownLazyImport::{test_module_load_does_not_call_import_for_trafilatura,test_first_trafilatura_import_attempt_is_inside_extract_markdown} + TestFromAC_ExtractMarkdownMissingDependency::* | Yes - detects eager import and missing actionable error | COVERED |
| AC3: exact delegate call + raw return | TestFromAC_ExtractMarkdownSuccess::{test_returns_extracted_markdown,test_calls_trafilatura_with_correct_kwargs,test_exactly_one_trafilatura_extract_call} | Yes - asserts exact kwargs and call count | COVERED |
| AC4: None/exception fallback empty-string/no re-raise | TestFromAC_ExtractMarkdownFallback::{test_returns_empty_string_when_extract_returns_none,test_returns_empty_string_when_extract_raises,test_does_not_surface_extraction_exception} | Yes - verifies fallback behavior and exception suppression | COVERED |
| AC5: no caller migration + focused RED tests pass | tests/test_web_extract.py suite (16/16 pass) + commit scope evidence (38dc077,0ff00f7,7d4bd6c,fb1d711) | Yes - scope drift would appear in commit file lists; focused suite passes | COVERED |

#### Security Review

- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, eval/exec, or sensitive logging found in src/owlbear/web_extract.py.
- No dependency additions in #868 commits.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---|---|---|
| 13 baseline TestFromAC methods from commit 165702d | No weakening/removal; git diff 165702d..HEAD -- tests/test_web_extract.py shows only additions plus non-semantic formatting | PRESERVED |
| TestFromAC_ExtractMarkdownLazyImport::test_module_load_does_not_call_import_for_trafilatura | Added in retry cycle | STRENGTHENED |
| TestFromAC_ExtractMarkdownLazyImport::test_first_trafilatura_import_attempt_is_inside_extract_markdown | Added in retry cycle | STRENGTHENED |
| TestFromAC_ImportBoundary::test_web_extract_has_no_forbidden_owlbear_layer_imports | Added in retry cycle | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact kwargs/call-count checks and explicit import-tracking assertions (tests/test_web_extract.py:38,51,209,250,320) |
| Negative/error paths | STRONG | None-return, extraction exception, and missing dependency paths are explicitly tested (tests/test_web_extract.py:108,115,148) |
| Mutation reasoning | ADEQUATE | Eager-import mutation and forbidden-import mutation are caught; fallback and delegate mutations are covered |
| Test independence | STRONG | Patch/reload state is restored in finally; no shared mutable fixture coupling |
| Descriptive names | STRONG | Test names encode behavior and expected outcome clearly |

#### Data Safety

- No data-safety risks introduced (no persistence, concurrency, or unbounded-processing path changes).

#### Implementation-Aware Test Gaps

- No significant untested behavioral paths in extract_markdown; branches for lazy import, missing dependency, delegate call, None fallback, and exception fallback are covered.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. src/owlbear/web_extract.py exports extract_markdown(...) and avoids prohibited internal imports | src/owlbear/web_extract.py:9 (**all**), 17 (def extract_markdown); no from/import owlbear... matches; static boundary guard at tests/test_web_extract.py:320 | TestFromAC_ImportBoundary::test_web_extract_has_no_forbidden_owlbear_layer_imports | PASS |
| 2. Lazy import on first call + actionable ImportError | Lazy import at src/owlbear/web_extract.py:38; actionable hint at 42; missing-dependency raise at 40-44; lazy timing tests at tests/test_web_extract.py:209,250 | TestFromAC_ExtractMarkdownLazyImport::*, TestFromAC_ExtractMarkdownMissingDependency::* | PASS |
| 3. Exactly one delegate call with exact kwargs and raw return | Single delegate at src/owlbear/web_extract.py:47-52; raw return path at 56 | test_calls_trafilatura_with_correct_kwargs, test_exactly_one_trafilatura_extract_call, test_returns_extracted_markdown | PASS |
| 4. None/exception fallback returns empty string and suppresses extraction exception | Exception fallback at src/owlbear/web_extract.py:53-56 | test_returns_empty_string_when_extract_returns_none, test_returns_empty_string_when_extract_raises, test_does_not_surface_extraction_exception | PASS |
| 5. No caller rewires in this task; focused RED tests pass | #868 commit file lists only src/owlbear/web_extract.py and tests/test_web_extract.py; scoped pytest 16/16 passing | tests/test_web_extract.py full suite | PASS |

### Verdict: PASS

- Confidence: .95

### Action Taken

- Pending status move to docs via reviewer gate.

[[2026-03-23]] Mon 06:03

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | Tech-stack row already updated: leaf markdown helper extract_markdown in owlbear.web_extract at line 51 |
| 2 | Docstrings complete | Yes | Pass | src/owlbear/web_extract.py has module docstring + full docstring on extract_markdown (Args/Returns/Raises) |
| 3 | docs/sources/overview.md | Yes | Pass | Line 1120 already attributes trafilatura to src/owlbear/web_extract.py; researcher noted attribution updated |
| 4 | README.md | No | N/A | No CLI commands added; extract_markdown is a Python API helper only |
| 5 | Research doc | Yes | Pass | docs/research/leaf-markdown-extraction-helper.md exists; linked from task body; follow-up tasks #874 and #875 created |

### Files Updated

- None (all documentation already updated by researcher/builder)

### Scratch Files Cleaned

- Deleted docs/scratch/868-builder.tmp

[[2026-03-23]] Mon 06:41

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Leaf export + no forbidden imports | web_extract.py:8-9 **all**; AST guard test at test_web_extract.py:320 | PASS |
| 2. Lazy import + actionable ImportError | web_extract.py:15 sentinel; web_extract.py:38-44 lazy path; 2 lazy-import tests + 3 missing-dep tests | PASS |
| 3. Exact delegate call + raw return | web_extract.py:48-52 single extract call; line 56 raw return | PASS |
| 4. None/exception fallback empty string | web_extract.py:53-56 except+or; 4 fallback tests | PASS |
| 5. No caller migration + RED tests pass | Commits 38dc077,0ff00f7,7d4bd6c,fb1d711 touch only web_extract files; 16/16 pass | PASS |

### Test Results

- pytest (scoped): 16 passed, 0 failed
- pytest (full suite): 3790 passed, 128 failed (all pre-existing: numpy compat, missing modules, unrelated tasks)
- ruff (scoped): All checks passed
- Coverage: 100% (16 stmts, 0 missed)

### Architect Quality

- AC specificity: Excellent - exact function signature, kwargs, import boundary, fallback behavior
- Edge case coverage: Complete - lazy import timing, missing dep, None, exception
- Design direction: Correct - leaf module precedent followed
- AC Quality Score: 5/5

### Upstream Commits Verified

- 165702d feat: add extract_markdown helper and tests (#874, auditor)
- 38dc077 feat: implement extract_markdown leaf helper (#868, builder)
- 0ff00f7 fix: make trafilatura import truly lazy (#868, builder)
- 7d4bd6c test: fix lint + add AC1 import-boundary guard (#868, test-writer)
- fb1d711 test: format path expression (#868, builder)

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 06:41

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Leaf export + no forbidden imports | web_extract.py:8-9 **all**; AST guard test at test_web_extract.py:320 | PASS |
| 2. Lazy import + actionable ImportError | web_extract.py:15 sentinel; web_extract.py:38-44 lazy path; 2 lazy-import tests + 3 missing-dep tests | PASS |
| 3. Exact delegate call + raw return | web_extract.py:48-52 single extract call; line 56 raw return | PASS |
| 4. None/exception fallback empty string | web_extract.py:53-56 except+or; 4 fallback tests | PASS |
| 5. No caller migration + RED tests pass | Commits 38dc077,0ff00f7,7d4bd6c,fb1d711 touch only web_extract files; 16/16 pass | PASS |

### Test Results

- pytest (scoped): 16 passed, 0 failed
- pytest (full suite): 3790 passed, 128 failed (all pre-existing: numpy compat, missing modules, unrelated tasks)
- ruff (scoped): All checks passed
- Coverage: 100% (16 stmts, 0 missed)

### Architect Quality

- AC specificity: Excellent - exact function signature, kwargs, import boundary, fallback behavior
- Edge case coverage: Complete - lazy import timing, missing dep, None, exception
- Design direction: Correct - leaf module precedent followed
- AC Quality Score: 5/5

### Upstream Commits Verified

- 165702d feat: add extract_markdown helper and tests (#874, auditor)
- 38dc077 feat: implement extract_markdown leaf helper (#868, builder)
- 0ff00f7 fix: make trafilatura import truly lazy (#868, builder)
- 7d4bd6c test: fix lint + add AC1 import-boundary guard (#868, test-writer)
- fb1d711 test: format path expression (#868, builder)

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 06:42

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4525544 | chore | kanban/tasks/868-*.md, kanban/activity.jsonl | #868 |
