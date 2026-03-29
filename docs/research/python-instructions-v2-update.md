# Update python.instructions.md for v2 Layout

> **Owning task:** #91 — Update python.instructions.md for v2 layout
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #35 (archived) established v2 test infrastructure: monorepo workspace with `uv`, `--import-mode=importlib`, dual testpaths, and per-package test directories. The `python.instructions.md` file partially reflects v2 (source paths updated) but its project layout and testing sections still omit key v2 conventions.

**Question:** What specific changes are needed to align `python.instructions.md` with the v2 pyproject.toml configuration?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pytest — Good Integration Practices | https://docs.pytest.org/en/stable/explanation/goodpractices.html | .90 — official guidance on src layout + importlib mode |
| 2 | pytest — Import mechanisms and sys.path | https://docs.pytest.org/en/stable/explanation/pythonpath.html | .85 — importlib mode semantics and trade-offs |
| 3 | OwlBear pyproject.toml (root) | Local: `pyproject.toml` | 1.0 — single source of truth for project config |
| 4 | Task #35 (v2 test infrastructure) | Local: kanban task #35 (archived) | .95 — established the v2 config this doc must match |

## 3. Analysis

### Gap analysis: current vs. required

| Section | Current content | Required content | Gap |
|---------|----------------|-----------------|-----|
| Project layout — Source | `packages/*/src/` | `packages/*/src/` | None |
| Project layout — Tests | `tests/` only | `tests/` + `packages/*/tests/` | Missing per-package tests |
| Testing — import mode | Not mentioned | `--import-mode=importlib` | Missing |
| Testing — testpaths | Not mentioned | `["tests", "packages"]` | Missing |
| Testing — asyncio mode | Not mentioned | `asyncio_mode = "strict"` | Already listed (`pytest-asyncio`) but not explicit |
| Testing — norecursedirs | Not mentioned | `["v1"]` | Nice to document |

### Import mode: why importlib matters (.90 confidence)

Per pytest docs (sources 1, 2): `--import-mode=importlib` avoids `sys.path` mutation, allows duplicate test file names across packages, and is pytest's recommended mode for new projects with src layout. This is critical in a monorepo where multiple packages have `tests/test_package.py`.

**Trade-off:** Test modules can't import each other directly (must use conftest fixtures). This matches our current pattern — no cross-test imports exist.

### Scope of change

This is a **documentation-only edit** to an instruction file. Two bullets need updating and one needs adding. No source code, config, or test changes.

## 4. Recommendation (.95 confidence)

Update `python.instructions.md` with three targeted edits:

1. **Project layout — Tests line:** Change from `tests/` to `tests/` at workspace root + `packages/*/tests/` per package.
2. **Testing section:** Add a bullet noting `--import-mode=importlib` and dual testpaths `["tests", "packages"]`.
3. **Known gotchas:** No new gotchas needed — the existing `patch.dict("sys.modules")` warning already covers the main importlib-era pitfall.

Minimal, KISS-aligned. The instruction file stays under 60 lines.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Update python.instructions.md for v2 layout" --priority nice-to-have --status ideation --tags "phase-1,docs,scope:build" --body "## Objective\nEdit python.instructions.md to reflect v2 layout:\n\n## Acceptance Criteria\n- [ ] Project layout Tests line includes both tests/ and packages/*/tests/\n- [ ] Testing section documents --import-mode=importlib and dual testpaths\n- [ ] No source code changes (docs-only edit)\n\n## Context\nSee docs/research/python-instructions-v2-update.md for analysis.\nDepends on #35 (archived). Sibling of #90."
```

**Note:** Task #91 already exists with equivalent AC. The follow-up task above is the implementation task derived from this research. Since #91 itself is the research task and its AC matches the implementation need, the architect should refine #91's AC with the specific edits identified here and advance it directly.
