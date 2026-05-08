---
id: 1418
title: Fix uv.lock exclusion in MegaLinter and add mcp-browser to ruff src
status: research
priority: needed
created: 2026-05-07T23:29:04.456182+00:00
updated: 2026-05-07T23:29:25.605536+00:00
tags:
- scope:infra
parent: 1413
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Two small config fixes:
1. Remove `uv\.lock$` from `FILTER_REGEX_EXCLUDE` in `.mega-linter.yml` — currently blocks Trivy from scanning the lockfile for dependency vulnerabilities.
2. Add `serve/mcp-browser/src` to `[tool.ruff] src` list in `pyproject.toml`.
See `.owlbear/research/1413-ci-sast-baseline.md` gaps G3 and G4.

## Acceptance Criteria
P1: `uv.lock` is no longer excluded from MegaLinter's `FILTER_REGEX_EXCLUDE`
P1: `serve/mcp-browser/src` is listed in `[tool.ruff] src` in `pyproject.toml`
P2: `uv run ruff check` still passes with no new errors after adding mcp-browser src