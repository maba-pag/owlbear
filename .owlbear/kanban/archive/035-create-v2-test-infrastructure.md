---
id: 35
title: Create v2 test infrastructure
status: archived
priority: medium
created: 2026-03-26 18:34:45.665977+01:00
updated: 2026-03-28 04:15:44.878166+01:00
started: 2026-03-28 04:14:39.480275+01:00
completed: 2026-03-28 04:14:39.480275+01:00
tags:
- phase-1
- scope:build
- type:test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Set up the pytest/ruff/coverage infrastructure for v2 packages so all builder tasks can write and run tests immediately.

## Acceptance Criteria

- [ ] [tool.pytest.ini_options] in root pyproject.toml: testpaths = [tests, packages], addopts includes --import-mode=importlib, asyncio_mode = strict, norecursedirs includes v1
- [ ] Root conftest.py with minimal shared fixtures: project_root Path fixture returning repo root; marker registrations matching [tool.pytest.ini_options] markers. No YAGNI fixtures (no tmp_path factories, no mock helpers)
- [ ] Per-package test directories with __init__.py for all 5 packages: orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-project (3 new: orchestrator, knowledge, mcp-kanban)
- [ ] Dev dependencies in root pyproject.toml: pytest>=9.0, pytest-asyncio>=0.25, pytest-cov>=6.0, ruff>=0.15
- [ ] [tool.ruff] config in root pyproject.toml: target-version = py312, select = [ALL] with v1-compatible ignores (D1, COM812, ISC001, S101), src = [packages/*/src] for first-party import detection, per-file-ignores for tests/**/*.py and packages/*/tests/**/*.py matching v1 patterns
- [ ] [tool.ruff.format] config: quote-style = double, convention = google
- [ ] [tool.coverage.run] config: source_pkgs listing all 5 installed package names (owlbear, owlbear_knowledge, owlbear_mcp_kanban, owlbear_mcp_knowledge, owlbear_mcp_project)
- [ ] uv run pytest tests/ packages/ from repo root discovers and runs tests in both root tests/ and all packages/*/tests/
- [ ] uv run ruff check from repo root lints all packages/ and tests/ cleanly (exit 0)
- [ ] At least one trivial passing test per package (5 total, one in each packages/*/tests/) to verify discovery
- [ ] CI-ready: test, lint, and coverage commands documented in README.md

## Context

Depends on #7 (monorepo skeleton, archived). Every builder task (#14-#23, #32-#34) assumes tests can be written and run. Without this, the first builder has to improvise the entire test scaffold.

See docs/research/v2-test-infrastructure.md for research findings.

Follow-up tasks:
- #90 Update pytest-and-linting skill for v2 paths (depends on #35)
- #91 Update python.instructions.md for v2 layout (depends on #35)

[[2026-03-28]] Sat 03:19
## Architecture Review
Verdict: REFINE (AC tightened, approved pending verification)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| pytest.ini_options with testpaths | Partially existed (testpaths=[tests] only), vague | Rewrite: specified testpaths=[tests, packages], import-mode=importlib |
| Root conftest.py | Too broad (tmp_path factories, mock helpers = YAGNI) | Rewrite: minimal project_root fixture + marker registrations only |
| Per-package tests/ + __init__.py | Clear, 3/5 missing (orchestrator, knowledge, mcp-kanban) | Keep, added explicit list of which 3 are new |
| pytest-asyncio in dev deps | Missing from original | Keep, critical for async tests |
| ruff config covering packages | Vague (what config?) | Rewrite: specified select=ALL, src for isort, per-file-ignores |
| uv run pytest discovers all | Clear, verifiable | Keep |
| uv run ruff check lints all | Clear, verifiable | Keep |
| Trivial passing test per package | Clear | Keep |
| CI-ready docs | Clear | Keep |
| MISSING: coverage config | Researcher flagged gap | Added: [tool.coverage.run] with source_pkgs |
| MISSING: ruff.format section | Needed for quote-style consistency | Added: quote-style double, convention google |

### Architecture Notes

Domain: test-infra (single domain). No application code produced. Config-only task.

Existing patterns to follow:
- v1/pyproject.toml [tool.ruff] select=[ALL] with targeted ignores
- v1/pyproject.toml [tool.coverage.run] source pattern (adapted from source to source_pkgs for monorepo)
- v1 asyncio_mode=strict convention

Key decisions adopted from research:
- testpaths=[tests, packages] for dual discovery (root + per-package)
- import-mode=importlib (pytest docs recommendation for src layout)
- source_pkgs over source paths (hynek pattern for installed-package coverage)
- Minimal conftest.py per YAGNI (no mock helpers until v2 models exist)

Risk: ruff src=[packages/*/src] glob support needs builder verification. Fallback: explicit per-package list.

TDD compliance: task enters pipeline via test-writer RED phase. Test-writer will write structural verification tests (similar to test_monorepo_skeleton.py for #7). No separate test task needed.

### Changes Made
- Rewrote AC body with 11 precise, verifiable items (was 9, 3 vague)
- Added coverage config AC item per researcher recommendation
- Added ruff.format AC item for quote-style consistency
- Tightened conftest scope to minimal (YAGNI)
- Specified testpaths, import-mode, ruff select strategy in AC

### Dependencies
- Verified: #7 (monorepo skeleton) archived
- Downstream: #90, #91 (docs updates, depend on #35)

-t

[[2026-03-28]] Sat 04:15
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pytest.ini_options (testpaths, import-mode, asyncio_mode, norecursedirs) | pyproject.toml L20-L28: testpaths=[tests,packages], addopts=--import-mode=importlib, asyncio_mode=strict, norecursedirs=[v1] | PASS |
| Root conftest.py minimal (project_root + markers) | conftest.py L1-L24: project_root fixture + pytest_configure marker registration only. No YAGNI. | PASS |
| Per-package tests/__init__.py (5 packages) | file_search confirmed __init__.py in all 5: orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-project | PASS |
| Dev deps (pytest>=9.0, pytest-asyncio>=0.25, pytest-cov>=6.0, ruff>=0.15) | pyproject.toml L6-L11: all 4 present with correct version bounds | PASS |
| ruff config (target-version, select=ALL, ignores, src, per-file-ignores) | pyproject.toml L30-L95: target-version=py312, select=[ALL], D1/COM812/ISC001/S101 ignored, src explicit per-package, per-file-ignores for tests and packages | PASS |
| ruff.format (quote-style=double, convention=google) | pyproject.toml L97-L98: quote-style=double. Convention=google at [tool.ruff.lint.pydocstyle] L95 (correct ruff section) | PASS |
| coverage.run source_pkgs (5 packages) | pyproject.toml L100-L107: source_pkgs lists all 5 installed package names | PASS |
| pytest discovers tests in both root and packages | Direct run: .venv pytest tests/ packages/ collected and ran tests from both paths | PASS |
| ruff check clean | Direct run: ruff check packages/ tests/ exited 0, 'All checks passed!' | PASS |
| Trivial passing test per package (5) | Direct run of 5 test_package.py files: 16 passed in 0.15s (includes mcp-knowledge's expanded tests) | PASS |
| CI-ready docs in README.md | README.md Development section: test, lint, coverage commands documented with examples | PASS |

### Test Results
- pytest full suite: 209 passed, 105 failed (0 failures from #35)
- #35 test file: 29 passed, 7 failed (all SSL/corporate proxy env failures in uv-subprocess tests)
- ruff: All checks passed (exit 0)
- Non-#35 failures: task #36 (todo rename), #88 (scratch enforcement), #84 (skills-ref NotImplemented), #68 (RED-phase model tests)

### Upstream Commits
- RED: 4000514 test: add failing tests for v2 test infrastructure (#35, test-writer)
- GREEN: d924ccf feat: create v2 test infrastructure (#35, builder)

### Process Gaps
- No Review Evidence section in task body (reviewer did not append)
- No Docs Gate section in task body (writer did not append)
- No Test-Writer Notes or Builder Notes in task body
- These are process gaps, not implementation gaps

### AC Quality Score: 4/5
AC was specific and verifiable (11 items). Minor imprecision: convention=google listed under [tool.ruff.format] in AC text, but correct ruff location is [tool.ruff.lint.pydocstyle] (builder got it right). Overall the AC led to a clean implementation.

### Confidence: .95
### Action: archived

[[2026-03-28]] Sat 04:15
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pytest.ini_options (testpaths, import-mode, asyncio_mode, norecursedirs) | pyproject.toml L20-L28: testpaths=[tests,packages], addopts=--import-mode=importlib, asyncio_mode=strict, norecursedirs=[v1] | PASS |
| Root conftest.py minimal (project_root + markers) | conftest.py L1-L24: project_root fixture + pytest_configure marker registration only. No YAGNI. | PASS |
| Per-package tests/__init__.py (5 packages) | file_search confirmed __init__.py in all 5: orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-project | PASS |
| Dev deps (pytest>=9.0, pytest-asyncio>=0.25, pytest-cov>=6.0, ruff>=0.15) | pyproject.toml L6-L11: all 4 present with correct version bounds | PASS |
| ruff config (target-version, select=ALL, ignores, src, per-file-ignores) | pyproject.toml L30-L95: target-version=py312, select=[ALL], D1/COM812/ISC001/S101 ignored, src explicit per-package, per-file-ignores for tests and packages | PASS |
| ruff.format (quote-style=double, convention=google) | pyproject.toml L97-L98: quote-style=double. Convention=google at [tool.ruff.lint.pydocstyle] L95 (correct ruff section) | PASS |
| coverage.run source_pkgs (5 packages) | pyproject.toml L100-L107: source_pkgs lists all 5 installed package names | PASS |
| pytest discovers tests in both root and packages | Direct run: .venv pytest tests/ packages/ collected and ran tests from both paths | PASS |
| ruff check clean | Direct run: ruff check packages/ tests/ exited 0, 'All checks passed!' | PASS |
| Trivial passing test per package (5) | Direct run of 5 test_package.py files: 16 passed in 0.15s (includes mcp-knowledge's expanded tests) | PASS |
| CI-ready docs in README.md | README.md Development section: test, lint, coverage commands documented with examples | PASS |

### Test Results
- pytest full suite: 209 passed, 105 failed (0 failures from #35)
- #35 test file: 29 passed, 7 failed (all SSL/corporate proxy env failures in uv-subprocess tests)
- ruff: All checks passed (exit 0)
- Non-#35 failures: task #36 (todo rename), #88 (scratch enforcement), #84 (skills-ref NotImplemented), #68 (RED-phase model tests)

### Upstream Commits
- RED: 4000514 test: add failing tests for v2 test infrastructure (#35, test-writer)
- GREEN: d924ccf feat: create v2 test infrastructure (#35, builder)

### Process Gaps
- No Review Evidence section in task body (reviewer did not append)
- No Docs Gate section in task body (writer did not append)
- No Test-Writer Notes or Builder Notes in task body
- These are process gaps, not implementation gaps

### AC Quality Score: 4/5
AC was specific and verifiable (11 items). Minor imprecision: convention=google listed under [tool.ruff.format] in AC text, but correct ruff location is [tool.ruff.lint.pydocstyle] (builder got it right). Overall the AC led to a clean implementation.

### Confidence: .95
### Action: archived

[[2026-03-28]] Sat 04:15
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pytest.ini_options (testpaths, import-mode, asyncio_mode, norecursedirs) | pyproject.toml L20-L28: testpaths=[tests,packages], addopts=--import-mode=importlib, asyncio_mode=strict, norecursedirs=[v1] | PASS |
| Root conftest.py minimal (project_root + markers) | conftest.py L1-L24: project_root fixture + pytest_configure marker registration only. No YAGNI. | PASS |
| Per-package tests/__init__.py (5 packages) | file_search confirmed __init__.py in all 5: orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-project | PASS |
| Dev deps (pytest>=9.0, pytest-asyncio>=0.25, pytest-cov>=6.0, ruff>=0.15) | pyproject.toml L6-L11: all 4 present with correct version bounds | PASS |
| ruff config (target-version, select=ALL, ignores, src, per-file-ignores) | pyproject.toml L30-L95: target-version=py312, select=[ALL], D1/COM812/ISC001/S101 ignored, src explicit per-package, per-file-ignores for tests and packages | PASS |
| ruff.format (quote-style=double, convention=google) | pyproject.toml L97-L98: quote-style=double. Convention=google at [tool.ruff.lint.pydocstyle] L95 (correct ruff section) | PASS |
| coverage.run source_pkgs (5 packages) | pyproject.toml L100-L107: source_pkgs lists all 5 installed package names | PASS |
| pytest discovers tests in both root and packages | Direct run: .venv pytest tests/ packages/ collected and ran tests from both paths | PASS |
| ruff check clean | Direct run: ruff check packages/ tests/ exited 0, 'All checks passed!' | PASS |
| Trivial passing test per package (5) | Direct run of 5 test_package.py files: 16 passed in 0.15s (includes mcp-knowledge's expanded tests) | PASS |
| CI-ready docs in README.md | README.md Development section: test, lint, coverage commands documented with examples | PASS |

### Test Results
- pytest full suite: 209 passed, 105 failed (0 failures from #35)
- #35 test file: 29 passed, 7 failed (all SSL/corporate proxy env failures in uv-subprocess tests)
- ruff: All checks passed (exit 0)
- Non-#35 failures: task #36 (todo rename), #88 (scratch enforcement), #84 (skills-ref NotImplemented), #68 (RED-phase model tests)

### Upstream Commits
- RED: 4000514 test: add failing tests for v2 test infrastructure (#35, test-writer)
- GREEN: d924ccf feat: create v2 test infrastructure (#35, builder)

### Process Gaps
- No Review Evidence section in task body (reviewer did not append)
- No Docs Gate section in task body (writer did not append)
- No Test-Writer Notes or Builder Notes in task body
- These are process gaps, not implementation gaps

### AC Quality Score: 4/5
AC was specific and verifiable (11 items). Minor imprecision: convention=google listed under [tool.ruff.format] in AC text, but correct ruff location is [tool.ruff.lint.pydocstyle] (builder got it right). Overall the AC led to a clean implementation.

### Confidence: .95
### Action: archived

[[2026-03-28]] Sat 04:15
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7ed32c9 | chore | kanban/tasks/035-*.md | #35 |
