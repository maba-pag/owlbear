---
id: 1202
title: Narrow exception handling (BLE001) in engine.py
status: backlog
priority: important
created: '2026-04-30 15:28:57.610272+00:00'
updated: '2026-04-30 15:32:04.076566+00:00'
tags:
- audit-kanban
- safety
parent:
depends_on:
- 1203
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace broad `except Exception` (BLE001) with specific exception types.

## Files
- engine.py (list_tasks, _move_file, pick_tasks)

## Change
Replace `except Exception` with specific types: yaml.YAMLError, CorruptionError, FileNotFoundError, subprocess.CalledProcessError. Each handler should log appropriately.

## AC
- [ ] No bare `except Exception` in engine.py
- [ ] Each handler catches the narrowest applicable exception
- [ ] Ruff BLE001 clean
- [ ] Existing tests pass

## Finding: 4.1
