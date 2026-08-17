# Terminal Working Directory Confinement

> **Owning task:** #467 — Add working directory confinement to terminal toolset
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-02 from `docs/security-audit.md`: `TerminalToolset.run_command()` accepts any absolute path as `working_dir` without validation. `FileToolset` and `KnowledgeToolset` sandbox file access to `workspace_root` via `_safe_path`, but terminal commands can operate on the entire filesystem. This is OWASP A01:2021 Broken Access Control.

**Question:** Should we apply the same `_safe_path` pattern to confine `working_dir`?

## 2. Sources Studied

| Source | URL | Relevance | What we learned |
|--------|-----|-----------|-----------------|
| OwlBear `FileToolset._safe_path` | `src/owlbear/tools/filesystem.py` L52-68 | 1.0 | `(root / user_path).resolve()` + `is_relative_to(root)` + null-byte rejection |
| OwlBear `KnowledgeToolset._safe_path` | `src/owlbear/tools/knowledge.py` L81-95 | 1.0 | Identical pattern, copy-pasted from FileToolset |
| OwlBear security audit SEC-02 | `docs/security-audit.md` L52-75 | 1.0 | Identifies the gap as HIGH severity, recommends `_safe_path` pattern |
| Aider `Commands.cmd_run()` | `github.com/Aider-AI/aider` commands.py | 0.8 | Forces `cwd=self.coder.root` — no user-supplied cwd at all |
| Python `pathlib.PurePath.is_relative_to()` | `docs.python.org/3/library/pathlib.html` | 0.9 | String-based; must call `.resolve()` first to eliminate `..` segments |
| OWASP A01:2021 | `owasp.org/Top10/A01_2021-Broken_Access_Control/` | 0.7 | Path traversal is a canonical broken-access-control vulnerability |

## 3. Analysis

### 3.1 Current vulnerability

```python
# terminal.py L164-167 — no confinement
if working_dir is None:
    cwd = self._workspace_root
else:
    cwd_path = Path(working_dir)
    cwd = cwd_path if cwd_path.is_absolute() else self._workspace_root / cwd_path
```

An LLM agent can pass `working_dir="/etc"` or `working_dir="../../"` and run commands outside the workspace.

### 3.2 Approach comparison

| Approach | Complexity | Security | Breaks existing? | KISS |
|----------|-----------|----------|-------------------|------|
| A. Inline `_safe_path` in terminal.py | Low | High | No | High |
| B. Extract shared `safe_path()` helper | Medium | High | No | Medium |
| C. Ignore `working_dir` entirely (like Aider) | Low | Highest | Yes — removes feature | High |

**Option A** is the right choice. It matches the existing pattern, is a ~10-line change, and doesn't disrupt the API. Option B (extracting a shared helper) is worth doing separately since `_safe_path` is already duplicated across FileToolset and KnowledgeToolset, but mixing refactoring with a security fix is bad practice. Option C is too restrictive — agents legitimately need subdirectory cwd.

### 3.3 Implementation pattern

Apply directly in `run_command()` at the working-directory resolution block:

```python
# Resolve working directory with confinement
if working_dir is None:
    cwd = self._workspace_root
else:
    if "\x00" in working_dir:
        msg = f"Path outside workspace: {working_dir!r}"
        raise PermissionError(msg)
    cwd_path = Path(working_dir)
    cwd = (cwd_path if cwd_path.is_absolute() else self._workspace_root / cwd_path).resolve()
    if not cwd.is_relative_to(self._workspace_root.resolve()):
        msg = f"Path outside workspace: {working_dir}"
        raise PermissionError(msg)
```

Key details:

- Resolve `self._workspace_root` too (it may not be stored resolved — currently it isn't, unlike FileToolset which stores `workspace_root.resolve()`)
- Null-byte check first (prevents OS truncation attacks)
- `PermissionError` matches the existing convention in FileToolset/KnowledgeToolset

### 3.4 Edge cases

| Input | Expected | Notes |
|-------|----------|-------|
| `None` | `self._workspace_root` | Unchanged behavior |
| `"subdir"` | `workspace_root/subdir` resolved | Valid relative path |
| `"/etc"` | `PermissionError` | Absolute path outside workspace |
| `"../../escape"` | `PermissionError` | Traversal attempt |
| `"sub\x00dir"` | `PermissionError` | Null-byte injection |
| `str(workspace_root / "sub")` | `workspace_root/sub` | Absolute path inside workspace — allowed |

## 4. Recommendation (.90 confidence)

**Option A: Inline `_safe_path` pattern in terminal.py.** Low risk, small diff, consistent with existing codebase. The `_workspace_root` should also be stored resolved in `__init__` (like FileToolset does with `self._root`). This is a one-line addition to `__init__`.

Risk: Agent commands that intentionally need external cwd (e.g., system tools) will break. Mitigation: This is desired behavior — the security boundary is the workspace.

## 5. Follow-up Tasks

The task #467 already exists and covers the implementation. No new tasks needed — the implementation is straightforward. A separate DRY task for extracting `_safe_path` into a shared utility may be warranted but is out of scope.

### Testing strategy

Tests to add in `test_terminal_tools.py`:

1. `test_working_dir_absolute_outside_raises` — `working_dir="/etc"` → `PermissionError`
2. `test_working_dir_traversal_raises` — `working_dir="../../escape"` → `PermissionError`
3. `test_working_dir_null_byte_raises` — `working_dir="sub\x00dir"` → `PermissionError`
4. `test_working_dir_absolute_inside_allowed` — `working_dir=str(tmp_path / "sub")` → succeeds
5. Existing `test_relative_working_dir` and `test_absolute_working_dir` validate happy paths

The existing `test_absolute_working_dir` test passes an absolute path to a subdirectory of `tmp_path` — this should continue to work after the fix since it's inside `workspace_root`.
