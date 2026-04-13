---
id: 843
title: Implement task_io.py PyYAML to ruamel.yaml migration
status: backlog
priority: nice-to-have
created: '2026-04-12T02:24:30.617737+00:00'
updated: '2026-04-12T02:24:30.617737+00:00'
tags:
- scope:kanban
- cleanup
parent: 798
depends_on:
- 818
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `task_io.py` uses `from ruamel.yaml import YAML` instead of `import yaml`
- `_NoTimestampLoader` class replaced with `_make_yaml()` function (same pattern as `config_loader.py`)
- `_to_plain()` helper added for CommentedMap → dict conversion on load
- `write_task()` uses `YAML(typ="rt")` dump via `StringIO` instead of `yaml.dump()`
- `pyyaml` removed from `serve/kanban/pyproject.toml` dependencies
- All existing task I/O tests pass without modification (60+ tests)
- Live board round-trip integration tests pass (700+ files)

## Context

Research: `.owlbear/research/migrate-task-io-pyyaml-to-ruamel-827.md`
Parent research task: #827. Supersedes #827 for implementation.

## Implementation Notes

Follow the `config_loader.py` pattern exactly:
1. `_make_yaml()` → `YAML(typ="rt")` with timestamp resolver stripping
2. `_to_plain()` → recursive CommentedMap/CommentedSeq → dict/list conversion
3. `StringIO` wrapper for dump-to-string

~15 lines removed (PyYAML loader class), ~15 lines added (ruamel helpers). Net delta ~0.