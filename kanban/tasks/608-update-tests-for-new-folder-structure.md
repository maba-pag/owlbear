---
id: 608
title: Update tests for new folder structure
status: backlog
priority: needed
created: 2026-04-04T20:31:51.963696+02:00
updated: 2026-04-04T20:31:51.963696+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - test
depends_on:
    - 600
    - 601
    - 602
    - 603
    - 604
parent: 598
class: standard
---

## Summary

Update test files that assert on folder paths, fixture structures, or path assumptions that changed in the migration.

## Acceptance Criteria

- [ ] AC1: All tests referencing .github/agents/ updated to share/agents/
- [ ] AC2: All tests referencing .github/skills/ updated to share/skills/
- [ ] AC3: All tests referencing packages/ updated to serve/
- [ ] AC4: All tests referencing data/ updated to store/
- [ ] AC5: All tests referencing kanban/ updated to .owlbear/kanban/
- [ ] AC6: All tests referencing scripts/ updated to .owlbear/scripts/ or setup/
- [ ] AC7: setup.py test files updated for setup/init.py location and new behavior
- [ ] AC8: uv run pytest passes with no failures
- [ ] AC9: uv run ruff check passes

## Notes

Many tests create temporary directories with specific structures. Grep for path patterns: .github/agents, .github/skills, packages/, kanban/, scripts/, data/.
Focus on test files in tests/ and serve/*/tests/.
