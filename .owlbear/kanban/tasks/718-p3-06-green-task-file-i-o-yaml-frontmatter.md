---
id: 718
title: 'P3-06: GREEN — task file I/O (YAML frontmatter + markdown body)'
status: backlog
priority: critical
created: 2026-04-09T03:25:30.2736084+02:00
updated: 2026-04-09T03:25:30.2736084+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 717
    - 716
class: standard
---

## Objective
Implement task file read/write with YAML frontmatter parsing via ruamel.yaml.

Brief: see parent #712 — YAML safety: safe loading only, no !!python/ tags

## AC
- [ ] `read_task(path)` parses YAML frontmatter + markdown body into TaskRecord
- [ ] `write_task(path, record)` writes TaskRecord to file in correct format
- [ ] Unknown YAML fields preserved on round-trip
- [ ] Path containment: validated before every I/O (tasks must be inside tasks_dir)
- [ ] Slug: `[a-z0-9-]`, max 80 chars, frozen at creation
- [ ] Windows reserved filenames rejected
- [ ] Atomic writes via temp file + os.replace()
- [ ] All #717 and #715 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/task_io.py` (new)
