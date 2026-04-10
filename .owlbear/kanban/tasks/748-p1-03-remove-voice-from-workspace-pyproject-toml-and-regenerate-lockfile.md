---
id: 748
title: 'P1-03: Remove voice from workspace pyproject.toml and regenerate lockfile'
status: todo
priority: needed
created: '2026-04-10T10:36:47.060472+00:00'
updated: '2026-04-10T10:36:47.060472+00:00'
tags:
- phase-1
- type:cleanup
- cleanup
- scope-reduction
- scope:infra
parent: 745
depends_on:
- 747
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — config file edits.

After voice code deletion, the workspace pyproject.toml still references `serve/voice/src` (ruff sources) and `owlbear_voice` (coverage). These stale references will cause ruff/coverage errors.

## Acceptance Criteria
1. `"serve/voice/src"` removed from `[tool.ruff.lint.per-file-ignores]` sources list (line ~44)
2. `"owlbear_voice"` removed from `[tool.coverage.run] source_pkgs` list (line ~137)
3. `uv lock` regenerated successfully — `serve/voice` no longer appears as a workspace member
4. `uv sync` completes without errors

## Files
- Edit: `pyproject.toml`
- Regenerate: `uv.lock`
