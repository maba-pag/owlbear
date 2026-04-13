---
id: 870
title: Clean up superseded Edge/CDP code and test files
status: backlog
priority: needed
created: '2026-04-13T23:22:02.247779+00:00'
updated: '2026-04-13T23:22:02.247779+00:00'
tags:
- pivot
- phase-1
- scope:browser
- type:cleanup
parent: 751
depends_on:
- 869
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

After Playwright launcher pivot (#869) is complete, remove old Edge/CDP code that is dead. Also clean up test files that tested the old approach.

## Acceptance Criteria

1. Remove or deprecate old Edge/CDP modules:
   - `serve/browser/src/owlbear_browser/launcher.py` — `find_edge_binary()`, `build_launch_args()`, `launch_edge()` (all Edge-specific)
   - `serve/browser/src/owlbear_browser/edge_launcher.py` — `EdgeCDPLauncher` class
   - `serve/browser/src/owlbear_browser/cdp.py` — `CDPConnectionManager`, `playwright_connect_over_cdp()`
2. Remove old Edge/CDP error types from `_errors.py`:
   - `EdgeNotFoundError` — no longer raised
   - `CDPConnectionError` — no longer raised
3. Update `__init__.py` — remove old Edge/CDP exports
4. Remove or archive superseded test files:
   - `tests/test_edge_launcher_cdp_755.py` (21 Edge CDP tests)
   - `tests/test_browser_package_scaffold_787.py` (4 tests checking Edge launcher deps)
   - `tests/test_browser_cdp_775.py` (if exists)
   - `tests/test_mcp_browser_fetcher_852.py` (Phase 1 fetcher tests — 13 of 17 already slated for removal by #859)
   - Any other test files that import from `owlbear_browser.launcher`, `owlbear_browser.cdp`, or `owlbear_browser.edge_launcher`
5. No import errors across the codebase after removal
6. All remaining tests pass
7. ruff clean

## Notes

- This is a cleanup task — no new features
- Run `grep -r "edge_launcher\|CDPConnectionManager\|find_edge_binary\|launch_edge\|connect_over_cdp" tests/` to find all affected test files
- Verify no MCP tool code imports the old modules before deleting