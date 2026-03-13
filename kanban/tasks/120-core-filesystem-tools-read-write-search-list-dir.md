---
id: 120
title: Core filesystem tools — read, write, search, list_dir
status: archived
priority: critical
created: 2026-02-27T14:54:08.0590699+01:00
updated: 2026-02-28T23:52:47.1008167+01:00
started: 2026-02-27T15:38:18.1308692+01:00
completed: 2026-02-28T23:52:47.1008167+01:00
tags:
    - phase-7
    - tools
    - agent
class: standard
---

PydanticAI FunctionToolset with the minimum tools agents need to interact with the codebase. Without these, agents are blind.

## Research Findings

See `docs/research/filesystem-tools.md` for full analysis.

**Key decisions:**
- Path traversal guard: `Path.resolve()` + `is_relative_to()` (Python-idiomatic version of MCP server pattern)
- Sync tools (PydanticAI wraps in executor automatically)
- Single file `src/owlbear/tools/filesystem.py` (not split like browser)
- `search_files`: `Path.glob()` + `re.search()` (two-phase)
- Constructor takes `workspace_root: Path` (required)

## AC

### Module structure
- [ ] New file: `src/owlbear/tools/filesystem.py`
- [ ] `FileToolset(FunctionToolset)` subclass following `BrowserToolset` pattern
- [ ] Constructor: `workspace_root: Path` (required, no default) — stored as `self._root = workspace_root.resolve()`
- [ ] Private `_safe_path(user_path: str) -> Path` — resolves against root, raises `PermissionError` if outside workspace
- [ ] Tools registered via `_register_tools()` + wrapper methods (pattern: `BrowserToolset._register_tools`)

### Tools (all sync — PydanticAI wraps automatically)
- [ ] `read_file(path: str, start_line: int | None, end_line: int | None) -> str` — reads file content; lines are 1-indexed inclusive; omit both for full file; raises `FileNotFoundError` if missing
- [ ] `write_file(path: str, content: str) -> str` — writes content, creates parent dirs (`mkdir(parents=True, exist_ok=True)`), overwrites if exists, returns confirmation message
- [ ] `create_file(path: str, content: str) -> str` — writes content, creates parent dirs, raises `FileExistsError` if file already exists
- [ ] `list_directory(path: str) -> str` — returns newline-separated sorted names; dirs get `/` suffix; raises `FileNotFoundError` if dir missing
- [ ] `search_files(glob_pattern: str, content_regex: str | None) -> str` — phase 1: `Path.glob(pattern)` collects file paths; phase 2: if `content_regex` given, filter with `re.search()`; returns newline-separated relative paths of matches (max 100 results, with `[truncated]` note)

### Guards and errors
- [ ] All 5 tools call `_safe_path()` first — `PermissionError` on traversal attempt
- [ ] `_safe_path`: `(self._root / user_path).resolve()` then `is_relative_to(self._root)`
- [ ] Tool errors (`FileNotFoundError`, `PermissionError`, `FileExistsError`) propagate as-is — PydanticAI surfaces them to the LLM as tool errors

### Tests (TDD: write tests first, see them fail, then implement)
- [ ] New file: `tests/test_filesystem_tools.py`
- [ ] Test each tool's happy path with `tmp_path` fixtures
- [ ] Test path traversal: `../escape`, absolute paths, null bytes in path
- [ ] Test `read_file` with line range (subset) and without (full file)
- [ ] Test `create_file` raises `FileExistsError` on existing file
- [ ] Test `list_directory` sorts names and appends `/` to dirs
- [ ] Test `search_files` with glob-only and glob+content_regex
- [ ] Test `search_files` result truncation at 100 matches
- [ ] ruff clean on both files
