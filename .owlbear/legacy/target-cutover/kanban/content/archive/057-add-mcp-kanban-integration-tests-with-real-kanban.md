---
id: 57
title: Add mcp-kanban integration tests with real kanban-md binary
status: archived
priority: medium
created: 2026-03-26 19:20:10.426487+01:00
updated: 2026-03-30 03:46:44.143466+02:00
started: 2026-03-30 03:46:43.822646+02:00
completed: 2026-03-30 03:46:43.822646+02:00
tags:
- phase-3
- mcp
- test
depends_on:
- 14
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 12:35
## Test-Writer Notes
- Test file: packages/mcp-kanban/tests/test_integration.py
- Classes: TestFromAC_Integration (6 tests), TestFromAC_Configuration (1 test)
- Total: 7 tests
- Status: PRE-IMPLEMENTATION — all 7 tests PASS against existing server.py
- ruff: not run (file pre-existed)
- Situation: implementation (server.py) and test file were built out-of-sequence before
  test-writer gate. No RED phase achievable — implementation is complete.
- AC coverage:
  - create+list roundtrip: test_create_list_roundtrip
  - create+show roundtrip: test_create_show_roundtrip + test_show_returns_output_with_title_and_status_fields
  - create+move+show: test_create_move_show
  - filtered list by tag: test_filtered_list_by_tag
  - nonexistent ID returns error not exception: test_show_nonexistent_returns_error_not_exception
  - integration marker in pyproject.toml: test_integration_marker_registered_in_pyproject
  - @pytest.mark.asyncio on all async tests: all 6 integration tests
  - binary resolution + pytest.skip: real_kanban_bin fixture
- Note for builder: verify full ruff + coverage gate; tests already pass

[[2026-03-30]] Mon 02:58
## Review Evidence

**Reviewer:** reviewer | **Date:** 2026-03-30

### Test Results

- `uv run pytest packages/mcp-kanban/tests/test_integration.py -v --tb=short` â€” 7 passed, 0 failed

### Lint Results

- `uv run ruff check packages/mcp-kanban/` â€” All checks passed!

### Coverage

- `test_integration.py`: 96% (4 lines missed: fixture skip branches 73-75, 83)
- `server.py`: 56% â€” pre-existing from #56, not changed by this task; suppressed per review skill (coverage only evaluated on modules changed by the task)

### Test-Writer Audit (AC-to-test mapping)

All AC lines covered; no MISSING or LAX entries.

### TestFromAC Comparison

All 7 TestFromAC tests preserved unchanged. No weakened or removed assertions detected.

### Security

- `asyncio.create_subprocess_exec` used (no `shell=True`) â€” no injection risk
- All tests use `tmp_path` via `board_dir` fixture â€” no real board mutation
- Binary validated via `.exists()` before use â€” no path traversal risk
- No hardcoded secrets

### Test Quality

- Assertion specificity: ADEQUATE â€” specific title strings checked; filtered list test checks positive AND negative
- Negative path coverage: COVERED â€” `test_show_nonexistent_returns_error_not_exception`
- Test independence: STRONG â€” `board_dir` uses `tmp_path` (fresh per test)
- Descriptive naming: STRONG

### AC Compliance

All 12 AC lines: PASS
- Test file at correct path: 7 tests collected and passed
- Fixture + minimal config.yml (version, board.name, tasks_dir, statuses, next_id) + tasks/ subdir: `board_dir` fixture + `_MINIMAL_CONFIG`
- Binary resolution (KANBAN_BIN env, convention fallback, pytest.skip): `real_kanban_bin` fixture lines 55-82
- MCP SDK in-memory client with lifespan override: `_make_test_server()` + `create_connected_server_and_client_session`
- Create+list roundtrip: `test_create_list_roundtrip` asserts specific title in output
- Create+show roundtrip (title + status): `test_create_show_roundtrip` + `test_show_returns_output_with_title_and_status_fields`
- Create+move+show: `test_create_move_show` asserts backlog in show output after move
- Filtered list by tag: `test_filtered_list_by_tag` asserts Alpha in and Beta NOT in filtered result
- Nonexistent ID returns error not exception: `test_show_nonexistent_returns_error_not_exception`
- @pytest.mark.integration + pyproject.toml registration: all 6 async tests marked; pyproject.toml line 25; verified by passing `test_integration_marker_registered_in_pyproject`
- @pytest.mark.asyncio + pytest-asyncio in dev deps: `@pytest.mark.asyncio(loop_scope=function)` on all async tests; `pytest-asyncio>=0.25` in pyproject.toml
- CI-compatible: pytest.skip when binary missing; env var override supported

### Verdict: PASS â€” confidence .94

[[2026-03-30]] Mon 03:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at packages/mcp-kanban/tests/test_integration.py | 250 lines, 7 tests | PASS |
| Fixture creates temp dir with config.yml + tasks/ | board_dir fixture L89, _MINIMAL_CONFIG | PASS |
| Binary resolution env/fallback/skip | real_kanban_bin fixture L60-82 | PASS |
| MCP SDK in-memory client with lifespan override | _make_test_server() + create_connected_server_and_client_session | PASS |
| Create+list roundtrip | test_create_list_roundtrip | PASS |
| Create+show roundtrip | test_create_show_roundtrip + test_show_returns_output_with_title_and_status_fields | PASS |
| Create+move+show | test_create_move_show | PASS |
| Filtered list by tag | test_filtered_list_by_tag (Alpha in, Beta NOT in) | PASS |
| Nonexistent ID returns error not exception | test_show_nonexistent_returns_error_not_exception | PASS |
| @pytest.mark.integration + pyproject.toml | All 6 async tests marked; pyproject.toml L25 | PASS |
| @pytest.mark.asyncio | loop_scope=function on all async tests | PASS |
| CI-compatible | pytest.skip when binary missing | PASS |

### Test Results
- pytest (task-specific): 7 passed, 0 failed
- pytest (full suite): 873 passed, 141 failed (all pre-existing RED-phase)
- ruff (packages/mcp-kanban/): All checks passed

### AC Quality Score: 5/5
AC was specific, complete, and led to clean implementation. All 12 lines mapped directly to tests.

### Upstream Commits
- d3dcfcb test: add mcp-kanban integration tests (#57, builder)

### Confidence: .97
### Action: archive
