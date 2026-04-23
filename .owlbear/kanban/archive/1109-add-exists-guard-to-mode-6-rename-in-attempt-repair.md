---
id: 1109
title: Add exists-guard to mode-6 rename in attempt_repair
status: research
priority: important
created: 2026-04-23T00:10:27.649126+00:00
updated: 2026-04-23T00:10:27.649126+00:00
tags:
  - scope:kanban
  - tdd:red
parent:
depends_on:
  - 1108
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

See `.owlbear/research/1108-mode6-rename-collision-guard.md`.

`attempt_repair` mode-6 (ID/filename mismatch) calls `path.replace(new_path)` without checking if `new_path` already exists. `Path.replace()` silently overwrites the destination, causing data loss of a valid task file.

## Acceptance Criteria

- [ ] AC-1: When mode-6 repair target path already exists, the corrupt file is quarantined instead of overwriting the existing file.
- [ ] AC-2: `RepairOutcome` has `action="quarantined"` with detail mentioning "rename collision".
- [ ] AC-3: The existing destination file is untouched after the collision guard triggers.
- [ ] AC-4: Happy-path mode-6 rename (no collision) continues to work as before.

## Implementation Guidance

In `serve/kanban/src/owlbear_kanban/corruption.py`, mode-6 block (~L390), before `path.replace(new_path)`:

```python
if new_path.exists():
    return _quarantine()
```

The quarantine detail should mention "rename collision" for diagnosability.

## Test Guidance

Add test in `serve/kanban/tests/test_corruption.py`:
- Create valid `42-my-task.md` + corrupt `999-wrong.md` (frontmatter id: 42).
- Call `attempt_repair(corrupt_file, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)`.
- Assert outcome is quarantined, valid file untouched, corrupt file in quarantine/.
