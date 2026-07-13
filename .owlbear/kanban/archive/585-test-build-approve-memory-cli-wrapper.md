---
id: 585
title: 'Test: Build approve_memory CLI wrapper'
status: archived
priority: medium
created: 2026-04-03 17:54:42.345022+02:00
updated: 2026-04-04 16:46:14.804190+02:00
started: 2026-04-04 16:46:14.804190+02:00
completed: 2026-04-04 16:46:14.804190+02:00
tags:
- scope:agents
- phase-2
- test
depends_on:
- 529
class: standard
archival_reason: completed
archival_refs: []
---

TDD RED phase tests for #531 (approve_memory CLI wrapper).

AC:
- [ ] Test file: tests/test_approve_memory_585.py
- [ ] Import path: from owlbear_mcp_memory.approve import main (module at packages/mcp-memory/src/owlbear_mcp_memory/approve.py per #531 AC)
- [ ] Test CLI args: --interactive, --approve, --reject mutually exclusive (argparse error on combination)
- [ ] Test --db-path resolution order: CLI arg > OWLBEAR_MEMORY_DB_PATH env var > default (use monkeypatch for env)
- [ ] Test bare invocation (no flags): lists pending entries as numbered table (index, truncated ID first 8 chars, category, content preview first 80 chars), exits 0
- [ ] Test interactive mode: approve/reject/skip flow with mocked input -- verify set_approval_state called with correct new-state for each choice
- [ ] Test interactive mode: summary line printed after all entries (N approved, N rejected, N skipped)
- [ ] Test batch --approve: calls set_approval_state with new-state=approved for each ID
- [ ] Test batch --reject: calls set_approval_state with new-state=deleted for each ID
- [ ] Test error path A: nonexistent entry_id -- ToolError (isError=true on CallToolResult) printed to stderr, processing continues to next entry
- [ ] Test error path B: disallowed state transition -- error-prefixed string in result text printed to stderr, processing continues
- [ ] Test curation report present: data/memory/curation-report.json exists -- recommendation column displayed in table (use tmp_path fixture for file placement)
- [ ] Test curation report absent (FileNotFoundError): warning to stderr, table renders without recommendation column, no crash
- [ ] Test MCP integration: in-memory transport via create_connected_server-and_client_session with custom lifespan (must include conn.row-factory = sqlite3.Row), list_entries + set_approval_state roundtrip
- [ ] Test exit code: 0 on full success, 1 if any operation failed
- [ ] Test main(argv: list[str] | None = None) -> int signature exists (follows migrate.py pattern)

[[2026-04-03]] Fri 18:18
## Architecture Review
**Verdict:** Approved
**DR Verification:** N/A -- not research-driven (test task for #531 which already passed arch review)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test CLI mutual exclusion | Clear, verifiable | Kept |
| Test bare invocation | Vague on output format | Refined: added format details (index, truncated ID, category, preview) |
| Test interactive flow | OK | Kept, added summary line test |
| Test batch approve/reject | OK | Kept |
| Test error handling | Conflates ToolError and error-string paths | Split into path A (ToolError) and path B (error prefix) |
| Test curation report | OK but no file path control | Added tmp_path guidance |
| Test MCP integration | Missing row-factory note | Added custom lifespan requirement |
| Test exit codes | OK | Kept |
| Test main signature | OK | Kept |
| (missing) --db-path | Not in original AC | Added |
| (missing) interactive summary | Not in original AC | Added |
| (missing) test file location | Not in original AC | Added |
| (missing) import path | Not in original AC | Added |

### Architecture Notes
Follows established patterns: migrate.py for CLI structure, test_integration.py (mcp-kanban) for MCP in-memory transport.
Custom test lifespan must include row-factory=sqlite3.Row (production app_lifespan omits this; #531 AC already specifies custom lifespan).
Test file at root tests/ following existing convention (test_memory_tools_525.py, test_memory_tools_556.py).

### Changes Made
- Refined AC: 11 lines to 16 lines (added test file path, import path, --db-path, display format details, summary output, split error paths, MCP lifespan note)

### Dependencies
- Verified: #529 (set_approval_state) -- archived
- No additional deps needed: custom test lifespan avoids dependency on #586

### Challenge Results
- Challenger: reconsider (confidence .62)
- Key challenges: module location ambiguity, error semantics conflation, missing display/db-path/summary tests, row-factory gap
- Architect response: accepted 5 of 7 challenges, refined AC accordingly. Rebutted row-factory as dependency (custom test lifespan handles it). Rebutted test file location under packages/ (root tests/ is project convention per existing test_memory_tools_*.py)

[[2026-04-03]] Fri 19:00
## Test-Writer Notes
- Test file: tests/test_approve_memory_585.py
- Classes: TestFromAC_ModuleImport, TestFromAC_CLIMutualExclusion, TestFromAC_DBPathResolution, TestFromAC_BareInvocation, TestFromAC_InteractiveMode, TestFromAC_BatchMode, TestFromAC_ErrorHandling, TestFromAC_CurationReport, TestFromAC_MCPIntegration, TestFromAC_ExitCodes
- Tests per category: happy 20, edge 5, error 12, boundary 7
- Total: 44 tests, all FAIL (ModuleNotFoundError on collection)
- ruff: clean
- All 16 AC lines covered

[[2026-04-04]] Sat 03:09
## Review Evidence\n\n47/47 pass. ruff clean. 16 AC lines → all COVERED by TestFromAC_ classes.\nBuilder did not modify test file (git confirmed). Test quality STRONG: DB-state assertions, subprocess stderr checks, mutation-resilient.\ntools.py change (list_entries → str fallback for empty results) verified against test_memory_tools_556 (62/62 pass, no regression).\nNo security issues. Builder process: CLEAN (1 commit).\nMinor: no builder notes in task body.\n\n**Confidence: .96 → PASS**

[[2026-04-04]] Sat 16:46
## Audit\nSee docs/scratch/585-auditor.md for full evidence.\n16/16 AC lines PASS. 47/47 tests pass. Full suite: no regressions. ruff clean. Architect quality 5/5. Confidence .98.
