---
id: 531
title: Build approve_memory CLI wrapper for set_approval_state
status: todo
priority: important
created: 2026-04-01T19:13:11.4079479+02:00
updated: 2026-04-03T17:55:52.7673293+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
    - 529
    - 585
class: standard
---

CLI wrapper for batch approve/reject of pending memory entries, calling set_approval_state MCP tool via in-memory transport. Per docs/research/approve-memory-cli-wrapper.md.

## Acceptance Criteria

### Module location
- [ ] File: packages/mcp-memory/src/owlbear_mcp_memory/approve.py (follows migrate.py pattern)
- [ ] Invocation: uv run --project packages/mcp-memory python -m owlbear_mcp_memory.approve [args]
- [ ] __all__ = [main]
- [ ] main(argv: list[str] | None = None) -> int (follows migrate.py signature)

### CLI interface (argparse)
- [ ] --db-path PATH: optional, resolution order: CLI arg > OWLBEAR_MEMORY_DB_PATH env var > data/memory/memory.db (reuse or replicate _resolve_db_path from migrate.py)
- [ ] --interactive: enter interactive approve/reject loop over pending entries
- [ ] --approve ID [ID ...]: batch-approve specified entry IDs (nargs=+)
- [ ] --reject ID [ID ...]: batch-reject specified entry IDs (nargs=+)
- [ ] --interactive and --approve/--reject are mutually exclusive (argparse add_mutually_exclusive_group or manual check with parser.error)
- [ ] Bare invocation (no mode flag): list pending entries to stdout and exit 0 (read-only preview)
- [ ] Exit 0 on success, 1 on any operation failure
- [ ] if __name__ == __main__: sys.exit(main())

### Display (pending entry listing)
- [ ] Calls list_entries via MCP session with arguments {status: pending}
- [ ] Parses CallToolResult.content[0].text via json.loads to get list of entry dicts
- [ ] Prints numbered table to stdout: index, entry_id (first 8 chars), category, content preview (first 80 chars, truncated with ...)
- [ ] If data/memory/curation-report.json exists and is valid JSON: adds recommendation column from matching entry_id in report
- [ ] If curation-report.json absent (FileNotFoundError) or malformed (json.JSONDecodeError): prints warning to stderr, omits recommendation column

### Interactive mode (--interactive)
- [ ] After listing, prompts user per entry: approve (a), reject (r), skip (s or Enter)
- [ ] Calls set_approval_state MCP tool with {entry_id: id, new-state: approved} for approve
- [ ] Calls set_approval_state MCP tool with {entry_id: id, new-state: deleted} for reject
- [ ] Prints confirmation per state change; prints error to stderr if tool returns error (continues to next entry)
- [ ] After all entries: prints summary line (N approved, N rejected, N skipped)

### Batch mode (--approve / --reject)
- [ ] --approve: calls set_approval_state with new-state=approved for each ID
- [ ] --reject: calls set_approval_state with new-state=deleted for each ID
- [ ] Prints confirmation per entry on success
- [ ] On error (ToolError surfaces as isError=true on CallToolResult, or error prefix in result text): prints error to stderr, continues to next entry
- [ ] Exit 1 if any entry operation failed

### MCP integration (in-memory transport)
- [ ] Uses create_connected_server-and_client_session from mcp.shared.memory
- [ ] Creates FastMCP server with custom asynccontextmanager lifespan that:
  - Opens sqlite3.connect(db_path, check_same_thread=False)
  - Sets conn.row-factory = sqlite3.Row (required for dict(row) in list_entries/get_knowledge)
  - Sets PRAGMA journal_mode=WAL and PRAGMA busy_timeout=5000
  - Reads project_name from owlbear-project.json (same as app_lifespan)
  - Yields AppContext(conn=conn, project_name=project_name)
  - Closes conn in finally
- [ ] Registers list_entries and set_approval_state tools on the test server via add_tool
- [ ] Calls tools via session.call_tool (MCP protocol layer)
- [ ] Wraps async main in asyncio.run() at CLI entry point

### Curation report convention
- [ ] Report path: data/memory/curation-report.json
- [ ] Expected format: JSON array of {entry_id: str, recommendation: str, reason: str}
- [ ] Read via json.load; FileNotFoundError and json.JSONDecodeError caught, warning printed to stderr

### Cross-cutting
- [ ] No new dependencies (uses mcp SDK + owlbear_mcp_memory, both in pyproject.toml)
- [ ] argparse for CLI (follows migrate.py pattern)
- [ ] stdout for user output, stderr for warnings/errors
- [ ] All entry IDs passed as-is to MCP tool calls (tool validates; no CLI-side SQL)

### Deliberate design notes
- MCP transport (not direct SQL): ensures CLI uses validated transition logic from set_approval_state without duplicating state machine rules. Direct function call alternative rejected: FastMCP Context construction outside MCP framework is fragile and couples to internal API.
- Custom lifespan (not production app_lifespan): production lifespan missing row-factory (see follow-up task). Custom lifespan includes conn.row-factory = sqlite3.Row.
- File location changed from scripts/ to package: follows migrate.py pattern in same package, natural imports, consistent invocation style.
- Curation report path hard-coded: matches convention from #567. Graceful skip if absent.

[[2026-04-03]] Fri 17:55
## Architecture Review
See docs/scratch/531-architect.md for full review.
