# Core Filesystem Tools Research

> **Owning task:** #120 — Core filesystem tools — read, write, search, list_dir
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear agents need filesystem access to read, write, and search code. Task #120 defines a `FileToolset(FunctionToolset)` with 5 tools: `read_file`, `write_file`, `create_file`, `list_directory`, `search_files`. All paths must be sandboxed within a configurable `workspace_root` via a path traversal guard.

Key design questions:

1. What path traversal guard pattern is safe and cross-platform?
2. Should tools be sync or async?
3. What's the right granularity — single module or actions + toolset split?
4. How should `search_files` combine glob + content grep?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| MCP Filesystem Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem> | .95 | Reference implementation for read/write/search/list tools with allowed-directory sandboxing, path validation via `resolve` + `startsWith`, tool annotations (readOnly/destructive) |
| MCP `path-validation.ts` | <https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/path-validation.ts> | .90 | `isPathWithinAllowedDirectories`: normalize → resolve → check `startsWith(dir + sep)`, null-byte rejection |
| Python `pathlib` docs | <https://docs.python.org/3/library/pathlib.html> | .90 | `Path.resolve()` eliminates `..` and symlinks; `Path.is_relative_to()` checks containment (string-based, no symlink resolution — must resolve first) |
| OwlBear `BrowserToolset` | `src/owlbear/tools/browser/toolset.py` | .95 | Established pattern: `FunctionToolset` subclass, `_register_tools()`, wrapper methods injecting shared state (`page`, `config`) |
| OwlBear `SkillRegistry` | `src/owlbear/skills/registry.py` | .85 | Second `FunctionToolset` subclass — simpler, sync tools, same `add_function()` pattern |
| OwlBear `CommandSafetyGuard` | `src/owlbear/core/command_guard.py` | .80 | Existing blocklist guard for shell commands and file paths — complementary to path traversal guard |
| OwlBear daemon-bootstrap research | `docs/daemon-bootstrap-research.md` | .75 | Planned `DevToolset` with `file_read`, `file_write`, `list_directory` — confirms this task's scope |

## 3. Analysis

### 3.1 Path Traversal Guard

| Approach | Method | Symlink-safe | Cross-platform | LOC |
|----------|--------|-------------|----------------|-----|
| A. `resolve()` + `is_relative_to()` | `(root / path).resolve().is_relative_to(root.resolve())` | Yes | Yes | ~5 |
| B. String `startsWith` after normalize | MCP server pattern (TS) | Yes | Needs OS handling | ~20 |
| C. `os.path.commonpath` | `commonpath([root, target]) == root` | No (no resolve) | Yes | ~5 |
| D. `try: relative_to()` | Raises `ValueError` if outside | No (lexical) | Yes | ~5 |

**Recommendation (.90):** Option A — `Path.resolve()` + `is_relative_to()`. This is the Python-idiomatic version of the MCP server's `normalize → resolve → startsWith` pattern. `resolve()` eliminates `..` segments and resolves symlinks. `is_relative_to()` checks containment. Both are stdlib, zero dependencies.

**Implementation:**

```python
def _safe_path(self, user_path: str) -> Path:
    resolved = (self._root / user_path).resolve()
    if not resolved.is_relative_to(self._root.resolve()):
        raise PermissionError(f"Path outside workspace: {user_path}")
    return resolved
```

**Edge cases to test:** `../escape`, absolute paths (`/etc/passwd`, `C:\Windows`), null bytes, symlinks pointing outside root, empty string, `.` path.

### 3.2 Sync vs Async

| Approach | Rationale | Fit |
|----------|-----------|-----|
| Sync tools | `pathlib` is sync; PydanticAI wraps sync tools in `run_in_executor` automatically | Best |
| Async tools (`aiofiles`) | Extra dependency, no real benefit for local FS on SSD | Over-engineered |

**Recommendation (.95):** Sync. PydanticAI's `FunctionToolset` handles sync functions natively (wraps them for async agent runs). All `pathlib` operations are sync. Adding `aiofiles` just for this violates KISS/YAGNI. Both `BrowserToolset` (async, because Playwright is async) and `SkillRegistry` (sync) confirm both patterns work.

### 3.3 Module Structure — Single File vs Split

| Approach | Files | LOC | KISS |
|----------|-------|-----|------|
| A. Single `filesystem.py` | 1 | ~120 | High |
| B. `actions.py` + `toolset.py` (browser pattern) | 2 | ~150 | Medium |
| C. Package with `__init__`, `actions.py`, `toolset.py`, `guard.py` | 4 | ~200 | Low |

**Recommendation (.85):** Option A — single file. The browser toolset needs the split because actions are individually complex (Playwright async, safety guards, base64 encoding). Filesystem tools are simple `pathlib` wrappers (~5-10 lines each). A single module keeps it flat and readable. Can split later if complexity grows (YAGNI).

### 3.4 Tool Design Decisions

**`read_file`:** Path + optional `start_line`/`end_line` (1-indexed, inclusive). MCP server uses `head`/`tail` (mutually exclusive). Line range is more flexible and matches VS Code Copilot's `read_file` tool. Return the content as a string.

**`write_file`:** Path + content. Creates parent directories via `Path.mkdir(parents=True, exist_ok=True)`. Overwrites if exists (like MCP server's `write_file`). Returns confirmation string.

**`create_file`:** Path + content. Fails with `FileExistsError` if the file already exists. This is a safety tool — agents can use `create_file` when they intend to create new files only. Distinct from `write_file` which overwrites.

**`list_directory`:** Path → sorted list of names. Directories get `/` suffix (matching the AC and VS Code's convention). Return as newline-separated string.

**`search_files`:** Glob pattern + optional content regex.

| Approach | Mechanism | Performance | KISS |
|----------|-----------|-------------|------|
| A. `Path.glob()` + `re.search` | Two-phase: glob names, then grep content | Good for small trees | High |
| B. `Path.rglob()` only | Recursive glob, no content search | Fast | Too limited |
| C. `subprocess` ripgrep | Shell out to `rg` | Fastest | External dep |

**Recommendation (.85):** Option A — `Path.glob()` for filename matching + `re.search()` for optional content filtering. Simple, no dependencies, good enough for workspace-scale trees. Return matching file paths (and optionally matching lines for content grep).

### 3.5 Integration with CommandSafetyGuard

The existing `CommandSafetyGuard` already checks `_FILE_TOOLS` (`create_file`, `write_file`, etc.) for blocked file patterns (e.g., `.env`). The new `FileToolset` path traversal guard is complementary — it prevents leaving the workspace root. Both guards should operate:

1. **Path traversal guard** (inside `FileToolset._safe_path`) — workspace containment
2. **CommandSafetyGuard** (PRE_TOOL_USE hook) — pattern-based blocklist

No changes needed to `CommandSafetyGuard` — it already has the right tool names in `_FILE_TOOLS`.

## 4. Recommendation (.88 confidence)

**Single-file `FileToolset(FunctionToolset)` in `src/owlbear/tools/filesystem.py`:**

- 5 sync tools registered via `_register_tools()` + wrapper methods (matching `BrowserToolset` pattern)
- Private `_safe_path()` method for path traversal guard using `resolve()` + `is_relative_to()`
- Constructor takes `workspace_root: Path` (required, no default)
- All tools are sync (PydanticAI handles threading)
- ~100-120 LOC for toolset, ~150-200 LOC for tests
- No external dependencies beyond stdlib + pydantic-ai

**Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Symlink escape (symlink inside workspace points outside) | Path traversal bypass | `resolve()` follows symlinks before checking containment |
| Large file reads consuming tokens | Token budget blown | Optional `start_line`/`end_line` + configurable `max_chars` truncation |
| Glob matching thousands of files | Slow search | Document that `search_files` is for workspace-scale, not filesystem-scale |
| Windows path separator differences | Inconsistent behavior | `pathlib` handles this natively; tests should run on Windows |

## 5. Follow-up Tasks

1. **Implement `FileToolset`** — `src/owlbear/tools/filesystem.py` with `_safe_path`, 5 tools
2. **Test `FileToolset`** — `tests/test_filesystem_tools.py` with `tmp_path` fixtures, path traversal tests
3. (Task #121 already covers `TerminalToolset` — no new task needed)
