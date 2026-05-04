---
id: 1351
title: Validate kanban config paths stay inside board
status: backlog
priority: critical
created: 2026-05-04T18:45:17.182693+00:00
updated: 2026-05-04T18:45:09+00:00
tags:
- sync-blocker
- kanban
- security
parent:
depends_on:
- 1338
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Kanban board paths are loaded from `config.yml` and then used by storage, engine, Cockpit watches, and MCP-facing operations. Existing file-name containment checks protect individual task paths, but the config itself can still name absolute or parent-traversing directories before reads/scans resolve the board shape.

Because the kanban engine is the central task and decision endpoint, path authority must be explicit: configured task/archive/decision/activity paths must stay under the intended board directory unless a deliberate future decision introduces an escape hatch.

## Acceptance Criteria

1. `PathsConfig` or config loading rejects absolute paths and parent-traversing paths for task/archive-related board directories with a clear validation error.
2. Engine/storage read paths, archive paths, and lock paths cannot resolve outside the configured kanban board directory.
3. Existing `validate_path_containment()` behavior is reused or centralized instead of creating a parallel ad hoc path checker.
4. Tests cover malicious `paths.tasks_dir` and `paths.archive_dir` values such as `../outside`, absolute paths, and symlink-adjacent resolution where practical.
5. Normal relative board configs continue to load, create, edit, archive, and list tasks without regression.
6. Cockpit and MCP board-binding tests still pass with the validated path model.

## Key Files

- `serve/kanban/src/owlbear_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/storage.py`
- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/_naming.py`
- `tests/test_config_authority.py`
- `tests/test_support_module_migration_1176.py`

## Audit Evidence

- `PathsConfig` currently stores `tasks_dir` and `archive_dir` as raw strings.
- Engine and storage build paths directly from `kanban_dir / config.paths.tasks_dir` and `kanban_dir / config.paths.archive_dir`.
- `_naming.validate_path_containment()` exists, but read/list/archive path construction is not uniformly guarded at config-boundary time.

## Recommendation

Treat config path validation as a sync blocker. It is a small surface area, but it is the trust boundary for every file-backed task operation.

## Source

Meta-audit blind source pass, 2026-05-04.
