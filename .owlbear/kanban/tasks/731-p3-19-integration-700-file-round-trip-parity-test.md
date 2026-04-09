---
id: 731
title: 'P3-19: Integration — 700-file round-trip parity test'
status: backlog
priority: needed
created: 2026-04-09T03:28:58.5750642+02:00
updated: 2026-04-09T03:28:58.5750642+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 730
class: standard
---

## Objective
Validate that the native engine loads and round-trips the live 700+ task board without data loss.

Brief: see parent #712 — Risk: behavioral drift from kanban-md

## AC
- [ ] Test loads all task files from live `.owlbear/kanban/tasks/` directory
- [ ] Test round-trips each file (read, write to temp, read back) and asserts equality
- [ ] Test config.yml round-trip preserves all fields
- [ ] Test list_tasks returns same task count as file count
- [ ] No data loss: frontmatter fields, unknown fields, body content, formatting all preserved
- [ ] Test marked with appropriate marker (e.g., `@pytest.mark.slow`) since it reads 700+ files

## Files
- `tests/test_kanban_engine_roundtrip.py` (new)
