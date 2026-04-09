---
id: 717
title: 'P3-05: RED — task file I/O (read, write, round-trip)'
status: backlog
priority: critical
created: 2026-04-09T03:25:21.0909825+02:00
updated: 2026-04-09T03:25:21.0909825+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 714
class: standard
---

## Objective
Write failing tests for task file I/O: reading YAML frontmatter + markdown body, writing task files, and round-trip preservation.

Brief: see parent #712

## AC
- [ ] Test reads a task file and returns TaskRecord with all frontmatter fields + markdown body
- [ ] Test writes a TaskRecord to a file in correct format (--- delimited YAML frontmatter + body)
- [ ] Test round-trips a task file without data loss (unknown fields, body formatting preserved)
- [ ] Test path containment validation (reject paths outside kanban tasks_dir)
- [ ] Test slug generation from title (a-z0-9 dash, max 80 chars)
- [ ] Test Windows reserved filename rejection (CON, PRN, AUX, NUL, etc.)
- [ ] Test file naming convention: `{id}-{slug}.md`
- [ ] All tests fail (no I/O implementation yet)

## Files
- `tests/test_kanban_engine_io.py` (new)
