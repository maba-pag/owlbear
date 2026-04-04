---
id: 615
title: 'First sync: validate clean main branch'
status: backlog
priority: needed
created: 2026-04-04T21:55:56.253579+02:00
updated: 2026-04-04T21:55:56.253579+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 610
depends_on:
    - 613
    - 614
class: standard
---

## Summary

After the sync workflow is created and the five-tier restructure is complete, run the first sync from dev to main. Verify the clean main branch works for consumers.

## Acceptance Criteria

- [ ] AC1: Manual workflow dispatch completes successfully
- [ ] AC2: main branch contains ONLY: share/, serve/, seed/, setup/, pyproject.toml, uv.lock, .python-version, .gitignore, README.md, SECURITY.md
- [ ] AC3: No dev-only files on main (.owlbear/, store/, tests/, v1/, .github/ copilot-instructions, etc.)
- [ ] AC4: git clone (main) produces working installation
- [ ] AC5: Consumer workflow: clone main, create project dir, run setup/init.py, open VS Code, agents/skills load
- [ ] AC6: uv sync on main succeeds (skills-ref not required)
- [ ] AC7: MCP servers start from the main branch installation

## Notes

This is the validation task. If anything fails, fix on dev and re-sync.
