---
id: 716
title: 'P3-04: GREEN — config.yml loader'
status: backlog
priority: needed
created: 2026-04-09T03:25:11.7301647+02:00
updated: 2026-04-09T03:25:11.7301647+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 715
class: standard
---

## Objective
Implement config.yml loader using ruamel.yaml round-trip mode (typ='rt').

Brief: see parent #712 — Decision D1: ruamel.yaml for lossless round-trip

## AC
- [ ] `load_config(kanban_dir)` reads config.yml and returns BoardConfig
- [ ] `save_config(kanban_dir, config)` writes config.yml preserving field order, comments, quoting
- [ ] Timestamp resolver disabled to prevent Go-nanosecond to Python-microsecond precision drift
- [ ] next_id atomic increment via load-modify-save
- [ ] ruamel.yaml added to `serve/mcp-kanban/pyproject.toml` dependencies
- [ ] All #715 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/config_loader.py` (new)
- `serve/mcp-kanban/pyproject.toml` (edit — add ruamel.yaml dep)
