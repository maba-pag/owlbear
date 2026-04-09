---
id: 715
title: 'P3-03: RED — config.yml loader (ruamel.yaml round-trip)'
status: backlog
priority: needed
created: 2026-04-09T03:25:03.4706335+02:00
updated: 2026-04-09T03:25:03.4706335+02:00
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
Write failing tests for config.yml loading via ruamel.yaml round-trip mode.

Brief: see parent #712 — Decision D1: ruamel.yaml

## AC
- [ ] Test loads config.yml and returns BoardConfig with correct statuses (list of dicts), priorities, defaults, next_id
- [ ] Test round-trips config.yml (load, save, reload) without data loss or field reordering
- [ ] Test preserves comments and unknown fields
- [ ] Test next_id increment (load, increment, save, verify)
- [ ] Test timestamp resolver disabled (no auto-conversion of date-like strings)
- [ ] All tests fail (no loader implementation yet)

## Files
- `tests/test_kanban_engine_config.py` (new)
