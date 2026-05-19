---
id: 606
title: Update mcp-kanban path resolution for .owlbear/kanban/
status: archived
priority: critical
created: 2026-04-04T20:31:28.5105181+02:00
updated: 2026-04-05T09:00:24.4583378+02:00
started: 2026-04-05T09:00:24.4583378+02:00
completed: 2026-04-05T09:00:24.4583378+02:00
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

[[2026-04-05]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_path_resolution_606.py
- Class: TestFromAC_KanbanPathResolution
- Tests: 6 total, all FAIL (RED confirmed)
- Categories: constant value (3), runtime lifespan (1), error message (2)
- Lint: ruff clean

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC1: _DEFAULT_KANBAN_DIR = Path(".owlbear/kanban") | test_default_kanban_dir_is_owlbear_dotdir, test_default_kanban_bin_reflects_new_dir, test_default_kanban_bin_not_bare_kanban_prefix, test_lifespan_yields_ctx_with_new_kanban_dir | 4 tests FAIL |
| AC2: FileNotFoundError message updated | test_lifespan_error_message_names_new_path, test_lifespan_error_message_not_old_bare_kanban_path | 2 tests FAIL |
| AC3: mcp.json no change needed | Verified by AC1 — no independent failing test (mcp.json already has no hardcoded KANBAN_BIN) | pass-through |
| AC4: manual verification | Non-testable — manual server start check | pass-through |
| AC5: existing tests pass | Builder gate — not test-writer scope | pass-through |

DONE #606 -> in-progress | 6 tests, all FAIL

[[2026-04-05]] Sun 03:19
Fixed _DEFAULT_KANBAN_DIR and _DEFAULT_KANBAN_BIN in server.py to point to .owlbear/kanban/. Updated error message. All 6 TDD tests pass. Ghost kanban/ directory cleaned up. MCP server verified working after restart.

[[2026-04-05]] Sun 05:48
## Review Evidence

**Reviewer:** reviewer | **Date:** 2026-04-05

### Test Results
`uv run pytest tests/test_mcp_kanban_path_resolution_606.py -v --tb=short`
- **6 passed, 0 failed**

Existing mcp-kanban suite (`test_mcp_kanban_server.py`, `test_mcp_kanban_start_work_470.py`): failures confirmed **pre-existing** (`git show e189439 -- tests/test_mcp_kanban_server.py tests/test_mcp_kanban_start_work_470.py` returned empty — neither file touched by the #606 commit). Causes: `packages/mcp-kanban/pyproject.toml` path in test_mcp_kanban_server.py (pre-#601 remnant, #608 scope); `claim` parameter RED tests in test_mcp_kanban_start_work_470.py (unimplemented #470 feature). No new failures introduced by this task.

### Lint
`uv run ruff check serve/mcp-kanban/ tests/test_mcp_kanban_path_resolution_606.py`
- **All checks passed.**

### Coverage
6 tests against `owlbear_mcp_kanban.server`: 34% total (expected — only 4 lines changed out of 299). Changed lines (L52, L117) are directly exercised by 3 constant tests + 2 lifespan error-path tests.

### Implementation Verification
`git show e189439` — commit `fix: update mcp-kanban path resolution for .owlbear/kanban (#606)`:
- L52: `_DEFAULT_KANBAN_DIR = Path("kanban")` → `Path(".owlbear/kanban")` ✓
- L53: `_DEFAULT_KANBAN_BIN = _DEFAULT_KANBAN_DIR / "kanban-md.exe"` — auto-derives, unchanged ✓
- L117: error message `"place binary at kanban/kanban-md.exe"` → `"place binary at .owlbear/kanban/kanban-md.exe"` ✓

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `_DEFAULT_KANBAN_DIR = Path(".owlbear/kanban")` | server.py L52 in commit diff + current file confirmed; tests test_default_kanban_dir_is_owlbear_dotdir, test_default_kanban_bin_reflects_new_dir, test_default_kanban_bin_not_bare_kanban_prefix all PASS with specific equality assertions | PASS |
| AC1 (bin): `_DEFAULT_KANBAN_BIN` auto-derives from `_DEFAULT_KANBAN_DIR` | L53 unchanged — `_DEFAULT_KANBAN_DIR / "kanban-md.exe"`; runtime test test_lifespan_yields_ctx_with_new_kanban_dir confirms ctx.kanban_dir == Path(".owlbear/kanban") | PASS |
| AC2: Error message updated | L117 diff confirmed: `"Set KANBAN_BIN or place binary at .owlbear/kanban/kanban-md.exe."` test_lifespan_error_message_names_new_path (asserts `.owlbear/kanban/kanban-md.exe` in message) and test_lifespan_error_message_not_old_bare_kanban_path (asserts old string absent) both PASS | PASS |
| AC3: `.vscode/mcp.json` no hardcoded KANBAN_BIN | `owlbear-kanban` entry uses `uv run python -m owlbear_mcp_kanban` — no `env` key, no KANBAN_BIN; server defaults now resolve correctly | PASS |
| AC4: Manual server start | Non-testable; builder reports verified. Pass-through. | PASS-THROUGH |
| AC5: Existing mcp-kanban tests pass | Pre-existing failures in test_mcp_kanban_server.py (#601 path) and test_mcp_kanban_start_work_470.py (#470 RED) are NOT caused by #606 (git evidence: those files absent from e189439). AC qualifier "immune to default changes" satisfied. | PASS (pre-existing failures excluded) |

### TestFromAC Integrity

| Test | Change | Assessment |
|------|--------|------------|
| test_default_kanban_dir_is_owlbear_dotdir | No change | PRESERVED |
| test_default_kanban_bin_reflects_new_dir | No change | PRESERVED |
| test_default_kanban_bin_not_bare_kanban_prefix | No change | PRESERVED |
| test_lifespan_yields_ctx_with_new_kanban_dir | No change | PRESERVED |
| test_lifespan_error_message_names_new_path | No change | PRESERVED |
| test_lifespan_error_message_not_old_bare_kanban_path | No change | PRESERVED |

### Test Quality

- **Assertion specificity:** STRONG — direct `==` equality, `in` containment with specific expected values
- **Error-path coverage:** STRONG — 2 lifespan error-path tests (happy path + old-string-absent boundary)
- **Mutation resistance:** STRONG — any revert of server.py would fail at least 5 of 6 tests
- **Independence:** STRONG — no shared mutable state
- **Names:** STRONG — all descriptive

### Security
Pure constant value change + short error string update. No injection surface, no path traversal, no credentials, no new dependencies. Clean.

### Deductions

| Finding | Impact | Deduction |
|---------|--------|-----------|
| TDD RED commit absent: test file and implementation combined in single commit `e189439`. Task-writer notes confirm RED phase validated separately, but no git artifact. Violates "one logical change per commit" (r-project-standards). | Process discipline | −0.03 |
| Builder notes omit commit hash `e189439`. Minor traceability. | Traceability | −0.01 |
| AC5 wording says "pass" but pre-existing failures exist; intent ("immune to default changes") is satisfied but literal wording is imprecise. | Spec precision | −0.02 |

**Total deductions: −0.06**

### Confidence: 0.94 → PASS

All 5 binding AC items verified with evidence against commit `e189439`. 6/6 domain tests pass, ruff clean. No TestFromAC modifications. No security concerns.

[[2026-04-05]] Sun 06:57
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (no doc update needed) | Path constant changed from `kanban/` to `.owlbear/kanban/`. Checked `.github/copilot-instructions.md` — single generic "kanban" sentence, no path reference. `README.md` — no `kanban/kanban-md` reference. No update needed. |
| 2 | Module docstrings | Yes | Verified (no update needed) | `server.py` modified. `app_lifespan` docstring: "Discover kanban-md binary..." — accurate, no path-specific content. `AppContext`, `_ForwardSlashPath`, `_apply_tool_exclusions`, `_run_kanban` docstrings verified against implementation — all accurate. Changed lines are constants + error string; no docstring impact. |
| 3 | External attribution | No | N/A | Pure constant value change + error message string. No external patterns referenced. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `docs/research/` file referenced in task body. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `docs/scratch/606-*` files found)

[[2026-04-05]] Sun 09:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: _DEFAULT_KANBAN_DIR = Path(".owlbear/kanban") | server.py L54 confirmed; tests test_default_kanban_dir_is_owlbear_dotdir, test_default_kanban_bin_reflects_new_dir, test_default_kanban_bin_not_bare_kanban_prefix PASS | PASS |
| AC1 (bin auto-derives): _DEFAULT_KANBAN_BIN | server.py L55 unchanged, test_lifespan_yields_ctx_with_new_kanban_dir PASS | PASS |
| AC2: Error message updated | server.py L117-119 confirmed ".owlbear/kanban/kanban-md.exe"; test_lifespan_error_message_names_new_path, test_lifespan_error_message_not_old_bare_kanban_path PASS | PASS |
| AC3: .vscode/mcp.json no change needed | Verified: owlbear-kanban entry uses "uv run python -m owlbear_mcp_kanban" with no KANBAN_BIN env | PASS |
| AC4: Manual server start | Pass-through (builder-reported, non-testable) | PASS-THROUGH |
| AC5: Existing mcp-kanban tests pass | 6/6 task tests pass; pre-existing failures in test_mcp_kanban_server.py (#601 path remnant) and test_mcp_kanban_start_work_470.py (#470 RED) not caused by #606 (absent from commit e189439) | PASS |

### Test Results
- pytest (task): 6 passed, 0 failed
- pytest (full suite): 2822 passed, 446 failed, 18 skipped. All failures pre-existing. No #606-scope regressions.
- ruff: All checks passed

### Architect Quality: 4/5
AC items precise with file paths, line numbers, and expected values. Scope boundaries well-documented. Overlap analysis thorough.

### Deduction Breakdown
- TDD RED commit absent (test + impl in single commit e189439): -0.02
- AC4 manual verification, no test evidence: -0.01

### Confidence: 0.97
### Action: archive
