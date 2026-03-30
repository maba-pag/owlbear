# Update pytest-and-linting Skill for v2 Paths

> **Owning task:** #90 — Update pytest-and-linting skill for v2 paths
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

The `pytest-and-linting` skill documents v1 patterns (single `src/` layout, `source` coverage config). Task #35 migrated test infrastructure to v2: monorepo workspace with `packages/*/src/`, `source_pkgs` coverage config, and `--import-mode=importlib`. The skill needs updating so agents use correct paths and flags.

**Question:** What specific lines in the skill are stale, and what should replace them?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pytest docs — Good Integration Practices | https://docs.pytest.org/en/stable/explanation/goodpractices.html | .90 — authoritative on `--import-mode=importlib` and `testpaths` |
| coverage.py config reference | https://coverage.readthedocs.io/en/latest/config.html | .95 — authoritative on `source_pkgs` vs `source` semantics |
| v2 `pyproject.toml` (root) | `pyproject.toml` (workspace) | 1.0 — ground truth for current config |
| v1 `pyproject.toml` | `v1/pyproject.toml` | .80 — baseline for comparison |
| pytest-cov config docs | https://pytest-cov.readthedocs.io/en/latest/config.html | .85 — bare `--cov` picks up `source_pkgs` from config |

## 3. Analysis — Stale References in Current Skill

| # | Skill section | Current (v1) | Required (v2) | Impact |
|---|---------------|-------------|---------------|--------|
| 1 | Full suite command | `tests/` | `tests/ packages/` (or omit — `testpaths` handles it) | Auditor misses package-level tests |
| 2 | Coverage `--cov` note | "picks up `source` from pyproject.toml" | "picks up `source_pkgs` from pyproject.toml" | Misleading; `source` ≠ `source_pkgs` |
| 3 | Coverage broken flags | `--cov=src/owlbear/{dir}/` example | Update to `--cov=packages/{name}/src/` example | v1 path no longer exists |
| 4 | ruff command | `uv run ruff check src/ tests/` | `uv run ruff check packages/ tests/` | Lints nothing (no `src/` in v2 root) |
| 5 | Import mode | Not mentioned | Document `--import-mode=importlib` in `addopts` | Agents may add conflicting `--import-mode` flags |
| 6 | `norecursedirs` | Not mentioned | Document `v1` exclusion | Agents may wonder why v1 tests aren't collected |
| 7 | File-capture fallback | Hardcoded `tests/` path | Should reference both `tests/` and `packages/` | Fallback misses package tests |

### Complexity assessment

This is a **docs-only edit** to an existing skill file (~150 lines). No source code changes. The builder needs to update ~7 specific locations in the skill file. Estimated as a small, well-scoped task.

## 4. Recommendation (.90 confidence)

Single follow-up task at `ideation`: update the skill file with all 7 changes above. The builder should:

1. Update full-suite pytest commands to omit explicit path (rely on `testpaths`) or use `tests/ packages/`
2. Change `source` → `source_pkgs` in the coverage note
3. Update broken-flag examples to v2 paths
4. Change ruff command to `packages/ tests/`
5. Add a note about `--import-mode=importlib` being configured in `addopts`
6. Add a note about `norecursedirs = ["v1"]`
7. Update file-capture fallback command

No decision request needed — the changes are mechanical and all driven by the ground-truth `pyproject.toml`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Update pytest-and-linting skill content for v2 monorepo paths" --priority nice-to-have --status ideation --tags "phase-1,docs,scope:build" --body "## Objective\nApply 7 updates to `.github/skills/pytest-and-linting/SKILL.md` per research doc `docs/research/pytest-linting-skill-v2-paths.md`.\n\n## Acceptance Criteria\n- [ ] Full-suite pytest commands use `tests/ packages/` or omit path (rely on testpaths)\n- [ ] Coverage note says `source_pkgs` not `source`\n- [ ] Broken-flag examples use v2 paths (`packages/` not `src/owlbear/`)\n- [ ] ruff command uses `packages/ tests/` not `src/ tests/`\n- [ ] `--import-mode=importlib` documented as configured in addopts\n- [ ] `norecursedirs = [\"v1\"]` mentioned\n- [ ] File-capture fallback includes both test discovery roots\n\n## Context\nSee `docs/research/pytest-linting-skill-v2-paths.md` for analysis."
```
