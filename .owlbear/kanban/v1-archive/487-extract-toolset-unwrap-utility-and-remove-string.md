---
id: 487
title: Extract toolset unwrap utility and remove string type dispatch
status: archived
priority: important
created: 2026-03-04T07:38:03.8534958+01:00
updated: 2026-03-07T18:07:55.3866505+01:00
started: 2026-03-06T20:59:54.7528993+01:00
completed: 2026-03-07T18:07:55.3866505+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:core
class: standard
---

DRY-07/DRY-08: Extract `unwrap()` and `find_toolset()` utilities; replace string type dispatch with `isinstance()`. See `docs/software-design-audit.md`.

## AC

### New utilities in `tools/protocols.py`

- [ ] `unwrap(toolset: AbstractToolset) -> AbstractToolset` exists — peels all `WrapperToolset` layers using `isinstance(inner, WrapperToolset)` (from `pydantic_ai.toolsets.wrapper`); returns the innermost non-wrapper toolset
- [ ] `find_toolset(toolsets: Iterable[AbstractToolset], cls: type[T]) -> T | None` exists — iterates toolsets, calls `unwrap()` on each, returns first match via `isinstance(inner, cls)` or `None`

### Production refactoring

- [ ] 4 `while hasattr(inner, "wrapped")` loops replaced with `unwrap()` calls: bootstrap.py L799, L866, L963 and projects/toolset.py L152
- [ ] L709 single-level peel (`ts.wrapped if isinstance(ts, HookedToolset) else ts`) also replaced with `unwrap(ts)`
- [ ] L709: `type(inner).__name__ in _destructive` replaced with `isinstance(inner, (GitLocalToolset, TerminalToolset, GitHubToolset))`; delete the `_destructive` string set (dead code after change)
- [ ] L868: `type(inner).__name__ == "ProjectToolset"` replaced with `find_toolset(toolsets, ProjectToolset)`
- [ ] L965: `type(inner).__name__ == "SkillRegistry"` replaced with `find_toolset(toolsets, SkillRegistry)`
- [ ] L801: unwrap loop replaced with `unwrap()`; `type(inner).__name__` for dict-key construction is **retained** (tool_map is string-keyed by design)

### Test updates

- [ ] Unit tests for `unwrap()` exist in `tests/test_toolset_protocols.py`: plain toolset (no wrapping), single wrapper, nested wrappers
- [ ] Unit tests for `find_toolset()` exist: match found, no match returns None, match through wrapper layers
- [ ] 4 test-site unwrap+name patterns replaced with `unwrap()` call: test_bootstrap.py `_inner_name` helper (L689-693), test_bootstrap.py L1078-1080, L1173-1175, test_bootstrap_integration.py `_toolset_names` helper (L34-38)

### Quality gate

- [ ] All existing tests pass
- [ ] `ruff check` clean

## Architecture Notes

**Pattern to follow**: `projects/toolset.py` L152 already imports from `tools.protocols` (`WorkspaceAware`). Same module, same import style.

**Import for `WrapperToolset`**: Use `from pydantic_ai.toolsets.wrapper import WrapperToolset` — same import used in `tools/hooked.py` L32 and `safety/gate.py` L31.

**No circular import risk**: `unwrap()` imports only `WrapperToolset` from pydantic_ai. `find_toolset()` is generic (takes `cls` param). No concrete OwlBear class imports in `tools/protocols.py`.

**Existing local imports to reuse**: `SkillRegistry` at bootstrap.py L625/L69, `ProjectToolset` at L845, `GitLocalToolset`/`TerminalToolset`/`GitHubToolset` are top-level imports.

**TDD order**: (1) write tests for `unwrap()` + `find_toolset()` in new test file, (2) implement utilities, (3) refactor production code using utilities, (4) refactor test helpers to use `unwrap()`, (5) verify all tests pass.

## Research Findings (2026-03-06)

### 1. Unwrap loop locations (DRY-07) — 4 production sites

| # | File | Line | Context |
|---|------|------|---------|
| 1 | `bootstrap.py` | L799 | `build_agent_registry` — builds `tool_map` by class name |
| 2 | `bootstrap.py` | L866 | `_patch_project_toolset_agent` — finds `ProjectToolset` |
| 3 | `bootstrap.py` | L963 | `bootstrap()` — finds `SkillRegistry` |
| 4 | `projects/toolset.py` | L152 | `update_all_workspaces` — finds `WorkspaceAware` toolsets |

All 4 use identical 3-line pattern: `inner = ts; while hasattr(inner, "wrapped"): inner = inner.wrapped`

### 2. String type dispatch locations (DRY-08) — 4 production sites + 1 non-standard peel

| # | File | Line | Pattern | Action |
|---|------|------|---------|--------|
| 1 | `bootstrap.py` | L709 | `type(inner).__name__ in _destructive` + single-level peel | `unwrap()` + `isinstance()` tuple; delete `_destructive` set |
| 2 | `bootstrap.py` | L801 | `type(inner).__name__` for `tool_map` dict keys | `unwrap()` for peeling; keep string keys |
| 3 | `bootstrap.py` | L868 | `== "ProjectToolset"` | `find_toolset()` |
| 4 | `bootstrap.py` | L965 | `== "SkillRegistry"` | `find_toolset()` |

Test files have 4 sites with paired unwrap+name patterns: test_bootstrap.py L691-693, L1078-1080, L1173-1175; test_bootstrap_integration.py L36-38.

### 3. Circular import analysis

- `unwrap()` imports only `WrapperToolset` from pydantic_ai — zero OwlBear imports, zero circular risk.
- `find_toolset()` is generic (takes `cls` param) — no concrete class imports needed in the module.
- Call sites in `bootstrap.py` already do local imports for `ProjectToolset` (L845) and `SkillRegistry` (L625). `isinstance()` uses same imports — no new circular risk.
- `GitLocalToolset`, `TerminalToolset`, `GitHubToolset` are top-level imports in `bootstrap.py` — `isinstance()` works directly.
