---
id: 376
title: Add benchmark optional extras to pyproject.toml
status: archived
priority: needed
created: 2026-03-01T20:14:00.3939908+01:00
updated: 2026-03-02T09:16:59.024805+01:00
started: 2026-03-01T20:22:47.6734364+01:00
completed: 2026-03-02T09:16:59.024805+01:00
tags:
    - phase-9
    - test
    - config
class: standard
---

From #252 (deleted umbrella) and docs/hybrid-search-benchmark-research.md §3.6.

## Acceptance Criteria

- [ ] `[benchmark]` extras group added to `[project.optional-dependencies]` in pyproject.toml
- [ ] Group includes `beir` and `ranx` (no pinned versions — let uv resolve)
- [ ] `uv sync --extra benchmark` installs beir + ranx successfully
- [ ] `uv sync` (default) does NOT install beir or ranx
- [ ] `benchmark` marker added to `[tool.pytest.ini_options]` markers list: `benchmark: marks benchmark tests requiring model/data downloads (deselect with '-m "not benchmark"')`
- [ ] `tests/benchmarks/__init__.py` created (empty) to make benchmarks a test subpackage
- [ ] `tests/benchmarks/.cache/` added to .gitignore (benchmark data cache)
- [ ] ruff clean on pyproject.toml changes

## Patterns to follow

- Existing optional extras groups in pyproject.toml (browser, crawl, knowledge, search, slack, voice, dev)
- Existing pytest markers pattern (api, slow) in [tool.pytest.ini_options]

## Notes

- beir + ranx add ~50 MB of deps — benchmark-only, never in default install.
- .cache/ dir used by #377-378 for BEIR data and embedding caches.
