---
id: 6
title: Monorepo tooling research
status: ideation
priority: needed
created: 2026-03-26T17:19:14.2346579+01:00
updated: 2026-03-26T17:19:14.2346579+01:00
tags:
    - research
    - phase-1
    - scope:build
class: standard
---

## Objective
Research uv workspaces for multi-package Python monorepo.

## Acceptance Criteria
- [ ] Document uv workspace configuration (pyproject.toml at root plus per-package)
- [ ] Test editable installs across packages
- [ ] Test shared dependency resolution (single lock file)
- [ ] Document dev dependency isolation per package
- [ ] Validate that MCP server packages can be run as standalone processes
- [ ] Validate that packages/knowledge/ can be imported by mcp-knowledge server
- [ ] Write findings to docs/research/monorepo-tooling.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
OwlBear v2 monorepo has multiple Python packages that need to cross-import. uv workspaces should handle this.
