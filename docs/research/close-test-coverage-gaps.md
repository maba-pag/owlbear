# Close Minor Test Coverage Gaps Across Modules

> **Owning task:** #575 — Close minor test coverage gaps across modules
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #575 lists 6 modules with minor coverage gaps totalling ~35 uncovered lines. Goal: determine exact files, line numbers, and test strategies so the builder can write targeted tests.

## 2. Sources Studied

| Source | Type | Relevance |
|---|---|---|
| `docs/test-quality-audit.md` | Internal audit | 1.0 — original gap identification |
| pytest `--cov-report=term-missing` output | Tool output | 1.0 — verified current line numbers |

No external sources needed — this is standard coverage analysis.

## 3. Verified Coverage Gaps

Coverage was re-measured on 2026-03-07. One gap (github_api) has been closed since the audit.

| Module | File | Current | Miss | Lines | What's uncovered |
|---|---|---|---|---|---|
| bootstrap | `src/owlbear/bootstrap.py` | 96% | 14 | 369-373, 424-426, 540-542, 642-643, 750-751, 845-846 | 6 `except Exception` handler paths (see below) |
| browser/config | `src/owlbear/tools/browser/config.py` | 94% | 4 | 73, 76-78 | `cdp_endpoint` URL parse failure raises `ValueError` |
| ask_user | `src/owlbear/tools/ask_user.py` | 96% | 3 | 152-153, 156 | `_receive_option`: TimeoutError + `None` response paths |
| ~~github_api~~ | ~~`src/owlbear/tools/github_api.py`~~ | **100%** | 0 | — | **Already closed** — no work needed |
| filesystem | `src/owlbear/tools/filesystem.py` | 96% | 4 | 53, 222, 226-227 | `update_workspace`, glob-escape guard, OSError in content search |
| usage | `src/owlbear/memory/usage.py` | ~97% | ~2 | 81-83 | `summary(window=None)` all-records branch |

**Total remaining: 27 lines across 5 modules** (not 35 — github_api is done).

### Bootstrap exception paths (14 lines)

| Lines | Function | Exception path |
|---|---|---|
| 369-373 | `_build_knowledge_toolset` | `inter_doc_graph_building=True` import/construct |
| 424-426 | `_build_knowledge_toolset` | Catch-all failure → log + return None |
| 540-542 | `_build_web_search_toolset` | Catch-all failure → log + return None |
| 642-643 | `build_toolsets` | GitHubToolset creation failure |
| 750-751 | `_build_mcp_registry` | `register_default_servers` failure |
| 845-846 | `_add_project_toolset` | ProjectToolset creation failure |

**Strategy:** Mock inner imports to raise, assert `logger.warning` called and result is `None`.

### Browser config validators (4 lines)

- L73: `except Exception` in `_cdp_endpoint_localhost_only` (unparseable URL)
- L76-78: `ValueError` raise inside that handler

**Strategy:** `BrowserConfig(cdp_endpoint=":::not-a-url")` → expect `ValidationError`.

### ask_user timeout/None in `_receive_option` (3 lines)

- L152-153: `except TimeoutError` → `_handle_timeout()`
- L156: `raw is None` → `_handle_timeout()`

**Strategy:** Mock `channel.receive()` to raise `asyncio.TimeoutError` (for L152-153) or return `None` (for L156), with options provided.

### Filesystem edge paths (4 lines)

- L53: `update_workspace()` body — just needs any call to the method
- L222: glob result outside workspace root (defensive guard)
- L226-227: `OSError` reading file during content-regex search

**Strategy:** L53: call `update_workspace(new_path)` and assert `_root` changed. L222: create a symlink escaping workspace. L226-227: mock `Path.read_text` to raise `OSError` or create an unreadable file.

### usage.py `summary(None)` (2 lines)

- L81-83: `summary(window=None)` takes the `self.load()` branch

**Strategy:** `tracker.summary(window=None)` with pre-existing records.

## 4. Recommendation (.90 confidence)

Split into **2 tasks** by effort:

1. **Quick wins (13 lines, 4 modules):** browser config, ask_user, filesystem, usage — simple edge-case tests, no complex mocking.
2. **Bootstrap exception paths (14 lines):** 6 exception handlers need import mocking — slightly more setup.

Both are straightforward but the bootstrap task is repetitive (6 similar exception handlers).

**Risk:** Filesystem L222 (symlink escape) may be tricky on Windows. Alternative: use `unittest.mock.patch` on `Path.resolve()` to return a path outside root.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Cover bootstrap exception handler paths (14 lines)" --priority nice-to-have --status backlog --tags "test,phase-12" --description "Add tests for 6 exception handlers in bootstrap.py (lines 369-373, 424-426, 540-542, 642-643, 750-751, 845-846). Mock inner imports/constructors to raise, assert logger.warning called and return is None. Target: 99%+ coverage on bootstrap.py. See docs/research/close-test-coverage-gaps.md."

kanban\kanban-md.exe create "Cover edge-case paths in browser config, ask_user, filesystem, usage (13 lines)" --priority nice-to-have --status backlog --tags "test,phase-12" --description "4 modules with minor gaps: (1) browser/config.py L73,76-78 — unparseable cdp_endpoint; (2) ask_user.py L152-153,156 — TimeoutError + None in _receive_option; (3) filesystem.py L53,222,226-227 — update_workspace + glob escape + OSError; (4) usage.py L81-83 — summary(None). See docs/research/close-test-coverage-gaps.md."
```
