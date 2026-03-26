---
id: 7
title: Create monorepo skeleton
status: ideation
priority: needed
created: 2026-03-26T17:19:31.7912984+01:00
updated: 2026-03-26T17:19:31.7912984+01:00
tags:
    - phase-1
    - scope:build
    - type:build
depends_on:
    - 6
class: standard
---

## Objective
Create the v2 monorepo directory structure with uv workspace configuration.

## Acceptance Criteria
- [ ] Root pyproject.toml with uv workspace definition
- [ ] packages/orchestrator/ with pyproject.toml and src/owlbear/ stub
- [ ] packages/knowledge/ with pyproject.toml and src/owlbear_knowledge/ stub
- [ ] packages/mcp-kanban/ with pyproject.toml and src/ stub
- [ ] packages/mcp-knowledge/ with pyproject.toml and src/ stub
- [ ] packages/mcp-project/ with pyproject.toml and src/ stub
- [ ] agents/ directory at repo root
- [ ] skills/ directory at repo root
- [ ] instructions/ directory at repo root
- [ ] kanban/ directory (already exists)
- [ ] docs/ directory structure (research/, sources/, decisions/, scratch/)
- [ ] scripts/ directory with setup.py placeholder
- [ ] uv sync succeeds with empty packages
- [ ] All packages can cross-import each other

## Context
Depends on R6 (monorepo tooling research) for the correct uv workspace configuration. This is the foundation everything else builds on.
