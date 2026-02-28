---
id: 106
title: Add sqlite-vec and fastembed to pyproject.toml
status: archived
priority: high
created: 2026-02-27T03:31:10.9778052+01:00
updated: 2026-02-27T13:21:37.7089483+01:00
started: 2026-02-27T03:32:47.77834+01:00
completed: 2026-02-27T13:21:37.7089483+01:00
tags:
    - memory
    - knowledge-graph
    - config
    - phase-2
class: standard
---

Add optional dependency group `[knowledge]` to pyproject.toml. Follows existing pattern (browser, slack groups).

## Acceptance Criteria

- [ ] New `knowledge` group under `[project.optional-dependencies]` in pyproject.toml
- [ ] Dependencies: `sqlite-vec >= 0.1.6` and `fastembed >= 0.7.4`
- [ ] Follows existing optional-group pattern (`browser`, `slack`)
- [ ] `uv sync --extra knowledge` resolves without errors
- [ ] `python -c 'import sqlite_vec; import fastembed'` succeeds after install
- [ ] Existing tests (`uv run pytest tests/ -m 'not api'`) still pass
- [ ] No changes to any file other than pyproject.toml

See docs/knowledge-graph-research.md section 4
