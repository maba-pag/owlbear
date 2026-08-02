---
id: 524
title: Scaffold mcp-memory package
status: archived
priority: medium
created: 2026-04-01 16:11:09.992105+02:00
updated: 2026-04-02 16:34:23.762841+02:00
started: 2026-04-02 16:33:44.270849+02:00
completed: 2026-04-02 16:33:44.270849+02:00
tags:
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

AC:
- [ ] Package structure: `packages/mcp-memory/` with pyproject.toml (name: owlbear-mcp-memory, deps: mcp[cli]>=1.26, hatch wheel: src/owlbear_mcp_memory), `src/owlbear_mcp_memory/__init__.py`, `__main__.py` (runs `mcp.run()` per mcp-kanban pattern), `server.py`, `models.py`
- [ ] models.py: Pydantic `MemoryEntry` model (BaseModel, ConfigDict) with 11 fields: id (str, UUID4), content (str), category (Literal[preference,knowledge,context,behavior,goal]), confidence (float, 0.0-1.0), created_at (str), updated_at (str), source (str), scope_agent (str | None), scope_project (str | None), approval_state (Literal[pending,approved,deleted]), deleted_at (str | None)
- [ ] server.py: `AppContext` dataclass with `conn: sqlite3.Connection` and `project_name: str | None`. Async lifespan that: (a) resolves DB path from OWLBEAR_MEMORY_DB_PATH env var, default `data/memory/memory.db`; (b) creates parent directories if absent; (c) opens sqlite3 connection; (d) sets `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`; (e) reads project name from `owlbear-project.json` via stdlib json (no cross-package import, just `data.get(name)`); (f) runs `CREATE TABLE IF NOT EXISTS memory_entries` DDL; (g) yields AppContext; (h) closes connection in finally. `mcp = FastMCP(owlbear-memory, lifespan=app_lifespan)`. `__all__` listing public symbols. No tool implementations
- [ ] SQLite DDL: `memory_entries` table with columns matching MemoryEntry (id TEXT PRIMARY KEY, content TEXT NOT NULL, category TEXT NOT NULL, confidence REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, source TEXT NOT NULL, scope_agent TEXT, scope_project TEXT, approval_state TEXT NOT NULL DEFAULT 'pending', deleted_at TEXT)
- [ ] scripts/setup.py: Add `owlbearMemory` stdio entry (`uv run --project {rel} -m owlbear_mcp_memory`) to `create_mcp_config()` servers dict. Update docstring: four to five MCP server entries, three to four owlbear stdio servers. Note: only affects fresh installs due to existing early-return guard
- [ ] tests/test_package_boundary.py: Add `owlbear_mcp_memory: set()` to ALLOWED_IMPORTS
- [ ] Root pyproject.toml: Add `packages/mcp-memory/src` to tool.ruff.src array

[[2026-04-01]] Wed 23:17
## Architecture Review
VERDICT: APPROVE
DR Verification: docs/decisions/resolved/387-memory-mcp-architecture.md approved: true (Option A)

### AC Assessment
Package structure: Clear, follows mcp-kanban template. Kept.
models.py MemoryEntry: Original had 12 fields with content_hash (pattern 3, not in DR). Reduced to 11. Rewritten.
server.py AppContext + lifespan: Original vague. Now step-by-step (a)-(h). Rewritten.
SQLite DDL: Original said 12 fields per design without listing. Now explicit column defs. Rewritten.
setup.py: Original said 4th MCP server. Corrected to 5th entry (4th stdio). Rewritten.
pyproject.toml workspace: Original misleading, workspace glob auto-discovers. Removed (no-op).
test_package_boundary.py: Clear as-is. Kept.
ruff src array: Clear as-is. Kept.

### Architecture Notes
Pattern: mcp-kanban for file skeleton, mcp-knowledge for SQLite lifespan, mcp-project for project identity. Project identity via inline json.loads (no cross-package dep). WAL mode new to codebase, required per design doc for concurrent agent sessions. Default DB path: data/memory/memory.db (relative, consistent with mcp-knowledge pattern). content_hash excluded per DR #387 Option A.

### Changes Made
- Rewrote AC (removed misleading workspace member, added directory creation to lifespan spec)
- Removed content_hash from schema (DR compliance)
- Specified inline project identity parsing (no owlbear_mcp_project dependency)

### Dependencies
- Verified: DR #387 approved (Option A), no code dependencies needed
- No depends_on required: standalone scaffold

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Key challenges: (1) content_hash past DR, (2) setup.py early-return, (3) project identity dependency, (4) WAL novel, (5) relative path
- Architect response: accepted 1 (removed content_hash), accepted 3 (inline json), noted 2 (fresh-install caveat), rebutted 5 (matches mcp-knowledge). Revised confidence: .88

[[2026-04-02]] Thu 04:52
## Builder Notes
- Files changed: packages/mcp-memory/pyproject.toml, src/owlbear_mcp_memory/__init__.py, __main__.py, models.py, server.py, tests/test_package_boundary.py, pyproject.toml, scripts/setup.py
- Tests: 62 passed, coverage server.py 100%, models.py 100%
- Lint: ruff clean on all changed files
- Evidence: 62 passed in 3.84s; ASYNC240 suppressed with noqa on startup-only pathlib reads
- Fixes applied: Removed type annotation from ALLOWED_IMPORTS (ast.Assign vs ast.AnnAssign for test); added owlbear_mcp_memory to pyproject.toml coverage source_pkgs

[[2026-04-02]] Thu 06:47
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Tech stack: 4â†’5 servers, added mcp-memory; MCP Conventions: 'All three'â†’'All four' + mcp-memory; Directory table: added packages/mcp-memory/ row |
| 2 | Docstrings | Yes | Pass | server.py: module docstring, AppContext docstring, app_lifespan docstring with step list; models.py: module docstring, MemoryEntry class docstring; __init__.py: module docstring; __main__.py: module docstring |
| 3 | docs/sources/overview.md | No | N/A | Scaffold uses only internal package patterns (mcp-kanban, mcp-knowledge, mcp-project) â€” no external sources |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc | No | N/A | Design governed by DR #387 (resolved), no research doc produced |

### Files Updated
- .github/copilot-instructions.md (committed e4e325f)

### Scratch Files Cleaned
- None

[[2026-04-02]] Thu 07:44
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Package structure | packages/mcp-memory/ with pyproject.toml, __init__.py, __main__.py, server.py, models.py verified | PASS |
| models.py MemoryEntry | 11 fields confirmed, Pydantic BaseModel + ConfigDict, correct Literal types | PASS |
| server.py AppContext + lifespan | Steps (a)-(h) all verified, __all__ listing, FastMCP('owlbear-memory'), no tools | PASS |
| SQLite DDL | All 11 columns match MemoryEntry, correct types and defaults | PASS |
| scripts/setup.py | owlbearMemory stdio entry added, docstring updated four-to-five | PASS |
| test_package_boundary.py | owlbear_mcp_memory: set() in ALLOWED_IMPORTS | PASS |
| Root pyproject.toml | packages/mcp-memory/src in tool.ruff.src | PASS |

### Test Results
- pytest: 2327 passed, 257 failed, 8 skipped, 1 error
- 3 failures IN SCOPE: test_setup_script.py server-count assertions expect 4, got 5 after #524 added owlbearMemory
- 254 other failures are from unrelated tasks (quality_runner_wiring, mcp_kanban_edit, etc.)
- ruff: clean on all #524 files

### Regression detail
- test_mcp_json_has_exactly_three_server_entries: asserts len==4, now 5
- test_mcp_server_names_are_camelcase: expected set missing owlbearMemory
- test_mcp_json_has_exactly_four_server_entries: asserts len==4, now 5
These are pre-existing tests from earlier tasks that the builder broke by adding the 5th server without updating the assertions.

### Reviewer gap
No Review Evidence section in task body. Task appears to have passed review without documented evidence.

### AC quality score: 5
AC was specific, complete, step-by-step (a)-(h) lifespan spec led to clean implementation.

### Deduction breakdown
- -.05: 3 full-suite test failures in task scope (test_setup_script.py broken by #524 change)
- -.02: Missing reviewer evidence section in task body
### Confidence: .93
### Action: reject to review

[[2026-04-02]] Thu 11:40
## Test-Writer Notes
- Audit-reject repair cycle: auditor rejected to review due to 3 broken test assertions
- Test file updated: tests/test_setup_script.py
- Fixed assertions (4 to 5 servers after owlbearMemory added by #524):
  - TestFromAC_McpConfig::test_mcp_json_has_exactly_three_server_entries: 4 to 5
  - TestFromAC_McpServerNames::test_mcp_server_names_are_camelcase: added owlbearMemory to expected set
  - TestFromAC_GitHubMcpServer::test_mcp_json_has_exactly_four_server_entries: 4 to 5, updated docstring
- All 3 tests: PASS (3 passed, 0.28s)
- ruff: clean
- Note: builder-written test_scaffold_mcp_memory_524.py provides full AC1-AC7 coverage (62 tests)

[[2026-04-02]] Thu 12:11
## Builder Notes (Repair)\n- Audit-reject repair: 3 broken test assertions in test_setup_script.py fixed by test-writer (committed 51bd1e3)\n- Tests: 3 passed (test_mcp_json_has_exactly_three_server_entries, test_mcp_server_names_are_camelcase, test_mcp_json_has_exactly_four_server_entries)\n- Lint: ruff clean on tests/test_setup_script.py\n- No code changes needed — test-writer commit sufficient to resolve regression

[[2026-04-02]] Thu 16:34
## Audit (Re-audit)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Package structure | pyproject.toml, __init__.py, __main__.py, server.py, models.py all exist under packages/mcp-memory/ | PASS |
| models.py MemoryEntry | 11 fields, BaseModel+ConfigDict, correct Literal types verified | PASS |
| server.py AppContext+lifespan | Steps (a)-(h) verified, __all__ listing, FastMCP('owlbear-memory'), no tools | PASS |
| SQLite DDL | 11 columns match MemoryEntry, correct types and defaults | PASS |
| scripts/setup.py | owlbearMemory stdio entry at L78, docstring updated | PASS |
| test_package_boundary.py | owlbear_mcp_memory: set() at L44 | PASS |
| Root pyproject.toml | packages/mcp-memory/src at L37 in tool.ruff.src | PASS |

### Test Results
- pytest (scoped): 125 passed (scaffold_mcp_memory_524 + setup_script + package_boundary)
- pytest (full): 2372 passed, 299 failed, 8 skipped (0 failures in #524 scope)
- ruff: clean on all #524 files

### Upstream Commits Verified
- c383d7e test: add failing tests (#524, test-writer)
- 7e86a63 feat: scaffold mcp-memory (#524, builder)
- 51bd1e3 test: fix server-count assertions (#524, test-writer)
- e4e325f docs: update copilot-instructions (#524, writer)

### AC quality score: 5
AC was specific, complete, step-by-step lifespan spec. Clean implementation.

### Deduction breakdown
- -.02: Missing reviewer evidence section in task body
### Confidence: .98
### Action: archive
