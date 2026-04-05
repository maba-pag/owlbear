# v2 Test Infrastructure

> **Owning task:** #35 — Create v2 test infrastructure
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #35 sets up pytest/ruff/coverage infrastructure for v2 packages so builders can
write and run tests immediately. Depends on #7 (monorepo skeleton, done). Key questions:
what pytest testpaths for a uv monorepo with mixed root+per-package tests? What ruff
config to adopt? What coverage source configuration?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pytest Good Integration Practices | https://docs.pytest.org/en/stable/explanation/goodpractices.html | .95 |
| pydantic-ai pyproject.toml | https://github.com/pydantic/pydantic-ai (main branch) | .90 |
| ruff Configuration docs | https://docs.astral.sh/ruff/configuration/ | .85 |
| hynek Testing & Packaging | https://hynek.me/articles/testing-packaging/ | .80 |
| v1 OwlBear pyproject.toml | (internal) v1/pyproject.toml lines 47-119 | 1.0 |
| v1 OwlBear conftest.py | (internal) v1/tests/conftest.py | .90 |

## 3. Analysis

### 3.1 Current State vs. AC

| AC Item | Status | Gap |
|---------|--------|-----|
| `[tool.pytest.ini_options]` | Missing | No pytest config in root pyproject.toml |
| Root conftest.py | Missing | No conftest at root |
| Per-package tests/ + `__init__.py` | 2/5 | mcp-knowledge, mcp-project exist; orchestrator, knowledge, mcp-kanban missing |
| pytest-asyncio in dev deps | Missing | Tests use `@pytest.mark.asyncio` but dep not declared |
| ruff config for packages/ | Missing | No `[tool.ruff]` section |
| `uv run pytest` discovers all | Broken | No testpaths configured |
| `uv run ruff check` works | Partial | ruff installed but unconfigured |
| Trivial passing test per package | Missing | 3 packages have no tests |
| CI-ready docs | Missing | No test commands documented |

### 3.2 Test Discovery — testpaths approach

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| `["tests"]` only | Root tests only | Simple | Misses packages/*/tests/ |
| `["tests", "packages"]` | Recurse both (.90) | Discovers all; matches current layout | Recurses src/ dirs (harmless) |
| Explicit per-package list | `["tests", "packages/orchestrator/tests", ...]` | Precise | Verbose; must update on new package |

**Recommendation (.90):** `testpaths = ["tests", "packages"]`. pytest recurses and finds
`test_*.py` files; `src/` dirs contain no test files so no harm. This is the simplest
approach that catches both root and per-package tests. pydantic-ai uses centralized
`tests/` but OwlBear already has per-package test dirs from prior builder tasks.

### 3.3 Import Mode

pytest docs recommend `--import-mode=importlib` for new projects with src layout. This
avoids `sys.path` manipulation and allows duplicate test module names across packages.
Confirmed by both pytest docs and hynek's article. v1 didn't set this (used default
`prepend`), but v2 should adopt it.

### 3.4 ruff Config

| Approach | Config |  KISS | Coverage |
|----------|--------|-------|----------|
| v1 clone (.85) | `select = ["ALL"]` + targeted ignores | Medium | Comprehensive |
| pydantic-ai style (.70) | `extend-select` with specific rule groups | High | Partial |
| Minimal start (.60) | Defaults + `"E", "F", "W"` | Highest | Minimal |

**Recommendation (.85):** Adopt v1's `select = ["ALL"]` approach. It's proven in the
project, comprehensive, and the `ignore`/`per-file-ignores` are already tuned. Key
adaptation: `src = ["packages/*/src"]` for first-party import detection (ruff `isort`
needs this to distinguish first-party from third-party imports).

### 3.5 Coverage Config

The existing `pytest-and-linting` skill says bare `--cov` picks up `[tool.coverage.run]`
from pyproject.toml — but this section doesn't exist in v2 yet. Two options:

| Approach | Config | Maintenance |
|----------|--------|-------------|
| `source_pkgs` (.85) | `["owlbear", "owlbear_knowledge", ...]` | Update on new package |
| `source` paths (.70) | `["packages/*/src/..."]` each listed | Verbose, fragile |

**Recommendation (.85):** Use `source_pkgs` — it resolves installed package locations
automatically. This is the pattern hynek recommends for installed-package testing.
The AC doesn't explicitly mention coverage config, but it's implied by pytest-cov being
a dependency. **Suggest architect add coverage AC item.**

### 3.6 conftest.py Scope

v1 conftest has project-specific fixtures (OwlBearSettings, MockChannel). v2 is early —
models don't exist yet. conftest should be minimal:

- `project_root` fixture returning repo root `Path`
- Marker registrations (mirrors `[tool.pytest.ini_options] markers`)
- Optional-dep detection for graceful skipping (from v1 pattern)

Expand later as v2 models stabilize. YAGNI principle applies.

### 3.7 asyncio_mode

v1 uses `asyncio_mode = "strict"` requiring explicit `@pytest.mark.asyncio` on
every async test. pydantic-ai doesn't set this (defaults to auto in newer versions).
**Stick with strict** — explicit is better, matches existing test patterns, prevents
accidental unmarked async tests. Confirmed by both v1 practice and pytest-asyncio docs.

## 4. Recommendation (.88 confidence)

Proceed with #35 as currently scoped. Adopt v1's ruff config adapted for `packages/`,
use `testpaths = ["tests", "packages"]`, add `--import-mode=importlib`, and keep
`asyncio_mode = "strict"`. One AC gap found: coverage config should be added.

**Risks:**
- `src = ["packages/*/src"]` glob in ruff — verify ruff supports this glob pattern;
  fallback is explicit list.
- `testpaths = ["tests", "packages"]` adds slight discovery overhead scanning
  non-test dirs under packages/ — negligible for 5 packages.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Update pytest-and-linting skill for v2 paths" --priority nice-to-have --status ideation --tags phase-1,docs,scope:build --body "## Objective\nUpdate the pytest-and-linting skill to reflect v2 test infrastructure: new testpaths, coverage source_pkgs config, --import-mode=importlib.\n\n## Acceptance Criteria\n- [ ] Skill references v2 package paths instead of v1 src/ paths\n- [ ] Coverage section updated for source_pkgs approach\n- [ ] Import mode documented\n\n## Context\nDepends on #35 (v2 test infrastructure). The skill currently documents v1 patterns."
```

```
kanban\kanban-md.exe create "Update python.instructions.md for v2 layout" --priority nice-to-have --status ideation --tags phase-1,docs,scope:build --body "## Objective\nUpdate python.instructions.md project layout and testing sections to reference v2 packages/ paths instead of v1 src/owlbear/.\n\n## Acceptance Criteria\n- [ ] Project layout section references packages/*/src/ and packages/*/tests/\n- [ ] Testing section reflects new testpaths and import mode\n\n## Context\nDepends on #35 (v2 test infrastructure). Currently documents v1 layout."
```
