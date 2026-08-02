---
id: 924
title: 'P1-03: Cockpit package skeleton + engine adapter boundary test'
status: archived
priority: medium
created: 2026-04-17T19:57:10.951841+00:00
updated: 2026-04-18T10:19:02.808374+00:00
tags:
- cockpit
- backend
- phase-1
- type:build
parent: 920
depends_on:
- 921
- 922
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Create the `serve/cockpit/` uv workspace member with FastAPI foundation and a boundary test enforcing engine adapter discipline (D12).

## Acceptance Criteria

- [ ] `serve/cockpit/pyproject.toml` as uv workspace member; deps: `owlbear-kanban`, `fastapi`, `uvicorn`, `pydantic`
- [ ] `serve/cockpit/src/owlbear_cockpit/__init__.py` — importable package
- [ ] `serve/cockpit/src/owlbear_cockpit/main.py` — minimal FastAPI app with `/health` endpoint
- [ ] `serve/cockpit/src/owlbear_cockpit/adapter.py` — engine adapter module (placeholder; will wrap allowed engine methods)
- [ ] Boundary test at `tests/test_cockpit_boundary.py`: AST-scans all `.py` files under `serve/cockpit/src/` for imports of `claim_task`, `start_work`, `end_work`, `pick_dispatchable` from `owlbear_kanban` — fails if any found
- [ ] Root `pyproject.toml` updated with workspace member
- [ ] `uv sync` succeeds with new workspace member

## Files

- `serve/cockpit/pyproject.toml`
- `serve/cockpit/src/owlbear_cockpit/__init__.py`
- `serve/cockpit/src/owlbear_cockpit/main.py`
- `serve/cockpit/src/owlbear_cockpit/adapter.py`
- `tests/test_cockpit_boundary.py`
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/924-cockpit-package-skeleton.md
- Sources: 8 studied, 6 high-relevance (≥0.90)
- Recommendation: Name-level AST scan for 4 forbidden engine imports (claim_task, start_work, end_work, pick_dispatchable); package scaffold follows existing serve/* workspace member pattern (confidence: 0.90)
- Follow-up tasks created: none (AC is self-contained)
- Decision requests: none

Key findings:

1. Root `pyproject.toml` uses `members = ["serve/*"]` — no explicit member entry needed, just create directory + `uv sync`
2. Boundary test must be name-level (specific forbidden imports), NOT namespace-level (cockpit legitimately imports from owlbear_kanban)
3. AST scan should cover both `from owlbear_kanban import X` and `from owlbear_kanban.engine import X` patterns
4. Builder note: add `"serve/cockpit/src"` to root `[tool.ruff] src` list for lint coverage
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Package scaffold + boundary enforcement — one logical deliverable |
| Interface clarity | PASS (refined) | AC #5 clarified re: import-level vs method-level enforcement; AC #6 made specific |
| Dependency correctness | PASS | #921, #922 both archived. Parent #920 archived. |
| Module layering | PASS | Cockpit imports from owlbear_kanban (library dep, downward). No upward imports. |
| TDD compliance | PASS | Boundary test is the test artifact. Test-writer will process. |
| KISS/YAGNI | PASS | Minimal scaffold + one focused test. Adapter is placeholder per YAGNI. |
| Premise challenge | PASS | Cockpit package is required per Brief D14. No existing capability. |
| Pattern consistency | PASS | Follows serve/mcp-kanban workspace member pattern. FastAPI per Brief. |
| Security surface | PASS | /health endpoint only, no user input. Minimal surface. |
| Single domain | PASS | Cockpit domain only. |

### Codebase Evidence

- Root `pyproject.toml`: `members = ["serve/*"]` auto-discovers — no explicit member entry needed
- `serve/mcp-kanban/pyproject.toml`: reference pattern for workspace dep (`[tool.uv.sources] owlbear-kanban = { workspace = true }`)
- `owlbear_kanban/__init__.py` exports: `KanbanEngine`, `Task`, `TaskSummary`, `BoardConfig`, `pick_dispatchable`
- `claim_task`, `start_work`, `end_work` are instance methods on `KanbanEngine` (engine.py L621, L689, L734) — NOT standalone importable names
- `pick_dispatchable` IS importable from `owlbear_kanban` and `owlbear_kanban.dispatch`
- Root `[tool.ruff] src` list needs `"serve/cockpit/src"` added (7 entries currently, `serve/mcp-browser/src` also missing — separate concern)

### Challenge Results

- Challenger: **reconsider** (confidence 0.45)
- Core critique: boundary test checks for imports that can't occur for 3 of 4 forbidden names (`claim_task`, `start_work`, `end_work` are instance methods, not importable names). Only `pick_dispatchable` is genuinely importable.
- Architect response: **accepted with refinement.** The critique is factually correct. The test is reframed as: (1) primary enforcement for `pick_dispatchable`, (2) defensive tripwire for the other 3 names against future re-exports. Method-level D12 enforcement belongs in adapter implementation tasks (#930, #934), not this scaffold. AC #5 refined to be honest about what import scanning can and cannot catch.

### AC Refinements Applied

**AC #5 (boundary test):** Original said "imports of `claim_task`, `start_work`, `end_work`, `pick_dispatchable` from `owlbear_kanban`". Refined to clarify: scan for forbidden name imports from any `owlbear_kanban*` module path. `pick_dispatchable` is the primary importable target. The other 3 names are defensive tripwires (currently instance methods on `KanbanEngine`, not standalone importable). Full D12 method-level enforcement deferred to adapter tasks.

**AC #6:** Original "Root `pyproject.toml` updated with workspace member" was misleading — `members = ["serve/*"]` glob auto-discovers. Refined to: add `"serve/cockpit/src"` to root `[tool.ruff] src` list for lint coverage.

### Builder Guidance

1. `pyproject.toml` pattern: follow `serve/mcp-kanban/pyproject.toml` — include `[tool.uv.sources] owlbear-kanban = { workspace = true }`
2. No explicit `[tool.uv.workspace] members` entry needed — glob handles it
3. Boundary test: scan `ImportFrom` AST nodes where module starts with `owlbear_kanban` and imported names intersect `{claim_task, start_work, end_work, pick_dispatchable}`. Cover both `from owlbear_kanban import X` and `from owlbear_kanban.engine import X` patterns.
4. Add `"serve/cockpit/src"` to root `[tool.ruff] src` list
5. `adapter.py` is a placeholder — empty module or minimal docstring only

### Verdict: APPROVE (with refinements)

[[2026-04-18]]

## Test-Writer Notes

- Test file: tests/test_cockpit_boundary.py
- Classes: TestFromAC_CockpitPackageSkeleton, TestFromAC_BoundaryEnforcement, TestFromAC_RuffConfig
- Tests per category: happy 8, edge 3, error 5, boundary 4
- Total: 20 tests, all FAIL (15 failed + 5 errors in fixture setup)
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC#1: pyproject.toml + deps | test_pyproject_toml_exists, test_pyproject_toml_declares_{owlbear_kanban,fastapi,uvicorn,pydantic}_dep, test_pyproject_toml_has_workspace_source_for_kanban |
| AC#2: package importable | test_package_importable |
| AC#3: /health endpoint | test_main_module_importable, test_main_module_exposes_fastapi_app, test_health_endpoint_exists_and_returns_200, test_health_endpoint_returns_json_body, test_health_endpoint_requires_no_auth |
| AC#4: adapter.py importable | test_adapter_module_importable |
| AC#5: AST boundary scan | test_cockpit_src_directory_exists, test_scan_covers_at_least_one_python_file, test_no_forbidden_import_{claim_task,start_work,end_work,pick_dispatchable} |
| AC#6: ruff src list | test_ruff_src_includes_cockpit |

### Failure types in RED

- FileNotFoundError: pyproject.toml doesn't exist (AC#1 tests)
- ModuleNotFoundError: owlbear_cockpit not installed (AC#2-4 tests)
- AssertionError: serve/cockpit/src/ missing (AC#5 fixture → 5 setup errors + cockpit_src_directory test)
- AssertionError: ruff src list missing cockpit entry (AC#6 test)

### Design notes

- `_collect_forbidden_imports()` helper scans both `owlbear_kanban` and `owlbear_kanban.engine`/`owlbear_kanban.dispatch` module paths
- `cockpit_src_root` fixture asserts directory exists — all 5 scan tests fail at setup in RED (not vacuous pass)
- `test_scan_covers_at_least_one_python_file` guards against vacuous boundary pass with empty src dir

Commit: 09bcefc5
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/cockpit/pyproject.toml` — new workspace member; deps: owlbear-kanban (workspace), fastapi, uvicorn, pydantic
- `serve/cockpit/src/owlbear_cockpit/__init__.py` — importable package
- `serve/cockpit/src/owlbear_cockpit/main.py` — FastAPI app with /health endpoint returning `{"status": "ok"}`
- `serve/cockpit/src/owlbear_cockpit/adapter.py` — placeholder module (empty)
- `pyproject.toml` — added `"serve/cockpit/src"` to `[tool.ruff] src` list

### Test Results

- 20/20 TestFromAC_* tests passed (0 failures, 0 errors)
- ruff: clean

### Evidence

- `uv sync` resolved and installed owlbear-cockpit==0.1.0 without errors
- All 3 test classes GREEN: TestFromAC_CockpitPackageSkeleton (13), TestFromAC_BoundaryEnforcement (6), TestFromAC_RuffConfig (1)
- Commit: ccdc730a
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 20 passed, 0 failed (tests/test_cockpit_boundary.py)

### Lint

clean: true — no violations

### Coverage

Coverage did not generate — no source data captured. `owlbear_cockpit` is installed as a workspace package and pytest-cov source configuration did not instrument it. Code under review is ~20 lines across 4 files (3 near-empty), all execution paths verified by code reading. Tooling gap noted; not a quality blocker.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC#1: pyproject.toml with deps + workspace source | test_pyproject_toml_exists, test_pyproject_toml_declares_{owlbear_kanban,fastapi,uvicorn,pydantic}_dep, test_pyproject_toml_has_workspace_source_for_kanban | Yes — file existence + string presence checks | COVERED |
| AC#2: owlbear_cockpit importable | test_package_importable | Yes — import raises ModuleNotFoundError | COVERED |
| AC#3: main.py FastAPI app + /health | test_main_module_importable, test_main_module_exposes_fastapi_app, test_health_endpoint_exists_and_returns_200, test_health_endpoint_returns_json_body, test_health_endpoint_requires_no_auth | Yes — type check, 200 status, json body, no-auth check | COVERED |
| AC#4: adapter.py importable placeholder | test_adapter_module_importable | Yes — import raises if missing | COVERED |
| AC#5: AST boundary scan for forbidden imports | test_cockpit_src_directory_exists, test_scan_covers_at_least_one_python_file, test_no_forbidden_import_{claim_task,start_work,end_work,pick_dispatchable} | Yes — fixture asserts existence; non-vacuousness guard; violation list checked | COVERED |
| AC#6: ruff src includes serve/cockpit/src | test_ruff_src_includes_cockpit | Yes — string presence assertion with both quote styles | COVERED |

#### Security Review

- No hardcoded secrets, tokens, or credentials.
- /health endpoint accepts no user input — no injection surface.
- AST scanner path constructed from `project_root` fixture (workspace root), not user-controlled — no path traversal.
- New deps: fastapi, uvicorn, pydantic — all well-maintained, no known vulnerabilities.
- No secret leakage in error messages or logs.
- No issues.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 20 TestFromAC_* tests | No changes detected — test count (20), class names (3), and test names match test-writer notes exactly. Fixture cockpit_src_root still asserts existence. Vacuous-pass guard (test_scan_covers_at_least_one_python_file) intact. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `__name__ == "owlbear_cockpit"`, `isinstance(app, FastAPI)`, `status_code == 200`, violation list `== []` with file/line detail |
| Negative/error-path coverage | ADEQUATE | Boundary tests check for violations; `test_health_endpoint_requires_no_auth` guards against over-restriction; fixture guards against vacuous pass |
| Manual mutation reasoning | STRONG | Missing /health route → 404 fails 200-check; wrong type → isinstance fails; forbidden import added → violation list non-empty |
| Test independence | STRONG | No shared mutable state; all fixtures are read-only file system ops |
| Descriptive test names | STRONG | All names clearly describe intent per AC line |

#### Data Safety

- No LLM output persistence. No race conditions. No shared mutable state. No unbounded inputs (AST scanner walks a fixed, bounded package directory). No issues.

#### Implementation-Aware Gaps

- `__init__.py`: `__all__ = []` — trivial, importability verified by test.
- `main.py`: single route, covered by 5 tests. No untested branches.
- `adapter.py`: empty placeholder, importability verified by test.
- No significant untested paths.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `test_health_endpoint_returns_json_body` checks `isinstance(body, dict)` but not the specific `{"status": "ok"}` content. AC only requires "minimal /health endpoint" — this is fine. Could be tightened in a future iteration.
- Coverage tooling: `owlbear_cockpit` not instrumented by pytest-cov. Root `pyproject.toml` `[tool.coverage.run] source` may need `owlbear_cockpit` added as a follow-up.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1: pyproject.toml + deps | serve/cockpit/pyproject.toml exists; deps list confirmed; `workspace = true` source confirmed | 6 tests PASS | PASS |
| AC#2: package importable | serve/cockpit/src/owlbear_cockpit/**init**.py exists; package installed via uv sync | test_package_importable PASS | PASS |
| AC#3: FastAPI app + /health | main.py L6: `app = FastAPI(...)`; L10: `@app.get("/health")`; returns `{"status": "ok"}` | 5 tests PASS | PASS |
| AC#4: adapter.py placeholder | adapter.py exists with `__all__ = []` | test_adapter_module_importable PASS | PASS |
| AC#5: AST boundary scan | _collect_forbidden_imports scans owlbear_kanban, owlbear_kanban.engine, owlbear_kanban.dispatch; 4 per-name violation tests; vacuous-pass guard present | 6 tests PASS | PASS |
| AC#6: ruff src updated | root pyproject.toml [tool.ruff] src contains "serve/cockpit/src" (8th entry) | test_ruff_src_includes_cockpit PASS | PASS |
| uv sync succeeds | Package installed; 20 import-dependent tests pass | (operational) | PASS |

### Confidence: .98

### Verdict: PASS

### Action: advance to docs

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New package in `serve/`; `copilot-instructions.md` lists `serve/` at directory level only — no per-package enumeration; no update required |
| 2 | Module docstrings | Yes | Verified | `__init__.py`: module docstring present; `main.py`: module docstring + `health()` function docstring; `adapter.py`: module docstring. All accurate. |
| 3 | External attribution | No | N/A | Research sources S1–S5 are all internal codebase or git-history files; no external repos/articles cited |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/924-cockpit-package-skeleton.md` confirmed present; linked from task body |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`.owlbear/scratch/924-*` — no matches)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1: pyproject.toml + deps | serve/cockpit/pyproject.toml verified: owlbear-kanban, fastapi, uvicorn, pydantic deps + `workspace = true`. 6 tests PASS | PASS |
| AC#2: importable package | `__init__.py` exists, test_package_importable PASS | PASS |
| AC#3: /health endpoint | main.py L10: `@app.get("/health")` returns `{"status": "ok"}`. 5 tests PASS | PASS |
| AC#4: adapter.py placeholder | adapter.py exists with `__all__ = []`. test_adapter_module_importable PASS | PASS |
| AC#5: AST boundary scan | `_collect_forbidden_imports()` scans 3 module paths × 4 forbidden names; vacuous-pass guard present; 6 tests PASS | PASS |
| AC#6: ruff src | Root pyproject.toml `[tool.ruff] src` contains `"serve/cockpit/src"` (8th entry). test_ruff_src_includes_cockpit PASS | PASS |
| AC#7: uv sync | Builder confirmed install; 20 import-dependent tests pass | PASS |

### Test Results

- pytest: 460 passed, 6 failed (all failures in serve/mcp-knowledge/tests/ — out of scope)
- ruff: clean

### Architect Quality: 4/5

Good AC after challenger refinement. AC#5 and #6 initially imprecise (method vs import confusion, misleading workspace member update) but corrected via challenger cycle. No builder improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (-.02 each) = 0
- Lint violations: none (-.05) = 0
- AC quality ≤ 3: no (-.03) = 0
- Missing reviewer evidence: no (-.02) = 0
- Full-suite failures in task scope: none (-.05) = 0

### Confidence: 1.00

### Action: archive
