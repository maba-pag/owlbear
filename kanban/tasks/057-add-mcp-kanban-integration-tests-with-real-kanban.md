---
id: 57
title: Add mcp-kanban integration tests with real kanban-md binary
status: todo
priority: nice-to-have
created: 2026-03-26T19:20:10.4264872+01:00
updated: 2026-03-28T03:45:46.3763137+01:00
tags:
    - phase-3
    - mcp
    - test
depends_on:
    - 14
class: standard
---

Integration tests that exercise mcp-kanban against real kanban-md binary with temp board directory.

## Acceptance Criteria

- [ ] Integration test file at `packages/mcp-kanban/tests/test_integration.py`
- [ ] pytest fixture creates temp directory with minimal `config.yml` (version, board.name, tasks_dir, statuses list, next_id) and `tasks/` subdirectory
- [ ] Fixture resolves kanban-md binary: `KANBAN_BIN` env var first, then `kanban/kanban-md.exe` relative to repo root, `pytest.skip` if neither found
- [ ] Tests use MCP SDK in-memory client (`mcp.shared.memory` or equivalent from mcp>=1.26) with lifespan overridden to inject temp board dir + real binary path
- [ ] Test: create task + list tasks roundtrip -- verify created task appears in list output
- [ ] Test: create task + show by ID roundtrip -- verify returned fields (title, status) match creation args
- [ ] Test: create + move + show -- verify status change persisted after move
- [ ] Test: create 2 tasks with distinct tags + filtered list by tag -- verify filter returns only matching task
- [ ] Test: show nonexistent task ID returns error string in tool result (not an exception)
- [ ] Tests marked with `@pytest.mark.integration`; marker registered in root `pyproject.toml` `[tool.pytest.ini_options].markers`
- [ ] Tests use `@pytest.mark.asyncio` for async MCP client calls (`pytest-asyncio` must be in dev deps)
- [ ] CI-compatible (binary downloaded via `kanban/setup.ps1`)

## References

- docs/research/mcp-kanban-integration-tests.md (full research)
- docs/research/scaffold-mcp-kanban.md (server architecture)
- kanban/setup.ps1 (binary download)
- MCP SDK testing pattern: `mcp.shared.memory.create_connected_server_and_client_session`
- v1/src/owlbear/tools/kanban.py (tool name reference: kanban_list, kanban_show, kanban_create, kanban_move)

## Research

Research complete. Doc: docs/research/mcp-kanban-integration-tests.md

Key findings:

- Use MCP SDK in-memory client_session for testing (.90 confidence)
- Use tmp_path per test for board isolation (.90 confidence)
- Binary resolution: env var then convention then pytest.skip (.90 confidence)
- 5 test scenarios cover AC: create+list, create+show, create+move+show, filtered list, error case
- Depends on #56 (full toolset) -- integration tests need create/show/move/list tools

[[2026-03-27]] Fri 22:47
## Architecture Review
**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file at packages/mcp-kanban/tests/test_integration.py | Precise path | Keep |
| Fixture creates temp dir with config.yml + tasks/ | Precise, config fields specified | Keep |
| Binary resolution: env var, fallback, pytest.skip | Precise 3-step chain | Keep |
| MCP SDK in-memory client with lifespan override | Precise, SDK API referenced, flexibility noted | Refined: allow equivalent API |
| Create + list roundtrip | Precise scenario, pass/fail verifiable | Keep |
| Create + show roundtrip | Precise, field assertions specified | Keep |
| Create + move + show | Precise, status persistence verified | Keep |
| Filtered list by tag | Precise, 2 tasks + filter assertion | Keep |
| Show nonexistent ID returns error | Precise, error-not-exception specified | Keep |
| @pytest.mark.integration + registration | Was missing marker registration | Added: register in pyproject.toml |
| @pytest.mark.asyncio for async MCP calls | Was missing entirely | Added: async test requirement |
| CI-compatible via setup.ps1 | Precise | Keep |

### Architecture Notes

- Pattern: follows MCP SDK in-memory testing pattern (mcp.shared.memory), validated by research at .90 confidence
- Board isolation via tmp_path per test is correct -- prevents cross-test contamination
- Binary resolution matches server lifespan pattern from #39 scaffold
- Module name is owlbear_mcp_kanban (per #7 monorepo, pyproject.toml wheel config)
- Tests import from owlbear_mcp_kanban.server (once #56 implements tools)
- Security: tests use temp dirs only, no mutation of real board
- Single domain: scope:test/mcp integration testing

### Changes Made

- Rewrote AC: added marker registration requirement, added async test requirement, clarified config.yml fields
- Updated depends_on: removed #39 (scaffold, only has list_tasks), added #56 (full toolset with create/show/move/list)
- Note: #39 is archived but server code appears undelivered (only skeleton stub from #7 exists). #56 expansion will need to address scaffold gap.

### Dependencies

- Removed: #39 (scaffold only, insufficient for integration tests needing create/show/move)
- Added: #56 (expands to full 7-tool set including create, show, move, list with filters)
- Transitive: #35 (test infrastructure: pytest-asyncio, per-package test dirs) -- not formal dep since #56 will need it too
- Verified: kanban-md.exe binary available (v0.33.0, kanban/setup.ps1)
