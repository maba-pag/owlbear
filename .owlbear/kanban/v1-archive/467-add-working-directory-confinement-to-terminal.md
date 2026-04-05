---
id: 467
title: Add working directory confinement to terminal toolset
status: archived
priority: needed
created: 2026-03-04T07:37:47.0146661+01:00
updated: 2026-03-06T19:28:15.6338133+01:00
started: 2026-03-06T10:15:41.0094698+01:00
completed: 2026-03-06T19:28:15.6338133+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

SEC-02: working_dir parameter accepts any absolute path without confinement. Apply _safe_path pattern.

## Acceptance Criteria

- [ ] `__init__` stores `self._workspace_root = workspace_root.resolve()` (matches FileToolset `self._root` pattern at filesystem.py L45)
- [ ] `run_command()` rejects `working_dir` containing null bytes (`\x00`) with `PermissionError('Path outside workspace: ...')`
- [ ] `run_command()` resolves `working_dir` (relative  `workspace_root / working_dir`; absolute  as-is) then calls `.resolve()` and checks `is_relative_to(self._workspace_root)`
- [ ] `run_command()` raises `PermissionError` for resolved paths outside workspace root
- [ ] `working_dir=None` continues to use `self._workspace_root` (no behaviour change)
- [ ] Relative paths to valid subdirectories continue to work (no behaviour change)
- [ ] Absolute paths inside workspace continue to work (no behaviour change)

## Tests (in test_terminal_tools.py, add to TestWorkingDir class)

- [ ] `test_working_dir_absolute_outside_raises`  `working_dir='/etc'` (or Windows equiv)  `PermissionError`
- [ ] `test_working_dir_traversal_raises`  `working_dir='../../escape'`  `PermissionError`
- [ ] `test_working_dir_null_byte_raises`  `working_dir='sub\x00dir'`  `PermissionError`
- [ ] `test_working_dir_absolute_inside_allowed`  `working_dir=str(workspace_root / 'sub')`  succeeds (existing test `test_absolute_working_dir` covers this but verify it still passes)
- [ ] Existing tests `test_relative_working_dir`, `test_absolute_working_dir`, `test_default_uses_workspace_root`, `test_none_working_dir_uses_workspace_root` all pass unchanged

## Implementation Notes

- Inline the guard in `run_command()` at the working-dir resolution block (lines ~164-167). Do NOT extract a shared helper  that is a separate DRY task.
- Follow the exact pattern from `FileToolset._safe_path` at filesystem.py L52-68: null-byte check  resolve  `is_relative_to`  `PermissionError`
- ~10 LOC change in terminal.py + ~30 LOC new tests

## Research

See docs/research/terminal-cwd-confinement.md
