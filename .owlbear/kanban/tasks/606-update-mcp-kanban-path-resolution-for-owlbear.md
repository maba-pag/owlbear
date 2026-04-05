---
id: 606
title: Update mcp-kanban path resolution for .owlbear/kanban/
status: todo
priority: needed
created: 2026-04-04T20:31:28.5105181+02:00
updated: 2026-04-05T00:16:36.1272542+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
parent: 598
depends_on:
    - 601
    - 602
    - 603
class: standard
---

## Summary

Update mcp-kanban path resolution from `kanban/` to `.owlbear/kanban/` for the new folder structure. After #603 moves kanban/ to .owlbear/kanban/, the MCP server defaults must point to the new location.

**Scope clarification:** This task covers only mcp-kanban path resolution. The data/ → store/ default constant changes for mcp-knowledge, mcp-memory, and mcp-project are in #602 scope. The dual knowledge path feature (global + project-local KB) is split to a new ideation task.

## Acceptance Criteria

- [ ] AC1: `_DEFAULT_KANBAN_DIR` updated from `Path("kanban")` to `Path(".owlbear/kanban")` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py L52. `_DEFAULT_KANBAN_BIN` auto-derives correctly (L53, uses `_DEFAULT_KANBAN_DIR` — verify only).
- [ ] AC2: FileNotFoundError message in `app_lifespan` (L115-119) updated from `"place binary at kanban/kanban-md.exe"` to `"place binary at .owlbear/kanban/kanban-md.exe"`
- [ ] AC3: `.vscode/mcp.json` owlbear-kanban entry verified — no change needed if revised defaults resolve correctly (document "no change needed" in commit message)
- [ ] AC4: mcp-kanban server starts and responds to `list_tools` with `.owlbear/kanban/` board (manual verification)
- [ ] AC5: Existing mcp-kanban unit tests pass (test fixtures use mocked Path values in test_server.py, test_start_work_470.py — immune to default changes)

## Files Affected

- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py (L52: `_DEFAULT_KANBAN_DIR`, L115-119: error message)
- .vscode/mcp.json (verify only — no changes expected)

## Scope Boundaries

- Default constant updates for mcp-knowledge/mcp-memory/mcp-project (data/ → store/) → #602
- Integration test path updates (test_integration.py L80 `convention = repo_root / "kanban" / "kanban-md.exe"`) → #608 (breakage from #603 file move, not this task's constant change)
- Dual knowledge path feature (global store/knowledge/ + local .owlbear/knowledge/) → split to new ideation task
- setup.py → setup/init.py migration (creates .owlbear/kanban/ in new projects) → #604

## Dependencies

- #601 (packages/ → serve/): file location changes
- #602 (data/ → store/): other MCP server defaults updated first
- #603 (kanban/ → .owlbear/kanban/): physical directory move completed before code update

## Notes

- After #603 moves kanban/ to .owlbear/kanban/ and before #606 lands, the mcp-kanban server will fail to start with default paths. Users can work around with `KANBAN_BIN=.owlbear/kanban/kanban-md.exe` env var during migration.
- No KANBAN_DIR env var support exists currently (only KANBAN_BIN). Adding one is beyond minimal scope — can be a follow-up if needed.
- Line numbers reference current source (pre-#601 rename). File paths use post-#601 convention (serve/ not packages/).

[[2026-04-05]] Sun 00:16
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One constant update + error message in mcp-kanban server.py. Dual knowledge path split to #616. |
| Interface clarity | PASS | 5 AC items with exact file paths, line numbers, and expected values. |
| Dependency correctness | PASS | Depends on [601, 602, 603]. #603 moves kanban/ to .owlbear/kanban/ before this runs. #601 renames packages/ to serve/. #602 handles other MCP server defaults. |
| Module layering | N/A | Constant value change only — no new modules or cross-package imports. |
| TDD compliance | PASS | Produces testable code change (constant value, error message). Test-writer can verify. |
| KISS/YAGNI | PASS | Minimal scope after removing overlapping AC. Two constants + one error message string. |
| Premise challenge | PASS | mcp-kanban must resolve binary from new location. No alternative — default must match physical path. |
| Pattern consistency | PASS | Follows existing env-var + default Path pattern. KANBAN_BIN override still works. |
| Security surface | PASS | No new system boundaries. Path constant change only. |
| Single domain | PASS | scope:mcp, type:build. All changes in mcp-kanban server module. |

### Overlap Analysis (resolved)

| Original AC | Overlap | Action |
|-------------|---------|--------|
| AC3 (knowledge global KB) | #602 AC3 | REMOVED — already in #602 scope |
| AC4 (knowledge dual path) | New feature | SPLIT to #616 at ideation |
| AC5 (memory from store/) | #602 AC2 | REMOVED — already in #602 scope |
| AC6 (project unchanged) | No-op | REMOVED — project_list change in #602 AC5 |
| AC8 (all MCP tests pass) | #608 | REMOVED — scoped to mcp-kanban tests only (AC5) |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| app_lifespan binary discovery | .owlbear/kanban/kanban-md.exe missing | FileNotFoundError | Yes — AC2 error message + KANBAN_BIN env var fallback | Server fails to start with clear message |
| _run_kanban --dir flag | .owlbear/kanban/ has no config.yml | kanban-md CLI error | Yes — #603 moves all kanban files first | Board ops fail |

### Challenge Results

- Challenger: CONDITIONAL APPROVE (confidence: 0.71)
- Concerns: (1) directory transition strategy, (2) integration test breakage, (3) setup.py coupling
- Architect response: Override with rebuttal
  - Concern 1 (transition): Rebutted. #603 moves directory before #606 runs. No backwards compat per project heuristics.
  - Concern 2 (integration test): Accepted as scope note. test_integration.py L80 breakage from #603 file move, deferred to #608. Added scope boundary.
  - Concern 3 (setup.py): Rebutted. setup.py → setup/init.py is #604 domain. Parallel sibling task.
- Post-rebuttal confidence: 0.88

### Refinements Applied

1. Removed 5 overlapping AC items (covered by #602, #608, or no-op)
2. Renamed task from generic "Update MCP server path resolution" to specific "Update mcp-kanban path resolution for .owlbear/kanban/"
3. Added Files Affected section with exact file paths and line numbers
4. Added Scope Boundaries section with explicit handoff to #602, #604, #608
5. Split dual knowledge path (AC4) to new task #616 at ideation
6. Added migration window note (KANBAN_BIN workaround between #603 and #606)

### Verdict: APPROVE
### Action Taken: Removed overlapping AC, narrowed scope to mcp-kanban only, split dual knowledge path to #616, advanced to todo.

APPROVED #606 -> todo | Narrowed from 4-server scope to mcp-kanban only (other servers in #602). Removed 5 overlapping AC items. Split dual knowledge path to #616 (ideation). Refined to 5 precise AC items with file paths and line numbers. Challenger override: transition concerns rebutted (dependency chain ensures correct order).
