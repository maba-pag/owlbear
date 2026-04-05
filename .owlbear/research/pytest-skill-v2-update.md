# Pytest-and-Linting Skill v2 Update

> **Owning task:** #90 — Update pytest-and-linting skill for v2 paths
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #90 requested updating the pytest-and-linting skill to reflect v2 test infrastructure (new testpaths, coverage source_pkgs, --import-mode=importlib). Depends on #35 (v2 test infrastructure, archived).

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| Commit `1774d1b` ("docs: update pytest-and-linting skill for v2 paths (#90, builder)") | Git history | 1.0 — prior implementation of this exact task |
| `pyproject.toml` [tool.pytest.ini_options], [tool.coverage.run] | Config file | 1.0 — ground truth for v2 settings |
| Current `skills/pytest-and-linting/SKILL.md` (post-copy via #115) | Skill file | 1.0 — current state to verify |
| Task #35 audit evidence (11/11 AC PASS, .95 confidence) | Kanban body | 0.9 — confirms v2 infra is stable |

## 3. Analysis — AC Verification

| AC Item | Current Skill State | Evidence | Verdict |
|---------|-------------------|----------|---------|
| v2 package paths (no v1 src/) | Full-suite: `tests/ packages/`; ruff: `packages/ tests/`; no `src/owlbear` refs | grep for `src/owlbear`, `v1/`, `src/ tests/` returns 0 hits | PASS |
| Coverage source_pkgs approach | Documents bare `--cov`, lists 6 source_pkgs matching pyproject.toml | Skill lists same 6 names as [tool.coverage.run] source_pkgs | PASS |
| Import mode documented | "``--import-mode=importlib`` is set in addopts — no manual flag needed" | Line present in skill after commit 1774d1b | PASS |

**Confidence: .95** — all AC items verified against both the skill file content and pyproject.toml config.

## 4. Recommendation

N/A — work already completed. Commit `1774d1b` updated the skill; commit `91865e4` (#115) copied it to the current `skills/` location. No remaining gaps.

**Note:** `owlbear_voice` is absent from `source_pkgs` — this is intentional (optional addon with heavy native deps, not installed in default dev env).

## 5. Follow-up Tasks

None needed. The task should proceed through the pipeline for formal verification and archival.
